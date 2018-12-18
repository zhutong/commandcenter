# -*- coding: utf-8 -*-

"""
基于pexpect的通用SSH采集器。需要系统支持openSSH。
"""

__version__ = 0.6
__author__ = 'zhutong <zhtong@cisco.com>'

import re
from time import strftime

import pexpect

SSH_V1_STR = 'ssh -1 -o "UserKnownHostsFile /dev/null" -l %s %s'
SSH_V2_STR = 'ssh -2 -o "UserKnownHostsFile /dev/null" -l %s %s'


class SSH():

    def __init__(self, device_info, logger, prompt_list, hostname_pattern, no_pager_list, error_sign):
        self.device_info = device_info
        self.method = device_info.get('method', 'ssh').lower() or 'ssh'
        self.timeout = device_info.get('timeout', 10)
        self.logger = logger
        self.prompt_list = prompt_list
        self.hostname_pattern = hostname_pattern
        self.no_pager_list = no_pager_list
        self.error_sign = error_sign
        self.child = None

    def login(self):
        ip = self.device_info['ip']
        username = self.device_info.get('username')
        password = self.device_info.get('password')
        timeout = self.timeout
        prompt = self.prompt_list[0]
        child = self.child
        try:
            if self.method != 'ssh':
                self.logger.info('ssh(v1) %s as %s', ip, username)
                cmd_str = SSH_V1_STR % (username, ip)
            else:
                self.logger.info('ssh(v2) %s as %s', ip, username)
                cmd_str = SSH_V2_STR % (username, ip)
            child = pexpect.spawn(cmd_str, maxread=8192, searchwindowsize=4096)

            first_pattern = ['.*assword:',
                             '.*(yes/no)',
                             pexpect.TIMEOUT,
                             pexpect.EOF]
            i = child.expect(first_pattern, timeout=timeout)
            if i == 3:
                raise Exception('LoginException.CONNECTION_CLOSED')
            if i == 2:
                raise Exception('LoginException.TIMEOUT')
            if i == 1:
                child.sendline('yes')
                child.expect(['.*assword:'])
            child.sendline(password)

            second_pattern = ['.*%s' % prompt,
                              '.*assword:',
                              pexpect.TIMEOUT,
                              pexpect.EOF]
            i = child.expect(second_pattern, timeout=timeout)
            if i == 1:
                raise Exception('LoginException.LOGIN_FAILED')
            if i == 2:
                raise Exception('LoginException.LOGIN_TIMEOUT')
            if i == 3:
                raise Exception('LoginException.CONNECTION_CLOSED')

            for line in self.no_pager_list:
                child.sendline(line)
                child.expect(prompt, timeout=timeout)
            last_line = child.before.splitlines()[-1].decode()
            self.prompt = last_line + prompt
            try:
                hostname = self.hostname_pattern.findall(self.prompt)[0]
            except:
                hostname = self.device_info.get('hostname', '')
            self.hostname = hostname
            self.child = child
            self.logger.info('ssh %s success. Got hostname: %s', ip, hostname)
            expect_pattern = [pexpect.TIMEOUT,
                              pexpect.EOF,
                              re.escape(self.prompt)]
            for p in self.prompt_list[1:]:
                expect_pattern.append(re.escape(p))
            expect_pattern.append('.*\r\n')
            self.expect_pattern = expect_pattern
            return self.hostname
        except Exception as e:
            self.logger.warning('ssh %s failed: %s', ip, e)
            raise

    def execute(self, command):
        ip = self.hostname or self.device_info['ip']
        expect_pattern = self.expect_pattern
        new_line_pattern_id = len(expect_pattern) - 1
        timeout = self.timeout
        child = self.child
        res = []
        self.logger.info('%s execute: %s', ip, command)
        child.sendline(command)
        while True:
            c = child.expect(expect_pattern, timeout=timeout)
            res.append(child.before.decode())
            res.append(child.after.decode())
            if c < new_line_pattern_id:
                break
        if c == 0:
            msg = 'Timeout'
            self.logger.error('Timeout execute: %s @ %s', command, ip)
            raise Exception(msg)

        output = ''.join(res)
        if self.error_sign and self.error_sign in output:
            status = 'Error'
        else:
            status = 'Ok'
        timestamp = strftime('%Y-%m-%d %H:%M:%S')
        return dict(command=command, status=status, output=output, timestamp=timestamp)

    def close(self):
        try:
            self.child.close()
            self.logger.info('Disconnected from %s', self.device_info['ip'])
        except:
            pass
