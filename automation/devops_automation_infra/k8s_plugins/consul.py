import json
import base64
import consul
from infra.model import cluster_plugins
from pytest_automation_infra import helpers
from automation_infra.utils import waiter
from devops_automation_infra.k8s_plugins.kubectl import Kubectl
from devops_automation_infra.utils import container
from devops_automation_infra.utils import kubectl


class Consul(object):
    def __init__(self, cluster):
        self._cluster = cluster
        self.NAME = "consul-server"
        self.DNS_NAME = f'{self.NAME}.default.svc.cluster.local'
        self.URI = "/consul"
        self.PORT = 8500

    @property
    def _master(self):
        return self._cluster.K8SMaster()

    @property
    def _tunnel(self):
        return self._master.TunnelManager.get_or_create('consul', self.DNS_NAME, self.PORT)

    def create_client(self):
        host, port = self._tunnel.host_port
        return consul.Consul(host, port)

    def clear_data(self):
        client = self._cluster.Kubectl.client()
        kubectl.delete_stateful_set_data(client, self.NAME)
        kubectl.delete_pods_by_label(client, label="app=consul, component=client")
        waiter.wait_for_predicate(lambda: kubectl.is_daemon_set_ready(client, "consul"), timeout=60)


cluster_plugins.register('Consul', Consul)

