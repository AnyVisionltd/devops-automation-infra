import pymysql
from infra.model import cluster_plugins
from pymysql.constants import CLIENT
import copy
from devops_automation_infra.k8s_plugins.kubectl import Kubectl
from devops_automation_infra.utils import kubectl as kubectl_utils


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
        return kubectl_utils.get_secret_data(self._cluster.Kubectl.client(), namespace="default", name='memsql-secret',
                                             path='password')

    def _create_connection(self, **kwargs):
        memsql_kwargs = copy.copy(kwargs)
        memsql_kwargs['password'] = self.password.decode()
        memsql_kwargs.setdefault('user', 'root')
        memsql_kwargs.setdefault('client_flag', CLIENT.MULTI_STATEMENTS)
        memsql_kwargs.setdefault('cursorclass', pymysql.cursors.DictCursor)
        return pymysql.connect(**memsql_kwargs)


cluster_plugins.register('Memsql', Memsql)
