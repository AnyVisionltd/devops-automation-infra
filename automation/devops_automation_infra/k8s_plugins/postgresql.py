import logging
import psycopg2
import psycopg2.extras

from infra.model import cluster_plugins
from devops_automation_infra.utils import kubectl as kubectl_utils


class Postgresql(object):
    def __init__(self, cluster):
        self._cluster = cluster
        self.DNS = 'postgres.default.svc.cluster.local'
        self.PORT = 5432

    @property
    def _master(self):
        return self._cluster.K8SMaster()

    @property
    def password(self):
        return kubectl_utils.get_secret_data(self._cluster.Kubectl.client(),
                                             namespace="default",
                                             name='postgres-secret',
                                             path='password').decode()

    def connection(self):
        tunnel = self._master.TunnelManager.get_or_create('postgres', self.DNS, self.PORT)
        connection = psycopg2.connect(host=tunnel.host_port[0],
                                      port=tunnel.host_port[1],
                                      user='anv_admin',
                                      password=self.password,
                                      database='anv_db')

        return connection


cluster_plugins.register('Postgresql', Postgresql)

