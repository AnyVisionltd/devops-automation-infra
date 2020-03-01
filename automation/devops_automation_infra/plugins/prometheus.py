import json

from prometheus_http_client import Prometheus

from devops_automation_infra.utils.config import prometheus_connection_config
from automation_infra.plugins.base_plugin import TunneledPlugin
from infra.model import plugins


class PrometheusService(TunneledPlugin):
    def __init__(self, host):
        super().__init__(host)
        self.DNS_NAME = host.ip
        self.PORT = prometheus_connection_config['port']
        self.start_tunnel(self.DNS_NAME, self.PORT)
        self._prom = Prometheus(url=f'http://localhost:{self.local_bind_port}')

    def query(self, query):
        return json.loads(self._prom.query(metric=query))


plugins.register('PrometheusService', PrometheusService)