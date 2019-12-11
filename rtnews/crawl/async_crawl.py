from rtnews.crawl import crawl_vars as cv
from rtnews import cons as ct
import asyncio
import aioredis
import logging
from datetime import datetime
import aiohttp
import lxml.html
from lxml import etree
from io import StringIO
from textrank4zh import TextRank4Sentence
import sys
import re


class SinaRollNewsItem(object):
    """
    新浪滚动新闻条目信息，包含：

        oid: 唯一标识
        url: str，网址
        lids: list(str)，所属频道id列表
        title: str，标题
        timestamp: str，时间戳
        keywords: list(str)，关键字列表
        summary: str，摘要
        body: str，正文
    """

    def __init__(self, oid):
        self._oid = oid

    def __str__(self):
        if len(self._body) > ct.MAX_SUMMARY_SENTENCES_NUM * ct.MAX_SUMMARY_SENTENCE_WORDS_NUM:
            half = ct.MAX_SUMMARY_SENTENCES_NUM * ct.MAX_SUMMARY_SENTENCE_WORDS_NUM // 4
            body = self._body[:half] + '...' + self._body[0-half:]
        else:
            body = self._body
        return (f'SinaRollNewsItem<oid={self._oid}, url={self._url}, '
                f'lids={self._lids}, title={self._title}, timestamp={self._timestamp}, '
                f'keywords={self._keywords}, summary={self._summary}, body={body}>')

    def to_dict(self):
        d = {}
        for k, v in self.__dict__.items():
            d[k[1:]] = ','.join(v) if type(v) == list else v
        return d

    @property
    def oid(self):
        return self._oid

    @oid.setter
    def oid(self, value):
        self._oid = value

    @property
    def url(self):
        return self._url

    @url.setter
    def url(self, value):
        self._url = value

    @property
    def lids(self):
        return self._lids

    @lids.setter
    def lids(self, value):
        self._lids = value

    @property
    def title(self):
        return self._title

    @title.setter
    def title(self, value):
        self._title = value

    @property
    def timestamp(self):
        return self._timestamp

    @timestamp.setter
    def timestamp(self, value):
        self._timestamp = value

    @property
    def keywords(self):
        return self._keywords

    @keywords.setter
    def keywords(self, value):
        self._keywords = value

    @property
    def summary(self):
        return self._title

    @summary.setter
    def summary(self, value):
        self._summary = value

    @property
    def body(self):
        return self._body

    @body.setter
    def body(self, value):
        self._body = value

async def run_task():
    """
    异步运行新闻采集任务。

    每个新闻频道对应一个采集任务，同时创建相同个数的redis持久化任务，
    采集到的新闻条目放入异步队列，redis持久化任务读取队列并持久化到redis中。
    """
    logging.info(f'Global channels: {ct.GLOBAL_CHANNELS}')
    logging.info('Creating queue...')
    queue = asyncio.Queue()

    logging.info('Creating redis pool...')
    redis = await aioredis.create_redis_pool(ct.REDIS_URI, encoding='utf-8')

    ts_now = int(datetime.now().timestamp())
    ts_crawl = ts_now - ct.CRAWL_CYCLE_SECS
    ts_expire = ts_now - ct.NEWS_EXPIRE_SECS # 时间戳比该值小的新闻均过期

    logging.info('Maintaining redis...')
    await _maintain(redis, ts_expire)

    logging.info('Creating crawl tasks...')
    crawl_tasks = [asyncio.create_task(_crawl(queue, lid, ts_crawl)) for lid in ct.GLOBAL_CHANNELS]
    logging.info(f'Created {len(crawl_tasks)} tasks, task=_crawl')

    logging.info('Creating save tasks...')
    save_tasks = [asyncio.create_task(_save(queue, redis)) for _ in range(len(crawl_tasks))]
    logging.info(f'Created {len(save_tasks)} tasks, task=_save')

    logging.info('Gathering crawl tasks...')
    res = await asyncio.gather(*crawl_tasks, return_exceptions=True)
    logging.debug(f'crawl tasks return: {res}')
    for i, v in enumerate(res):
        if v != 1:
            logging.error(f'index: {i}, crawl task failed: {v}')

    logging.info('Joining queue...')
    await queue.join()

    logging.info('Cancelling save tasks...')
    [save_task.cancel() for save_task in save_tasks]

    #logging.info('Gathering save tasks...')
    #await asyncio.gather(*save_tasks, return_exceptions=True)

    logging.info('Closing redis...')
    redis.close()
    await redis.wait_closed()

async def _save(queue, redis):
    """
    抓取到的新闻存取到redis中

    Parameters
    --------
        redis: aioredis.RedisPool
        queue: asyncio.Queue(SinaRollNewsItem)，存放抓取到的新闻条目
    """
    while True:
        news_item = await queue.get()
        if not news_item.oid:
            raise ValueError('News item oid empty')

        key = ct.KEY_NEWS.format(oid=news_item.oid)
        logging.info(f'Save news: key={key}')
        if not await redis.exists(key):
            await redis.hmset_dict(key, news_item.to_dict())
            await redis.expireat(key, int(news_item.timestamp) + ct.NEWS_EXPIRE_SECS)
            for lid in news_item.lids:
                await redis.zadd(ct.KEY_LID.format(lid=lid), int(news_item.timestamp), key)

        queue.task_done()

async def _maintain(redis, ts_expire):
    """
    维护存储的key和value，清除过期内容

    Parameters
    --------
        redis: aioredis.RedisPool
        ts_expire: int, 时间戳，时间戳比该值小的新闻均过期
    """
    if not await redis.exists(ct.KEY_CHANNELS):
        logging.debug(f'Redis: hmset_dict, key={ct.KEY_CHANNELS}, value={ct.GLOBAL_CHANNELS}')
        await redis.hmset_dict(ct.KEY_CHANNELS, ct.GLOBAL_CHANNELS) # 这里不在任务里
    tasks = [asyncio.create_task(_maintain_lid_zset(redis, ts_expire, lid)) for lid in ct.GLOBAL_CHANNELS]
    logging.debug(f'Created {len(tasks)} tasks, task=_maintain_lid_zset')
    await asyncio.gather(*tasks, return_exceptions=True)

async def _maintain_lid_zset(redis, ts_expire, lid):
    """
    维护频道内的新闻条目的key集合，清除过期的key

    Parameters
    --------
        redis: aioredis.RedisPool
        ts_expire: int, 时间戳，时间戳比该值小的新闻均过期
        lid: 新闻频道的id
    """
    key = ct.KEY_LID.format(lid=lid)
    logging.debug(f'Redis: zremrangebyscore, key={key}, min={float("-inf")}, max={ts_expire}')
    await redis.zremrangebyscore(key, min=float('-inf'), max=ts_expire)

async def _crawl(queue, global_lid, timeline):
    """
    异步方式抓取指定新闻频道在指定时间戳之后的新闻

    Parameters
    --------
        queue: asyncio.Queue(SinaRollNewsItem)，存放抓取到的新闻条目
        global_lid: str，新闻频道类别id
        timeline: int，时间戳，抓取大于该时间戳的新闻

    Return
    --------
    """
    if global_lid not in ct.GLOBAL_CHANNELS:
        raise KeyError(global_lid)
    if global_lid not in cv.SINA_CHANNELS:
        raise KeyError(global_lid)
    logging.info(f'Crawl: channel={ct.GLOBAL_CHANNELS[global_lid]}({global_lid}), '
                 f'timeline={datetime.fromtimestamp(timeline)}({timeline})')
    pageid = cv.SINA_CHANNELS[global_lid].get('pageid', '153')
    slid = cv.SINA_CHANNELS[global_lid]['slid']
    page = 1
    while True:
        url = cv.CRAWL_URL.format(
            p_type=ct.P_TYPE['https'],
            domain=ct.DOMAINS['sfeed'],
            pageid=pageid,
            channelid=slid,
            num=ct.PAGE_NUM[1],
            page=page)
        next_page = await _crawl_page(queue, global_lid, url, timeline)
        if next_page:
            page = page + 1
        else:
            logging.info(f'Task crawl end. global_lid={global_lid}')
            break


async def _crawl_page(queue, global_lid, url, timeline):
    """
    异步方式抓取指定url在指定时间戳之后的新闻

    Parameters
    --------
        queue: asyncio.Queue(SinaRollNewsItem)，存放抓取到的新闻条目
        url: str，待请求的url
        global_lid: str，新闻频道类别id
        timeline: int，时间戳，抓取大于该时间戳的新闻

    Return
        bool, 是否继续抓取下一页
    --------

    """
    logging.info(f'Crawl page: {url}')
    header = {'referer': cv.REF_URL.format(p_type=ct.P_TYPE['https'], domain=ct.DOMAINS['sn']),
              'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/78.0.3904.97 Safari/537.36'}
    async with aiohttp.ClientSession(headers=header, connector=aiohttp.TCPConnector(ssl=False)) as session:
        async with session.get(url) as response:
            try:
                json_response = await response.json(encoding=response.charset if response.charset else 'utf-8')
                #logging.debug(f'News json response: {json_response}')
            except aiohttp.ContentTypeError:
                logging.warning(
                    f'Skip this response. Reason: content-type not match, expect: "application/json", get: "{response.content_type}"')
            return await _parse_news_items(queue, session, global_lid, timeline, json_response)


async def _parse_news_items(queue, session, global_lid, timeline, json_response):
    """
    解析json中的新闻条目列表

    Parameters
    --------
        queue: asyncio.Queue(SinaRollNewsItem)，存放抓取到的新闻条目
        session: aiohttp.ClientSession，异步http会话，用于请求新闻正文
        global_lid: str，新闻频道类别id
        timeline: int，时间戳，抓取大于该时间戳的新闻
        json_response：json，包含待解析的新闻条目列表

    Return
        bool, 是否继续抓取下一页
    """
    next_page = True
    try:
        for json_item in json_response['result']['data']:
            logging.debug(f'News item json: {json_item}')
            if int(json_item['ctime']) < timeline:
                logging.warning(f'Json news item ctime: {json_item["ctime"]}, skip it.')
                next_page = False
                continue
            if not json_item['oid']:
                logging.warning(f'Json news item oid empty, skip it.')
                continue
            obj_item = SinaRollNewsItem(json_item['oid'])
            obj_item.url = json_item['url']
            obj_item.title = json_item['title']
            obj_item.timestamp = json_item['ctime']
            # lids
            obj_item.lids = []
            lids = json_item['lids']
            lids = lids.split(',')
            obj_item.lids = [cv.SINA_CHANNELS_1[slid]['lid']
                             for slid in lids if slid in cv.SINA_CHANNELS_1]
            obj_item.keywords = json_item['keywords'].split(',')
            # get news body and summary
            async with session.get(obj_item.url) as response:
                text = await response.text(encoding=response.charset if response.charset else 'utf-8')
                obj_item.body, obj_item.summary = _parse_news_item_body(text)
            if not obj_item.body or not obj_item.summary:
                logging.warning(f'News item body/summary empty, skip it. url: {obj_item.url}')
                continue
            # append to async queue
            logging.info(f'Put news item to queue: {obj_item}')
            await queue.put(obj_item)
    except KeyError as e:
        logging.error(f'news item parse error, exception: key {e} not found')
        next_page = False
    return next_page


def _parse_news_item_body(text):
    """
    解析新闻条目的正文，并根据正文生成摘要

    Parameters:
    ------
        text: str, 新闻正文网页文本

    Return:
    ------
        body: str, 新闻正文
        summary: str, 新闻摘要

    """
    html = lxml.html.parse(StringIO(text))
    res = html.xpath('//div[@id="artibody" or @id="article"]/p')
    body = ''
    for node in res:
        p_class = node.xpath('@class')
        if p_class and p_class[0] in ['article-editor', 'show_author']:
            continue
        p_text = node.xpath("string()")
        if not p_text:
            continue
        p_text.replace('&nbsp;', ' ')
        if p_text.startswith('\u3000\u3000新浪声明'):
            continue
        #if p_text.startswith('\u3000\u3000新浪财经讯 '):
        #    p_text = '\u3000\u3000' + p_text[len('\u3000\u3000新浪财经讯 '):]
        p_text = re.sub('^\u3000\u3000新浪.{0,6}讯 ', '\u3000\u3000', p_text)
        
        body = body + p_text + '\n'
    summary = ''
    logging.debug(f'news body: {body}')
    if body:
        tr4s = TextRank4Sentence()
        tr4s.analyze(text=body, lower=True, source = 'all_filters')
        summary_arr = []
        for item in tr4s.get_key_sentences(num=ct.MAX_SUMMARY_SENTENCES_NUM):
            if len(item.sentence) < ct.MAX_SUMMARY_SENTENCE_WORDS_NUM:
                summary_arr.append([item.index, item.sentence])
        summary_arr = sorted(summary_arr, key=lambda x: x[0])
        summary_arr = map(lambda x: x[1] + '。', summary_arr)
        summary = ''.join(summary_arr)
        logging.debug(f'news summary: {summary}')

    return body, summary

def _day_or_night(timestamp):
    """
    判断给定的时间戳是白天还是午夜。

    日间：（6:00-22:00）；午夜：（00:00-6:00, 22:00-24:00）

    Parameters
    -------
        timestamp: int, 时间戳

    Return
    -------
        'day': 白天
        'night': 午夜
    """
    h = datetime.fromtimestamp(timestamp).hour
    return 'day' if h >= 6 and h < 22 else 'night'

if __name__ == '__main__':
    try:
        fh = logging.FileHandler(ct.CRAWL_LOG_FILE, mode='w', encoding='utf-8', delay=False)
    except:
        fh = logging.StreamHandler(sys.stdout)
    logging.basicConfig(handlers=[fh], format='%(asctime)s %(filename)s %(lineno)d %(levelname)s:%(message)s', level=ct.LOG_LEVEL)
    #logging.basicConfig(format='%(asctime)s %(filename)s %(lineno)d %(levelname)s:%(message)s', level=ct.LOG_LEVEL)
    asyncio.run(run_task())