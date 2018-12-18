import json
import logging
import time
from threading import Thread

import requests as http_requests

__author__ = 'zhutong'

LOCAL_FILE = 'device_credential.json'


def _filter_device(device, q):
    if q in device.get('hostname', '').lower():
        return True
    if q in device.get('platform', '').lower():
        return True
    if q in device.get('vendor', '').lower():
        return True
    if q in ' '.join(device.get('tag', [''])).lower():
        return True
    return False


class CredentialManager(Thread):
    """
    A very simple credential manager
    """
    common = dict(username='',
                  password='',
                  community='',
                  method='ssh',
                  platform='cisco')
    device_dict = {}
    device_list = []
    renew_interval = 3600
    renew_url = "http://127.0.0.1:9116/apps/device_center/api/get_device_list"

    def query(self, q):
        if not q:
            devices = self.device_list
        else:
            if '|' in q and '&' in q:
                return dict(status='error',
                            message='Not support "&"" and "|"" in one query',
                            devices=[])
            if '|' in q:
                devices = []
                for s in q.split('|'):
                    ds = [d for d in self.device_list if _filter_device(d, s)]
                    devices.extend(ds)
            elif '&' in q:
                devices = self.device_list
                for s in q.split('&'):
                    devices = [d for d in devices if _filter_device(d, s)]
            else:
                devices = [d for d in self.device_list if _filter_device(d, q)]
        return dict(status='ok',
                    devices=devices)

    def create(self, **kwargs):
        if 'ip' not in kwargs:
            return dict(status='error',
                        err_msg='No ip info')

        ip = kwargs['ip']
        if self.device_dict.get(ip):
            return dict(status='error',
                        err_msg='%s already in db. Using update instead.' % ip)

        device = dict(**kwargs)
        self.device_dict[ip] = device
        if 'hostname' in device:
            self.device_dict[device['hostname']] = device

        self.device_list.append(device)
        return dict(status='ok')

    def create_m(self, device_info_list):
        for device_info in device_info_list:
            res = self.create(**device_info)
            if res.get('status', 'error') != 'ok':
                logging.info(res)
        return dict(status='ok')

    def update(self, device_id, **kwargs):
        device = self.device_dict.get(device_id)
        if not device:
            return self.create(**kwargs)
        device.update(**kwargs)
        return dict(status='ok')

    def update_m(self, device_info_list):
        for device_info in device_info_list:
            device_id = device_info['hostname']
            self.update(device_id, **device_info)
        return dict(status='ok')

    def delete(self, device_id):
        device = self.device_dict.get(device_id)
        if device:
            ip = device['ip']
            hostname = device.get('hostname')
            if hostname:
                del self.device_dict[hostname]
            del self.device_dict[device['ip']]
            for d in self.device_list:
                if d['ip'] == ip:
                    self.device_list.remove(d)
                    break
            return dict(status='ok')
        else:
            return dict(status='error',
                        err_msg='Device not found')

    def delete_all(self):
        self.device_dict = {}
        self.device_list = []
        return dict(status='ok')

    def get(self, device_id, common=False):
        params = self.device_dict.get(device_id)
        if not params:
            if common:
                return dict(status='warning',
                            device_info=self.common)
            else:
                return dict(status='error',
                            err_msg='Device not found')
        device = self.common.copy()
        for k in list(params.keys()):
            v = params[k]
            if not v:
                del params[k]
            else:
                try:
                    if v.strip() == '':
                        del params[k]
                except AttributeError:
                    pass
        device.update(params)
        return dict(status='ok',
                    device_info=device)

    def get_all(self):
        all_device = {}
        for device_id in self.device_dict:
            params = self.device_dict.get(device_id)
            device = self.common.copy()
            device.update(params)
            all_device[device_id] = device
        return dict(status='ok',
                    device_info=all_device)

    def get_common(self):
        return dict(status='ok',
                    common=self.common)

    def set_common(self, kwargs):
        self.common.update(**kwargs)
        return dict(status='ok')

    def save(self, filename=LOCAL_FILE):
        try:
            devices = sorted((self.device_list))
            data = dict(common=self.common, devices=devices)
            with open(filename, 'w') as f:
                json.dump(data, f, indent=2)
            return dict(status='ok')
        except Exception as e:
            return dict(status='error',
                        err_msg='Save device credential failed.')

    def __load(self, filename=LOCAL_FILE):
        """Load credential info from file"""
        try:
            with open(filename) as f:
                data = json.load(f)
                self.common.update(data['common'])
                self.create_m(data['devices'])
            return dict(status='ok')
        except Exception as e:
            return dict(status='error',
                        err_msg='Load device credential failed.')

    def run(self):
        # Pull credentials from URL in certain interval
        while True:
            try:
                response = http_requests.get(self.renew_url, timeout=10)
                if response.status_code == 200:
                    result = response.json()
                    if result.get("result") == "success":
                        data = result["data"]
                        logging.info(">> Got common info: %s" %
                                     data.get("common", ""))
                        logging.info(">> Got devices count: %s" %
                                     len(data.get('devices', [])))
                        if data.get('common'):
                            self.common.update(data['common'])
                        self.delete_all()
                        self.create_m(data.get('devices', []))
                        self.save()
                time.sleep(self.renew_interval)
            except Exception as e:
                self.__load()
                logging.error(e.message)
                return dict(status='error',
                            err_msg='Load device credential failed.')
