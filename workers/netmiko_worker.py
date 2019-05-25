# encoding: utf-8

from time import strftime, sleep
from netmiko import ConnectHandler

from modules.worker_base import BaseWorker, main, logging


class Worker(BaseWorker):
    channel = 'netmiko'
    name = channel.upper()

    def handler(self, task_id, params):
        commands = params['commands']
        given_name = params.get('hostname')
        ip = params.get('ip')
        host = ip or given_name
        u = params['username']
        p = params['password']
        s = params.get('enable_password', '')
        t = params['device_type']
        wait_seconds = params.get('wait', 0.1)
        output = []

        try:
            cli = ConnectHandler(ip=ip,
                                 device_type=t,
                                 username=u,
                                 password=p,
                                 secret=s)
            hostname = cli.base_prompt
            logging.info('%s connected', host)
            if given_name and given_name != hostname:
                message = 'Hostname not match. Given: %s, Got: %s' % (
                    given_name, hostname)
                raise Exception(message)
            else:
                status = 'success'
                message = ''
            for cmd in commands:
                logging.info('%s excute: %s', hostname, cmd)
                try:
                    text = cli.send_command(cmd)
                    status = 'Ok'
                except expression as identifier:
                    status = 'Error'
                timestamp = strftime('%Y-%m-%d %H:%M:%S')
                cmd_out = dict(command=cmd,
                               status=status,
                               output=text,
                               timestamp=timestamp)
                output.append(cmd_out)
                sleep(wait_seconds)
        except Exception as e:
            status = 'fail'
            message = str(e)
            hostname = given_name
        finally:
            cli.disconnect()
            logging.info('Disconnected from %s' % host)

        return dict(status=status,
                    message=message,
                    hostname=hostname,
                    output=output)


if __name__ == '__main__':
    main(Worker)
