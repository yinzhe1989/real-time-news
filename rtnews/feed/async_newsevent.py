import aioredis
import pandas as pd
from datetime import datetime
import lxml.html
from lxml.html import builder as E
from lxml import etree
import asyncio
import time
import os
import sys
import logging

from rtnews import cons as ct
from rtnews.feed import feed_vars as fv

async def get_latest_news(redis, channel, top=None, show_Body=False):
    """
    获取即时新闻

    Parameters
    -------
        redis: aioredis.RedisPool
        channel: str, 待获取的新闻所在频道(id或名称)
        top: int, 最多获取多少条新闻，默认None全获取
        show_body: bool, 是否返回新闻正文，默认False不返回

    Result
    -------
        pandas.DataFrame, 包括如下列：
            channel: 频道类别
            title: 标题
            summary: 摘要
            time: 时间
            url: 新闻链接
            body: 正文（在show_content为True的情况下出现）
    """
    lname = ''
    lid = ''
    if channel in ct.GLOBAL_CHANNELS:
        lname = ct.GLOBAL_CHANNELS[channel]
        lid = channel
    else:
        reversed_dic = {v: k for k, v in ct.GLOBAL_CHANNELS.items()}
        if channel not in reversed_dic:
            raise ValueError(f'Parameter "channel": value "{channel}" undefined.')
        else:
            lname = channel
            lid = reversed_dic[channel]
    assert lname and lid

    logging.info(f'Getting latest news, channel name: {lname}, channel id: {lid}')
   
    lid_key = ct.KEY_LID.format(lid=lid)
    end = -1 if top is None else top
    logging.debug(f'Redis zrevrange, key={lid_key}, start=0, end={end}')
    news_keys = await redis.zrevrange(lid_key, 0, end)
    logging.debug(f'news_keys={news_keys}')
    logging.info(f'Found {len(news_keys)} news in channel {lname}. Processing...')

    data = []
    for news_key in news_keys:
        logging.debug(f'Redis hgetall, key={news_key}')
        news = await redis.hgetall(news_key)
        logging.debug(f'raw news from redis: {news}')
        rt = datetime.fromtimestamp(int(news['timestamp']))
        rtstr = datetime.strftime(rt, "%m-%d %H:%M")
        row = [lname, news['title'], news['summary'], rtstr, news['url']]
        if show_Body:
            row.append(news['body'])
        data.append(row)
        logging.debug(f'news processed as a list: {row}')
    df = pd.DataFrame(data, columns=fv.LATEST_COLS_C if show_Body else fv.LATEST_COLS)
    return df

async def feeds_txt(redis, lid):
    df = await get_latest_news(redis, lid)
    txt_file = os.path.join(ct.DAT_DIR, f'{ct.GLOBAL_CHANNELS[lid]}.txt')
    logging.info(f'Writing text to file: {txt_file}')
    news_count = 0
    with open(txt_file, 'w', encoding='utf-8') as f:
        for row in df.iterrows():
            row = row[1]
            news = row['title'] + '\n' + row['time'] + '\n' + row['url'] + '\n' + row['summary'] + '\n'
            f.write(news)
            f.write('---\n\n')
            news_count = news_count +1
            logging.debug(f'Append one news to file, news: {news}')
    logging.info(f'news count: {news_count} ')


async def feeds_html(redis, lid):
    df = await get_latest_news(redis, lid)
    html = E.HTML(
        E.HEAD(
            E.META(content='text/html', charset='utf-8'),
            E.LINK(rel='stylesheet', href='../css/style.css', type='text/css'),
            E.TITLE(E.CLASS('title'), f'{ct.GLOBAL_CHANNELS[lid]}实时新闻摘要')
        )
    )
    body = etree.SubElement(html, 'body')
    logging.debug(f'html: {lxml.html.tostring(html, pretty_print=True, encoding="utf-8").decode("utf-8")}')

    news_count = 0
    for row in df.iterrows():
        row = row[1]
        div = etree.SubElement(body, 'div')
        h1 = etree.SubElement(div, 'h1', attrib={'class': 'heading'})
        a = etree.SubElement(h1, 'a', attrib={'href': row['url']})
        a.text = row['title']
        p1 = etree.SubElement(div, 'p', attrib={'class': 'time'})
        p1.text = row['time']
        p2 = etree.SubElement(div, 'p', attrib={'class': 'summary'})
        p2.text = row['summary']
        logging.debug(f'Append one news to html body, news: {etree.tostring(div, pretty_print=True, encoding="utf-8").decode("utf-8")}')
        news_count = news_count + 1

    html_file = os.path.join(ct.DAT_DIR, f'{ct.GLOBAL_CHANNELS[lid]}.html')
    logging.info(f'Writing html to file: {html_file}, news count: {news_count}')
    with open(html_file, 'w', encoding='utf-8') as f:
        f.write(lxml.html.tostring(html, pretty_print=True, encoding='utf-8').decode('utf-8'))

async def feeds():
    logging.info('Creating redis pool...')
    redis = await aioredis.create_redis_pool(ct.REDIS_URI, encoding='utf-8')
    logging.info(f'Creating tasks...')
    tasks = [asyncio.create_task(feeds_html(redis, lid)) for lid in ct.GLOBAL_CHANNELS]
    logging.info(f'Created {len(tasks)} tasks, task=feeds_html')

    logging.info('Gathering feeding tasks...')
    res = await asyncio.gather(*tasks, return_exceptions=True)
    logging.debug(f'tasks return: {res}')
    for i in res:
        if i != None:
            logging.error(f'task failed: {repr(i)}')

    logging.info('Closing redis...')
    redis.close()
    await redis.wait_closed()

if __name__ == '__main__':
    try:
        fh = logging.FileHandler(ct.FEED_LOG_FILE, mode='a', encoding='utf-8', delay=False)
    except:
        fh = logging.StreamHandler(sys.stdout)
    logging.basicConfig(handlers=[fh], format='%(asctime)s %(filename)s %(lineno)d %(levelname)s:%(message)s', level=ct.LOG_LEVEL)
    #logging.basicConfig(format='%(asctime)s %(filename)s %(lineno)d %(levelname)s:%(message)s', level=ct.LOG_LEVEL)
    #start_time = time.perf_counter()
    asyncio.run(feeds())
    #end_time = time.perf_counter()
    #print(f'run ASYNC feeds in {end_time - start_time} seconds.')