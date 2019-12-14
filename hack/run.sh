#!/bin/bash
source /etc/profile
export PATH=/usr/local/bin:/usr/bin:$PATH
hackdir=$(cd $(dirname $0); pwd)
workdir=$hackdir/..
export PYTHONPATH=$workdir
echo 'crawling news...'
`which python3` $workdir/rtnews/crawl/async_crawl.py
echo 'generating news html...'
`which python3` $workdir/rtnews/feed/async_newsevent.py
echo 'uploading to baiduyun...'
cd $workdir/dat
`which bypy` upload
echo 'done'