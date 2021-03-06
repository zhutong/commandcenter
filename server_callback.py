import json
import logging
from threading import Thread
from uuid import uuid4

import zmq
from tornado import options, web
from tornado.log import enable_pretty_logging
from zmq.eventloop import ioloop
from zmq.eventloop.zmqstream import ZMQStream

from config import *
from credential_mgr import CredentialManager

enable_pretty_logging()

ioloop.install()

context = zmq.Context()
active_workers = set()

def get_channel_dict():
    channel_dict = {}
    lines = worker_channel.strip().splitlines()
    for i, l in enumerate(lines):
        for c in l.strip().split():
            channel_dict[c] = WORKER_START_SOCKET_PORT + i
    return channel_dict


def port_query_daemon():
    rep = context.socket(zmq.REP)
    rep.bind("tcp://*:%d" % PORT_DAEMON_SOCKET_PORT)
    while True:
        message = rep.recv_string()
        for c in message.split('::'):
            port = channel_dict.get(c)
            if port:
                active_workers.add(c)
        rep.send_string(str(port))
        logging.info('Worker %s connect' % message)


def install_backends():
    ctx = zmq.Context.instance()
    for p in set(list(channel_dict.values())):
        backend = ctx.socket(zmq.DEALER)
        backend.bind("tcp://*:%d" % p)
        stream = ZMQStream(backend)
        stream.on_recv(write_client)
        backends[p] = backend


def write_client(message):
    task_id, _, payload = message
    try:
        c = clients.get(task_id)
        c.write(payload)
        c.finish()
        logging.info("Task finished: %s", task_id)
    except Exception as e:
        logging.error("Task %s error: %s", task_id, str(e))
    finally:
        del clients[task_id]
        logging.info('Opened tasks: %s', len(clients))


class CommandHandler(web.RequestHandler):

    def __verify_data(self, category, params):
        # verify commands field
        commands = params.get('commands')
        if not commands:
            raise Exception('No valid commands')

        # verify ip
        ip = params.get('ip')
        hostname = params.get('hostname')
        if not (ip or hostname):
            raise Exception('No valid ip or hostname')
        # get credential from local based on ip or hostname
        device = ip or hostname
        device_info_res = credential.get(device)
        # device found in local
        if device_info_res and device_info_res['status'] == 'ok':
            device_info = device_info_res['device_info']
            device_info.update(params)  # update device_info with given params
        else:  # device not found in local
            device_info = params  # just use given params
        # print(device_info)
        if 'ip' not in device_info:
            raise Exception('ip address not found for %s' % hostname)

        # just using common info for device without credential
        if category == 'cli':
            if not device_info.get('password'):
                common = credential.common
                device_info['username'] = common['username']
                device_info['password'] = common['password']
                device_info['enable_password'] = common['enable_password']
            ch = params.get('channel',
                            device_info.get('vendor', 'cisco')).lower()
        elif category == 'snmp':
            if not device_info.get('community'):
                common = credential.common
                device_info['community'] = common['community']
            ch = 'snmp'

        # verify channel
        if ch not in active_workers:
            raise Exception('not supported device type: %s' % ch)

        return device_info, ch

    # @web.asynchronous
    def get(self, category):
        params = {}
        for k, v in self.request.arguments.items():
            if k in ('commands', 'cmd'):
                params['commands'] = [i.decode() for i in v]
            elif k in ('username', 'u'):
                params['username'] = v[0].decode()
            elif k in ('password', 'p'):
                params['password'] = v[0].decode()
            elif k in ('channel', 'ch'):
                params['channel'] = v[0].decode()
            else:
                params[k] = v[0].decode()
        self.process(category, params)

    # @web.asynchronous
    def post(self, category):
        params = json.loads(self.request.body)
        self.process(category, params)

    @web.asynchronous
    def process(self, category, params):
        try:
            device_info, ch = self.__verify_data(category, params)
            task_id = uuid4().hex
            device_info['task_id'] = task_id
            x_real_ip = self.request.headers.get("X-Real-IP")
            remote_ip = x_real_ip or self.request.remote_ip
            logging.info("Request from %s, task: %s", remote_ip, task_id)

            p = channel_dict[ch]
            backends[p].send_multipart(
                [task_id.encode(), b'', json.dumps(device_info).encode()])

            clients[task_id] = self
        except Exception as e:
            reply = dict(status='error', message=str(e))
            self.write(reply)
            self.finish()


class CredentialApiHandler(web.RequestHandler):

    def check_origin(self, origin):
        return True

    def post(self, *args):  # Create
        device_id = args[0]
        self.set_header("Content-Type", "application/json")
        try:
            params = json.loads(self.request.body)
            if not device_id:  # Create multiple devices
                res = credential.create_m(params)
            else:  # Create one device
                res = credential.create(**params)
            credential.save()
            self.write(res)
        except ValueError:
            self.write(dict(status='fail',
                            message='Not valid fields'))

    def get(self, *args):  # Read
        device_id = args[0]
        self.set_header("Content-Type", "application/json")
        self.set_header('Access-Control-Allow-Origin', '*')
        if device_id:
            result = credential.get(device_id, True)
        else:
            result = credential.get_all()
        self.write(result)

    def put(self, *args):  # Update
        device_id = args[0]
        self.set_header("Content-Type", "application/json")
        try:
            params = json.loads(self.request.body)
            if not device_id:  # Update multi devices
                result = credential.update_m(params)
            else:  # Update one device
                result = credential.update(device_id, **params)
            credential.save()
            self.write(json.dumps(result))
        except ValueError:
            self.write(dict(status='fail',
                            message='Not valid fields'))

    def delete(self, *args):  # Delete
        device_id = args[0]
        self.set_header("Content-Type", "application/json")
        if not device_id:
            self.write(credential.delete_all())
        else:
            self.write(credential.delete(device_id))
            credential.save()


class CredentialCommonApiHandler(web.RequestHandler):

    def check_origin(self, origin):
        return True

    def get(self, *args):
        self.set_header("Content-Type", "application/json")
        self.set_header('Access-Control-Allow-Origin', '*')
        self.write(credential.common)

    def put(self, *args):  # Update
        self.set_header("Content-Type", "application/json")
        params = json.loads(self.request.body)
        result = credential.set_common(params)
        credential.save()
        self.write(result)


class DeviceApiHandler(web.RequestHandler):

    def check_origin(self, origin):
        return True

    def get(self, *args):
        q = args[0].lower()
        self.set_header("Content-Type", "application/json")
        self.set_header('Access-Control-Allow-Origin', '*')
        self.write(credential.query(q))


if __name__ == "__main__":
    options.define("p", default=8080, help="Web server port", type=int)
    options.parse_command_line()
    port = options.options.p

    credential = CredentialManager()
    credential.daemon = True
    credential.start()

    channel_dict = get_channel_dict()
    worker_channels = list(channel_dict.keys())

    port_daemon = Thread(target=port_query_daemon)
    port_daemon.daemon = True
    port_daemon.start()

    clients = {}
    backends = {}
    install_backends()

    print('Command Center server started on %s' % port)
    print('Press "Ctrl+C" to exit.\n')
    application = web.Application([
        (r"/api/v1/sync/(cli|snmp|netconf|api)", CommandHandler),
        (r'/api/v1/credential_common/?', CredentialCommonApiHandler),
        (r'/api/v1/credential/?(.*)', CredentialApiHandler),
        (r'/api/v1/device/?(.*)', DeviceApiHandler),
    ], autoreload=True).listen(port)

    try:
        ioloop.IOLoop.instance().start()
    except KeyboardInterrupt:
        print(' Interrupted')
