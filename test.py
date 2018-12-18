import time
import sys

import requests
from multiprocessing.dummy import Pool


def snmp(r):
    oids = (
        '1.3.6.1.2.1.1.1.0',  # sysDescr
        '1.3.6.1.2.1.1.2.0',  # sysObjectID
        '1.3.6.1.2.1.1.3.0',  # sysUpTime
        '1.3.6.1.2.1.1.5.0',  # sysName
    )
    data = dict(hostname='R001',
                commands=dict(operate='get',
                              oids=oids))
    res = requests.post(snmp_url, json=data)
    print(res.json())


def cisco(i):
    res = requests.post(cli_url,
                        json=dict(commands=['show ip route', 'show ver'],
#                                  channel='test',
                                  ip='192.168.12.101'),
                        timeout=1000)
    print(res.json())
    print('%06d finished @ %s, %d bytes' %
          (i, time.strftime('%H:%M:%S'), len(res.text)))


try:
    n = int(sys.argv[1])
except:
    n = 10
try:
    ip = sys.argv[2]
except:
    ip = '127.0.0.1'

cli_url = 'http://%s:8080/api/v1/sync/cli' % ip
snmp_url = 'http://%s:8080/api/v1/sync/snmmp' % ip
s = time.time()
pool = Pool(50)
# pool.map(snmp, range(2))
pool.map(cisco, range(n))
print('Spend %d s' % int(time.time()-s))
