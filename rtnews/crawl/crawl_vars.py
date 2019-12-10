# https://feed.mix.sina.com.cn/api/roll/get?pageid=153&lid=2513&k=&num=50&page=1
CRAWL_URL = '{p_type}{domain}/api/roll/get?pageid={pageid}&lid={channelid}&k=&num={num}&page={page}'

# https://news.sina.com.cn/roll/
REF_URL = '{p_type}{domain}/roll/'

# scid: sina channel id, lid: global channel id
SINA_CHANNELS = {'100': {'slid': '2509', 'lid': '100', 'pageid': '153'},
                 '101': {'slid': '2510', 'lid': '101', 'pageid': '153'},
                 '102': {'slid': '2511', 'lid': '102', 'pageid': '153'},
                 '103': {'slid': '2669', 'lid': '103', 'pageid': '153'},
                 '104': {'slid': '2512', 'lid': '104', 'pageid': '153'},
                 '105': {'slid': '2513', 'lid': '105', 'pageid': '153'},
                 '106': {'slid': '2514', 'lid': '106', 'pageid': '153'},
                 '107': {'slid': '2515', 'lid': '107', 'pageid': '153'},
                 '108': {'slid': '2516', 'lid': '108', 'pageid': '153'},
                 '109': {'slid': '2517', 'lid': '109', 'pageid': '153'},
                 '110': {'slid': '2518', 'lid': '110', 'pageid': '153'}}
SINA_CHANNELS_1 = {'2509': {'slid': '2509', 'lid': '100', 'pageid': '153'},
                   '2510': {'slid': '2510', 'lid': '101', 'pageid': '153'},
                   '2511': {'slid': '2511', 'lid': '102', 'pageid': '153'},
                   '2669': {'slid': '2669', 'lid': '103', 'pageid': '153'},
                   '2512': {'slid': '2512', 'lid': '104', 'pageid': '153'},
                   '2513': {'slid': '2513', 'lid': '105', 'pageid': '153'},
                   '2514': {'slid': '2514', 'lid': '106', 'pageid': '153'},
                   '2515': {'slid': '2515', 'lid': '107', 'pageid': '153'},
                   '2516': {'slid': '2516', 'lid': '108', 'pageid': '153'},
                   '2517': {'slid': '2517', 'lid': '109', 'pageid': '153'},
                   '2518': {'slid': '2518', 'lid': '110', 'pageid': '153'}}