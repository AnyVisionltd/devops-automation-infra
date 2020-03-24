import json

from base64 import b64encode
from prometheus_http_client import Prometheus

from devops_automation_infra.utils.config import prometheus_connection_config
from automation_infra.plugins.base_plugin import TunneledPlugin
from pytest_automation_infra import helpers
from infra.model import plugins


class PrometheusService(TunneledPlugin):
    def __init__(self, host):
        super().__init__(host)
        self.is_k8s = helpers.is_k8s(self._host.SshDirect)
        self.DNS_NAME = host.ip if not self.is_k8s else prometheus_connection_config['host']['k8s']
        self.PORT = prometheus_connection_config['port']['compose'] if not self.is_k8s \
            else prometheus_connection_config['port']['k8s']
        self.start_tunnel(self.DNS_NAME, self.PORT)
        self.url = f'{prometheus_connection_config["url"]["compose"]}:{self.local_bind_port}' if not self.is_k8s \
            else prometheus_connection_config['url']['k8s']
        self.headers = None if not self.is_k8s \
            else {'Authorization': f'Basic {prometheus_connection_config["auth"]}'}
        self._prom = Prometheus(url=self.url, headers=self.headers)

    def query(self, query):
        return json.loads(self._prom.query(metric=query))


plugins.register('PrometheusService', PrometheusService)