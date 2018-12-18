# __author__ = 'zhutong'

import time

from modules.worker_base import BaseWorker, main, logging
from modules.snmp_helper import SNMP


class Worker(BaseWorker):
    channel = 'snmp'
    name = 'SNMP'

    def handler(self, task_id, params):
        ip = params['ip']
        community = params['community']
        commands = params['commands']
        operate = commands['operate']
        oids = [str(o).strip('.') for o in commands['oids']]

        logging.info('%s for %s started', operate.upper(), ip)
        worker = SNMP(ip,
                      community,
                      logger=logging,
                      port=commands.get('port', 161),
                      timeout=commands.get('timeout', 5),
                      retries=commands.get('retries', 1),
                      non_repeaters=commands.get('non_repeaters', 0),
                      max_repetitions=commands.get('max_repetitions', 25))
        try:
            if operate == 'get':
                snmp_fun = worker.get
            elif operate == 'walk':
                snmp_fun = worker.walk
            elif operate == 'bulk_walk':
                snmp_fun = worker.bulk_walk
            else:
                return dict(task_id=task_id,
                            status='error',
                            message='Not support SNMP operate')
            logging.info('%s for %s finished', operate.upper(), ip)
            result = snmp_fun(*oids)
        except Exception as e:
            return dict(task_id=task_id,
                        status='error',
                        message=str(e))

        return result


main(Worker)
