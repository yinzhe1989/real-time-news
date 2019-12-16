VERSION = '0.0.1'

P_TYPE = {'http': 'http://', 'https': 'https://', 'ftp': 'ftp://'}

PAGE_NUM = [40, 60, 80, 100]

DOMAINS = {'sina': 'sina.com.cn', 'sinahq': 'sinajs.cn',
           'ifeng': 'ifeng.com', 'sf': 'finance.sina.com.cn',
           'vsf': 'vip.stock.finance.sina.com.cn',
           'idx': 'www.csindex.com.cn', '163': 'money.163.com',
           'em': 'eastmoney.com', 'sseq': 'query.sse.com.cn',
           'sse': 'www.sse.com.cn', 'szse': 'www.szse.cn',
           'oss': 'file.tushare.org', 'idxip': '115.29.204.48',
           'shibor': 'www.shibor.org', 'mbox': 'www.cbooo.cn',
           'tt': 'gtimg.cn', 'gw': 'gw.com.cn',
           'v500': 'value500.com', 'sstar': 'stock.stockstar.com',
           'dfcf': 'nufm.dfcfw.com', 'sn': 'news.sina.com.cn',
           'sfeed': 'feed.mix.sina.com.cn'}

# 新闻频道类别
"""
GLOBAL_CHANNELS = {'107': '科技'}
"""
GLOBAL_CHANNELS = {'100': '全部', '101': '国内', '102': '国际',
                   '103': '社会', '104': '体育', '105': '娱乐',
                   '106': '军事', '107': '科技', '108': '财经',
                   '109': '股市', '110': '美股'}

# 新闻摘要最大句子数
MAX_SUMMARY_SENTENCES_NUM = 4

# 新闻摘要句子最大字数
MAX_SUMMARY_SENTENCE_WORDS_NUM = 100

# 新闻摘要最大字数
MAX_SUMMARY_TOTAL_WORDS_NUM = 150

# Redis 相关配置
REDIS_URI = 'redis://127.0.0.1:6379'
KEY_CHANNELS = 'channels'
KEY_LID = 'lid-{lid}'
KEY_NEWS = 'news-{oid}'

# 新闻过期时长
NEWS_EXPIRE_SECS = 2*24*60*60

# 采集周期 30分钟
CRAWL_CYCLE_SECS = 30 * 60
#CRAWL_CYCLE_SECS = 3*24*60*60

# dir and log file
import sys
import os
import logging
import logging.handlers
LOG_LEVEL = logging.INFO
WORK_DIR = os.path.dirname(os.path.abspath(os.path.dirname(__file__)))
#print(WORK_DIR)
DAT_DIR = os.path.join(WORK_DIR, 'dat')
#print(DAT_DIR)
# 注释LOG_FILE即可打印到终端
CRAWL_LOG_FILE = os.path.join(DAT_DIR, 'crawl.log')
FEED_LOG_FILE = os.path.join(DAT_DIR, 'feed.log')
#print(LOG_FILE)
if not os.path.exists(DAT_DIR):
    os.mkdir(DAT_DIR)

def get_logger(log_name, log_level, log_file=None):
    logger = logging.getLogger(log_name)
    logger.setLevel(log_level)
    if log_file:
        fh = logging.handlers.RotatingFileHandler(log_file, mode='a', maxBytes=1024*1024*10, backupCount=2, encoding='utf-8', delay=False)
    else:
        fh = logging.StreamHandler(sys.stdout)
    datefmt = '%Y-%m-%d %H:%M:%S'
    format_str = '%(asctime)s %(filename)s %(lineno)d %(levelname)s:%(message)s'
    formatter = logging.Formatter(format_str, datefmt)
    fh.setFormatter(formatter)
    logger.addHandler(fh)
    
    return logger

    