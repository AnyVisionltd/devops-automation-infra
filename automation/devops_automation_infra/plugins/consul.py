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
        self.DEFAULT_KEY = "DEFAULT"
        self.OVERRIDE_KEY = "OVERRIDE"
        self.APPLICATION_KEY = "APPLICATION"

    def get_services(self):
        return self._consul.catalog.services()[1]

    def get_service_nodes(self, service_name):
        return self._consul.catalog.service(service_name)[1]

    def is_healthy(self, service_name, instance_name):
        nodes = self._consul.health.service(service_name)[1]
        for node in nodes:
            if node["Service"]["ID"] == instance_name:
                return "critical" not in [check["Status"] for check in node["Checks"]]
        return False

    def put_key(self, key, val):
        res = self._consul.kv.put(key, val)
        return res

    def update_key_value(self, key, val):
        self._consul.kv.delete(key, recurse=False)
        res = self._consul.kv.put(key, val)
        return res

    def get_key(self, key):
        res = self._consul.kv.get(key)[1]['Value']
        return res

    def delete_key(self, key, recurse=None):
        res = self._consul.kv.delete(key, recurse=recurse)
        return res

    def register_service(self, name, service_id, address, port, check):
        res = self._consul.agent.service.register(name=name, service_id=service_id, address=address, port=port, check=check)
        return res

    def ping_ttl_check(self, check_id):
        self._consul.agent.check.ttl_pass(check_id=check_id)

plugins.register('Consul', Consul)

