#!/bin/bash
hackdir=$(cd $(dirname $0); pwd)
workdir=$hackdir/..
export PYTHONPATH=$workdir
echo 'crawling news...'
python3 $workdir/rtnews/crawl/async_crawl.py
echo 'generating news html...'
python3 $workdir/rtnews/feed/async_newsevent.py
echo 'done'
