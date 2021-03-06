PORT_DAEMON_SOCKET_PORT = 16000  # Change this should modify worker_base.py manually
CLIENT_SOCKET_PORT = PORT_DAEMON_SOCKET_PORT + 1
WORKER_START_SOCKET_PORT = PORT_DAEMON_SOCKET_PORT + 10

# Used for threading pool mode only
MAX_WORKERS = 400
PULLER_TIMEOUT = 2 * 3600 * 1000  # 2 hours

DEVICE_LIST_URL = "http://127.0.0.1:9116/apps/device_center/api/get_device_list"

worker_channel = '''
test
snmp
cisco brocade
huawei h3c
f5
netmiko
'''
