import json

from automation_infra.plugins.ssh_direct import SshDirect
from infra.model import plugins


class Gravity(object):

    def __init__(self, host):
        self._host = host

    def status(self):
        return json.loads(self._host.SshDirect.execute("sudo gravity status --output json"))

    def number_healthy_nodes(self, number_nodes_required=None):
        res = self.status()
        nodes = res['cluster']['nodes']
        total_number_nodes = len(nodes)
        health_nodes_number = [node['status'] for node in nodes if node['status'] == "healthy"]
        if number_nodes_required:
            return True if len(health_nodes_number) == number_nodes_required else False
        return True if len(health_nodes_number) == total_number_nodes else False


plugins.register('Gravity', Gravity)

