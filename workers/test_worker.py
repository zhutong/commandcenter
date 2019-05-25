# encoding: utf-8

import random
from time import sleep

from modules.worker_base import BaseWorker, main, logging


class Worker(BaseWorker):
    channel = 'test'
    name = channel.upper()

    def handler(self, task_id, params):
        logging.info('Doing %s', task_id)
        sleep(random.randrange(1, 6))
        size = random.randrange(1, 1000) * 10000
        return dict(status='success',
                    message='',
                    hostname=params['hostname'],
                    output=['A'*size])


if __name__ == '__main__':
    main(Worker)
