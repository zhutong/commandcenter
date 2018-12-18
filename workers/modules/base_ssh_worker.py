# -*- coding: utf-8 -*-

__version__ = 0.5
__author__ = 'zhutong <zhtong@cisco.com>'

from .worker_base import BaseWorker, main, logging
from .ssh_helper import SSH


class SSHWorker(BaseWorker):

    def handler(self, task_id, params):
        commands = params['commands']
        given_name = params.get('hostname', '')
        wait_seconds = params.get('wait', 0)
        output = []

        worker = SSH(params,
                     logging,
                     self.prompt_list,
                     self.hostname_pattern,
                     self.no_pager_list,
                     self.error_sign)
        try:
            hostname = worker.login()
            if given_name and given_name != hostname:
                message = 'Hostname not match. Given: %s, Got: %s' % (
                    given_name, hostname)
                raise Exception(message)
            else:
                status = 'success'
                message = ''
            for cmd in params['commands']:
                output.append(worker.execute(cmd))
            status = 'success'
            message = ''
        except Exception as e:
            status = 'fail'
            hostname = given_name
            message = str(e)
        finally:
            worker.close()

        return dict(status=status,
                    hostname=hostname,
                    message=message,
                    output=output)
