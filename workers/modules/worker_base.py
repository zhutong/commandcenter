# encoding: utf-8

import json
import logging
import os
import sys
import time
from threading import Thread

import zmq
from tornado import ioloop, options
from tornado.log import enable_pretty_logging

enable_pretty_logging()

context = zmq.Context()


def get_port(server, channel):
    req = context.socket(zmq.REQ)
    req.connect("tcp://%s:16000" % server)
    req.send_string(channel)
    port = req.recv_string()
    logging.info('Connected server, got port: %s', port)
    req.close()
    return int(port)


class BaseWorker(Thread):

    def __init__(self, thread_name, server, port):
        Thread.__init__(self)
        worker = context.socket(zmq.REP)
        worker.connect("tcp://%s:%d" % (server, port))
        logging.info('Worker thread %s started', thread_name)
        self.worker = worker
        self.thread_name = thread_name

    def run(self):
        worker = self.worker
        t_name = self.thread_name
        while True:
            message = worker.recv_json()
            start_at = time.strftime('%Y-%m-%d %H:%M:%S')
            task_id = message['task_id']
            logging.info('%s: task started %s', t_name, task_id)
            result = self.handler(task_id, message)
            result['task_id'] = task_id
            result['ip'] = message['ip']
            result['start@'] = start_at
            result['finish@'] = time.strftime('%Y-%m-%d %H:%M:%S')
            worker.send_json(result)
            logging.info('%s: task finished %s', t_name, task_id)

    def handler(self, task_id, message):
        raise NotImplementedError()


def main(worker):
    options.define("s", default='127.0.0.1', help="zmq server", type=str)
    options.define("t", default=10, help="threads", type=int)
    options.parse_command_line()
    server = options.options.s
    threads = options.options.t

    port = get_port(server, worker.channel)

    pid = os.getpid()
    for tid in range(threads):
        worker_name = '%s-%05d-%03d' % (worker.name, pid, tid)
        work = worker(worker_name, server, port)
        work.daemon = True
        work.start()

    try:
        ioloop.IOLoop.instance().start()
    except KeyboardInterrupt:
        logging.info('Works exited')
