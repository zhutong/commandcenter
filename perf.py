# encoding: utf-8


import logging
import time

from multiprocessing.dummy import Pool

import requests
from tornado.log import enable_pretty_logging

enable_pretty_logging()


def collect(param):
    url = 'http://127.0.0.1:8080/api/v1/sync/cli'
    res = requests.post(url, json=param)
    logging.info(res.json()['hostname'])


chunk = 10


for n in xrange(100000/chunk):
    pool = Pool(chunk)
    params = []
    for m in xrange(chunk):
        i = n*chunk+m
        param = dict(ip='192.168.12.%d' % i,
                     hostname='R%08d' % i,
                     commands=['show ver'],
                     channel='test')
        params.append(param)
    pool.map(collect, params)
    pool.close()
    pool.join()
