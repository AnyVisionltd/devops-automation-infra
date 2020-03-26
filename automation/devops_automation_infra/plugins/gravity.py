import json

from automation_infra.plugins.ssh_direct import SshDirect
from infra.model import plugins


class Gravity(object):

    def __init__(self, host):
        self._host = host

    def status(self):
        return json.loads(self._host.SshDirect.execute("sudo gravity status --output json"))

    def is_cluster_healthy(self):
        res = self.status()
        all_nodes = res['cluster']['nodes']
        health_nodes_number = [node['status'] for node in all_nodes if node['status'] == "healthy"]
        return True if len(health_nodes_number) == len(all_nodes) else False

    def number_healthy_nodes(self, number_nodes_required=None):
        res = self.status()
        nodes = res['cluster']['nodes']
        health_nodes_number = [node['status'] for node in nodes if node['status'] == "healthy"]
        return len(health_nodes_number)


plugins.register('Gravity', Gravity)

