import requests

from infra.model import cluster_plugins


class JetsonStats(object):
    def __init__(self, cluster):
        self._cluster = cluster
        self._hardware_stats_port = "8000"
        self._pipe_stats_port = "9999"
        self._hardware_stats_name = "HardwareStats"
        self._pipe_stats_name = "PipeStats"

    @property
    def hardware_stats_url(self):
        return f"{self._cluster.hosts.host2.ip}:{self._hardware_stats_port}"

    @property
    def pipe_stats_url(self):
        return f"{self._cluster.hosts.host2.ip}:{self._pipe_stats_port}/metrics"

    def hardware_stats(self):
        return requests.get(f'http://{self.hardware_stats_url}').text.split('\n')

    def pipe_stats(self):
        return requests.get(f'http://{self.pipe_stats_url}').text.split('\n')


cluster_plugins.register('JetsonStats', JetsonStats)
