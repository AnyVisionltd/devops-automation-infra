import logging
from contextlib import closing
import pymysql

from infra.model import cluster_plugins
from pytest_automation_infra import helpers
from pymysql.constants import CLIENT
import copy
from automation_infra.utils import waiter
from devops_automation_infra.k8s_plugins.kubectl import Kubectl
from devops_automation_infra.utils import kubectl as kubectl_utils
import json

class Memsql(object):
    def __init__(self, cluster):
        self.DNS_NAME = 'memsql.default.svc.cluster.local'
        self.PORT = 3306
        self._cluster = cluster

    @property
    def _master(self):
        return self._cluster.K8SMaster()

    @property
    def _tunnel(self):
        return self._master.TunnelManager.get_or_create('memsql', self.DNS_NAME, self.PORT)

    def connection(self, database=None, **kwargs):
        host, port = self._tunnel.host_port
        return self._create_connection(host=host,
                                       port=port,
                                       cursorclass=pymysql.cursors.DictCursor,
                                       client_flag=CLIENT.MULTI_STATEMENTS,
                                       database=database,
                                       **kwargs)

    @property
    def password(self):
        return kubectl_utils.get_secret_data(self._cluster.Kubectl.client(), namespace="default", name='memsql-secret', path='password')

    def _create_connection(self, **kwargs):
        memsql_kwargs = copy.copy(kwargs)
        memsql_kwargs['password'] = self.password.decode()
        memsql_kwargs.setdefault('user', 'root')
        memsql_kwargs.setdefault('client_flag', CLIENT.MULTI_STATEMENTS)
        memsql_kwargs.setdefault('cursorclass', pymysql.cursors.DictCursor)
        return pymysql.connect(**memsql_kwargs)

    def ping(self):
        try:
            nodes_status = json.loads(self._host.Docker.run_cmd_in_service('memsql', 'gosu memsql memsql-admin list-nodes --json'))
        except Exception as e:
            raise Exception("Failed to execute node-status command") from e
        else:
            if not all([node['processState'] == 'Running' and node['isConnectable'] and node['recoveryState'] == 'Online'
                        for node in  nodes_status['nodes']]):
                raise Exception(f"memsql is not ready {nodes_status}")

    def verify_functionality(self):
        dbs = self.fetch_all("show databases")


cluster_plugins.register('Memsql', Memsql)
