# __author__ = 'zhutong'

# ##########################################################
# Script for collecting information from Cisco devices
# pexpect is required & openSSH is tested.
# ##########################################################

import re
from time import strftime

import pexpect


class LoginException(Exception):
    LOGIN_TIMEOUT = -1
    CONNECTION_CLOSED = -2
    LOGIN_FAILED = -3
    ENABLE_FAILED = -4
    SSH_VERSION_ERROR = -5

    __message = {LOGIN_TIMEOUT: 'Timeout',
                 CONNECTION_CLOSED: 'Connection_Closed',
                 LOGIN_FAILED: 'Wrong username or password',
                 ENABLE_FAILED: 'Wrong enable password',
                 SSH_VERSION_ERROR: 'SSH version not supported'
                 }

    def __init__(self, err_code):
        self.err_code = err_code
        self.err_msg = self.__message[err_code]

    def __str__(self):
        return '<LoginException.%s>' % self.err_msg


class CiscoCLI(object):
    TELNET_STR = 'telnet %s %d'
    SSH_STR = 'ssh -p %d -o "UserKnownHostsFile /dev/null" -l %s %s'
    SSH_V1_STR = 'ssh -1 -p %d -o "UserKnownHostsFile /dev/null" -l %s %s'

    def __init__(self, device_info, logger):
        self.device_info = device_info
        self.ip = device_info['ip']
        self.timeout = device_info.get('timeout', 30)
        self.username = device_info.get('username')
        self.password = device_info.get('password')
        self.enable_password = device_info.get('enable_password')
        self.method = device_info.get('method', 'ssh').lower()
        self.port = device_info.get('port')
        self.extra_prompts = device_info.get('extra_prompts')
        self.error_sign = device_info.get('error_sign', " '^' ")
        self.logger = logger
        self.child = None

    def login(self):
        try:
            return self.__login()
        except LoginException as e:
            if e.err_code == LoginException.CONNECTION_CLOSED:
                if self.method == 'telnet':
                    self.method = 'ssh'
                else:
                    self.method = 'telnet'
                return self.__login()
            elif e.err_code == LoginException.SSH_VERSION_ERROR:
                self.method = 'ssh_1'
                return self.__login()
            else:
                raise

    def __login(self):
        ip = self.ip
        method = self.method
        username = self.username
        timeout = self.timeout
        password = self.password
        enable_password = self.enable_password
        port = self.port
        device_type = 'cisco'

        child = self.child
        try:
            if method == 'telnet':
                port = port or 23
                cmd_str = self.TELNET_STR % (ip, port)
            elif method == 'ssh':
                port = port or 22
                cmd_str = self.SSH_STR % (port, username, ip)
            else:
                port = port or 22
                cmd_str = self.SSH_V1_STR % (port, username, ip)
            self.logger.info('%s %s as %s' % (method, ip, username))
            child = pexpect.spawn(cmd_str,
                                  maxread=8192,
                                  searchwindowsize=4096,
                                  env={"TERM": "dumb"})

            first_pattern = ['.*sername:',
                             '.*assword:',
                             '.*(yes/no)',
                             '.*>',
                             pexpect.TIMEOUT,
                             pexpect.EOF]
            i = child.expect(first_pattern, timeout=timeout)
            if i == 4:
                raise LoginException(LoginException.LOGIN_TIMEOUT)
            if i == 5:
                raise LoginException(LoginException.CONNECTION_CLOSED)
            if i < 3:
                if i == 0:
                    child.sendline(username)
                    child.expect(['.*assword:'], timeout=timeout)
                elif i == 2:
                    child.sendline('yes')
                    child.expect(['.*assword:'], timeout=timeout)
                child.sendline(password)
                second_pattern = ['.*sername:',
                                  '.*assword:',
                                  '.*>',
                                  '.*#',
                                  pexpect.TIMEOUT,
                                  pexpect.EOF]
                i = child.expect(second_pattern, timeout=timeout)
                if i < 2:
                    raise LoginException(LoginException.LOGIN_FAILED)
                if i == 4:
                    raise LoginException(LoginException.LOGIN_TIMEOUT)
                if i == 5:
                    raise LoginException(LoginException.CONNECTION_CLOSED)
                prompt = second_pattern[i][-1]
            else:
                prompt = first_pattern[i][-1]

            if prompt == '>' and enable_password:  # user mode
                child.sendline('enable')
                i = child.expect(['.*assword:', '>'], timeout=5)
                if i == 0:
                    child.sendline(enable_password)
                    third_pattern = ['.*assword:',
                                     '.*#',
                                     pexpect.TIMEOUT,
                                     pexpect.EOF]
                    i = child.expect(third_pattern, timeout=timeout)
                    if i == 0:
                        raise LoginException(LoginException.ENABLE_FAILED)
                    if i == 2:
                        raise LoginException(LoginException.LOGIN_TIMEOUT)
                    if i == 3:
                        raise LoginException(LoginException.CONNECTION_CLOSED)
                    prompt = '#'
                elif i == 1:
                    prompt = '>'

            if prompt == '#':
                # child.sendline('terminal pager 0')
                child.sendline('terminal length 0')
                child.expect('terminal length 0', timeout=timeout)
            else:
                child.sendline('')
            child.expect(prompt, timeout=timeout)
            self.prompt = last_line = ''.join(
                (child.before.splitlines()[-1].decode('utf-8'), prompt))
            if ':' in last_line and 'RP' in last_line:  # IOX
                hostname = last_line.split(':')[-1][:-1]
            elif ':' in last_line:  # BROCADE
                device_type = 'brocade'
                hostname = last_line.split(':')[0]
            else:
                hostname = last_line[:-1]
            self.hostname = hostname

            self.child = child
            self.logger.info('%s %s success. Got hostname: %s' % (method,
                                                                  ip,
                                                                  hostname))
            self.expect_pattern = ['.*\r\n',
                                   pexpect.TIMEOUT,
                                   pexpect.EOF,
                                   re.escape(self.prompt)]
            if device_type == 'cisco':
                self.expect_pattern.extend([
                    '\)#',
                    'fex-\d+#',
                    '\[[yn]\]',
                    '[pP]assword:',
                    '\[confirm\]',
                    '\]\?',
                    ])
            elif device_type == 'brocade':
                self.expect_pattern.extend([
                    '\): ',
                    'Name: ',
                    'Password: ',
                    'Directory: ',
                    ' \[Y\]:'])
            if self.extra_prompts:
                extra_prompts = [re.escape(p) for p in self.extra_prompts]
                self.expect_pattern.extend(extra_prompts)
            return self.prompt
        except LoginException as e:
            if (self.method == 'ssh') and (b'versions differ' in child.before):
                raise LoginException(LoginException.SSH_VERSION_ERROR)
            else:
                child.close()
                self.logger.warning('%s %s failed: %s' %
                                    (method, ip, e.err_msg))
                raise Exception(e.err_msg)
        except pexpect.exceptions.EOF:
            if (self.method == 'ssh') or (b'versions differ' in child.before):
                raise LoginException(LoginException.SSH_VERSION_ERROR)
        except:
            raise

    def execute(self, command):
        expect_pattern = self.expect_pattern
        child = self.child
        res = []
        timeout = self.timeout
        self.logger.info('%s execute: %s' % (self.ip, command))
        child.sendline(command)
        while True:
            c = child.expect(expect_pattern, timeout=timeout)
            res.append(child.before.decode('utf-8'))
            try:
                res.append(str(child.after.decode('utf-8')))
            except:
                break
            if c > 0:
                break
        output = ''.join(res)
        if c == 1:
            status = 'Timeout'
            self.logger.error('Timeout execute: %s @ %s' % (command, self.ip))
        elif self.error_sign in output:
            status = 'Error'
        else:
            status = 'Ok'
        timestamp = strftime('%Y-%m-%d %H:%M:%S')
        return dict(command=command, status=status, output=output, timestamp=timestamp)

    def close(self):
        try:
            self.child.sendline('end')
            self.child.sendline('exit')
            self.child.expect([pexpect.EOF, pexpect.TIMEOUT])
            self.child.close()
            self.logger.info('Disconnected from %s' % self.ip)
        except:
            pass
