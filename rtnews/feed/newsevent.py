import redis
import pandas as pd
from rtnews import cons as ct
from datetime import datetime
import lxml
from lxml.html import builder as E
from lxml import etree
import time
import os

from rtnews.feed import feed_vars as fv

def get_latest_news(channel, top=None, show_Body=False):
    """
    获取即时新闻

    Parameters
    -------
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
            raise ValueError(f'Channel "{channel}" undefined.')
        else:
            lname = channel
            lid = reversed_dic[channel]
    assert lname and lid

    client = redis.from_url(ct.REDIS_URI, decode_responses=True)
    
    lid_key = ct.KEY_LID.format(lid=lid)
    end = -1 if top is None else top
    news_keys = client.zrevrange(lid_key, 0, end) 
    
    data = []
    for news_key in news_keys:
        news = client.hgetall(news_key)
        rt = datetime.fromtimestamp(int(news['timestamp']))
        rtstr = datetime.strftime(rt, "%m-%d %H:%M")
        row = [lname, news['title'], news['summary'], rtstr, news['url']]
        if show_Body:
            row.append(news['body'])
        data.append(row)
    df = pd.DataFrame(data, columns=fv.LATEST_COLS_C if show_Body else fv.LATEST_COLS)
    return df

def feeds_txt():
    for lid in ct.GLOBAL_CHANNELS:
        df = get_latest_news(lid)
        with open(os.path.join(ct.DAT_DIR, f'{ct.GLOBAL_CHANNELS[lid]}.txt'), 'w', encoding='utf-8') as f:
            for row in df.iterrows():
                row = row[1]
                news = row['title'] + '\n' + row['time'] + '\n' + row['url'] + '\n' + row['summary'] + '\n'
                f.write(news)
                f.write('---\n\n')

def feeds_html():
    for lid in ct.GLOBAL_CHANNELS:
        df = get_latest_news(lid)
        html = E.HTML(
            E.HEAD(
                E.META(content='text/html', charset='utf-8'),
                E.LINK(rel='stylesheet', href='../css/style.css', type='text/css'),
                E.TITLE(E.CLASS('title'), f'{ct.GLOBAL_CHANNELS[lid]}实时新闻摘要')
            )
        )
        body = etree.SubElement(html, 'body')
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
        with open(os.path.join(ct.DAT_DIR, f'{ct.GLOBAL_CHANNELS[lid]}.html'), 'w', encoding='utf-8') as f:
            f.write(lxml.html.tostring(html, pretty_print=True, encoding='utf-8').decode('utf-8'))

if __name__ == '__main__':
    feeds_txt()
    feeds_html()
    #start_time = time.perf_counter()
    #feeds_html()
    #end_time = time.perf_counter()
    #print(f'run feeds in {end_time - start_time} seconds.')