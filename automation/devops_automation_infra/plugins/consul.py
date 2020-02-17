import sshtunnel
import consul
from munch import Munch
from automation_infra.plugins.base_plugin import TunneledPlugin
from infra.model import plugins
from pytest_automation_infra import helpers


class Consul(TunneledPlugin):
    def __init__(self, host):
        super().__init__(host)
        self.DNS_NAME = 'consul.tls.ai' if not helpers.is_k8s(self._host.SSH) else 'consul.default.svc.cluster.local'
        self.PORT = 8500
        self.start_tunnel(self.DNS_NAME, self.PORT)
        self._consul = consul.Consul("localhost", self.local_bind_port)

    def get_services(self):
        return self._consul.catalog.services()[1]

    def get_service_nodes(self, service_name):
        return self._consul.catalog.service(service_name)[1]

    def is_healthy_node(self, node_name):
        checks = self._consul.health.node(node_name)
        return "critical" not in [check["Status"] for check in checks[1]]

    def put_key(self, key, val):
        res = self._consul.kv.put(key, val)
        return res

    def get_key(self, key):
        res = self._consul.kv.get(key)[1]['Value']
        return res

    def delete_key(self, key, recurse=None):
        res = self._consul.kv.delete(key, recurse=recurse)
        return res

plugins.register('Consul', Consul)

