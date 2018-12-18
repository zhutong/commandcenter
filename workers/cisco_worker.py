# encoding: utf-8

from time import sleep

from modules.worker_base import BaseWorker, main, logging
from modules.cisco_cli_helper import CiscoCLI


class Worker(BaseWorker):
    channel = 'cisco'
    name = channel.upper()

    def handler(self, task_id, params):
        commands = params['commands']
        given_name = params.get('hostname', '')
        wait_seconds = params.get('wait', 0)
        output = []

        cli = CiscoCLI(params, logging)
        try:
            cli.login()
            hostname = cli.hostname
            if given_name and given_name != hostname:
                message = 'Hostname not match. Given: %s, Got: %s' % (
                    given_name, hostname)
                raise Exception(message)
            else:
                status = 'success'
                message = ''
            for cmd in commands:
                cmd_out = cli.execute(cmd)
                output.append(cmd_out)
                sleep(wait_seconds)
        except Exception as e:
            status = 'fail'
            message = str(e)
            hostname = given_name
        finally:
            cli.close()

        return dict(status=status,
                    message=message,
                    hostname=hostname,
                    output=output)


if __name__ == '__main__':
    main(Worker)
