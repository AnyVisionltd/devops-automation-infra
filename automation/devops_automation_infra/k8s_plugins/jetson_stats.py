import requests

from infra.model import cluster_plugins


class JetsonStats(object):
    def __init__(self, cluster):
        self._cluster = cluster
        self._port = "8000"
        self._name = "JetsonStats"

    @property
    def base_url(self):
        return f"{self._cluster.hosts.host2.ip}:{self._port}"

    def all_stats(self):
        return requests.get(f'http://{self.base_url}').text.split('\n')


cluster_plugins.register('JetsonStats', JetsonStats)
