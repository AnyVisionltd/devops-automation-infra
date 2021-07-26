import redis

from devops_automation_infra.plugins import tunnel_manager
from infra.model import cluster_plugins


class Redis(object):

    def __init__(self, cluster):
        self._cluster = cluster

    @property
    def _master(self):
        return self._cluster.K8SMaster()

    @property
    def _tunnel(self):
        master = self._master
        return master.TunnelManager.get_or_create('redis', dns_name="redis-master", port=6379,
                                                  transport=master.SSH.get_transport())

    def create_client(self, db=0):
        return redis.Redis(host="127.0.0.1", port=self._tunnel.local_port, db=db)


cluster_plugins.register('Redis', Redis)