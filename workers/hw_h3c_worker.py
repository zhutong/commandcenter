# -*- coding: utf-8 -*-

__version__ = 0.1
__author__ = 'zhutong <zhtong@cisco.com>'

import re

from modules.base_ssh_worker import SSHWorker
from modules.worker_base import main


class CLIWorker(SSHWorker):
    channel = 'huawei'
    name = 'HW-H3C'
    hostname_pattern = re.compile('<(.*?)>')
    error_sign = " '^' "
    no_pager_list = ('screen-length 0 temporary',)
    prompt_list = ('>', '[Y/N]:')


main(CLIWorker)
