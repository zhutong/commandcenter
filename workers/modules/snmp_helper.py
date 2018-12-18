# __author__ = 'zhutong'

from pysnmp.entity.rfc3413.oneliner import cmdgen


class SNMP():
    def __init__(self, ip, community, logger,
                 port, timeout, retries,
                 non_repeaters, max_repetitions):
        self.logger = logger
        self.ip = ip
        self.port = port
        self.timeout = timeout
        self.retries = retries
        self.non_repeaters = non_repeaters
        self.max_repetitions = max_repetitions
        self.cmd_gen = cmdgen.CommandGenerator()
        self.community_data = cmdgen.CommunityData(community)
        self.transport_target = cmdgen.UdpTransportTarget((ip, port),
                                                          timeout=timeout,
                                                          retries=retries)

    def get(self, *oid_str):
        cmd_gen = self.cmd_gen
        error_indication, error_status, error_index, var_binds = cmd_gen.getCmd(
            self.community_data,
            self.transport_target,
            *oid_str
        )
        if error_indication:
            self.logger.error('%s: %s', error_indication, self.ip)
            return dict(status='error',
                        message=str(error_indication))
        else:
            if error_status:
                error_msg = error_status.prettyPrint()
                self.logger.error('%s: %s at %s', self.ip, error_msg,
                    error_index and var_binds[-1][int(error_index) - 1] or '?')
                return dict(status='error',
                            message=error_msg)
            else:
                output = []
                for name, val in var_binds:
                    output.append(dict(oid=str(name),
                                       value=val.prettyPrint()))
                return dict(status='success',
                            message='',
                            output=output)

    def walk(self, *oid_str):
        cmd_gen = self.cmd_gen
        error_indication, error_status, error_index, var_bind_table = cmd_gen.nextCmd(
            self.community_data,
            self.transport_target,
            *oid_str
        )
        if error_indication:
            self.logger.error('%s: %s', error_indication, self.ip)
            return dict(status='error',
                        message=str(error_indication))
        else:
            if error_status:
                error_msg = error_status.prettyPrint()
                self.logger.error('%s: %s at %s', self.ip, error_msg,
                    error_index and var_bind_table[-1][int(error_index) - 1] or '?')
                return dict(status='error',
                            message=error_msg)
            else:
                output = []
                for var_bind_row in var_bind_table:
                    row = []
                    for name, val in var_bind_row:
                        row.append((str(name), val.prettyPrint()))
                    if oid_str[0] not in row[0][0]:
                        break
                    output.append(row)

                return dict(status='success',
                            message='',
                            output=output)

    def bulk_walk(self, *oid_str):
        cmd_gen = self.cmd_gen
        error_indication, error_status, error_index, var_bind_table = cmd_gen.bulkCmd(
            self.community_data,
            self.transport_target,
            self.non_repeaters, self.max_repetitions,
            *oid_str
        )
        if error_indication:
            self.logger.error('%s: %s', error_indication, self.ip)
            return dict(status='error',
                        message=str(error_indication))
        else:
            if error_status:
                error_msg = error_status.prettyPrint()
                self.logger.error('%s: %s at %s', self.ip, error_msg,
                    error_index and var_bind_table[-1][int(error_index) - 1] or '?')
                return dict(status='error',
                            message=error_msg)
            else:
                output = []
                for var_bind_row in var_bind_table:
                    row = []
                    for name, val in var_bind_row:
                        row.append((str(name), val.prettyPrint()))
                    if oid_str[0] not in row[0][0]:
                        break
                    output.append(row)

                return dict(status='success',
                            message='',
                            output=output)
