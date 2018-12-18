# -*- coding: utf-8 -*-

__version__ = 0.1
__author__ = 'zhutong <zhtong@cisco.com>'

import re

from modules.base_ssh_worker import SSHWorker
from modules.worker_base import main


class CLIWorker(SSHWorker):
    channels = 'f5',
    name = 'F5'
    hostname_pattern = re.compile('.*@(.*)\(Active\)\(tmos\)#')
    error_sign = ''
    no_pager_list = ('tmsh modify cli preference pager disabled',
                     'terminal length 0')
    prompt_list = '#',


main(CLIWorker)
