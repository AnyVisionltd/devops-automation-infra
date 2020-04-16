import json

from automation_infra.plugins.ssh_direct import SshDirect
from automation_infra.utils.waiter import wait_for_predicate, wait_for_predicate_nothrow
from infra.model import plugins
from pytest_automation_infra.helpers import hardware_config


class Gravity(object):

    def __init__(self, host):
        self._host = host

    def status(self):
        return json.loads(self._host.SshDirect.execute("sudo gravity status --output json"))

    def is_cluster_healthy(self):
        return self.number_healthy_nodes() == len(self.nodes())

    def number_healthy_nodes(self, number_nodes_required=None):
        nodes = self.nodes()
        health_nodes_number = [node['status'] for node in nodes if node['status'] == "healthy"]
        return len(health_nodes_number)

    def nodes(self):
        res = self.status()
        return res['cluster']['nodes']

    def join_cluster(self, master_ip, join_token):
        download_path = "/usr/local/bin/gravity"
        download_cmd = f"sudo curl -k -H \"Authorization: Bearer {join_token}\" https://{master_ip}:32009/portal/v1/gravity -o {download_path}"

        self.download_gravity(download_cmd)
        self.gravity_make_executable(download_path)

        self.join(master_ip, join_token)
        wait_for_predicate_nothrow(lambda: self.is_cluster_healthy(), timeout=600, interval=10)

    @property
    def token(self):
        res = self.status()
        return res['cluster']['token']['token']

    @property
    def master_ip(self):
        res = self.status()
        return res['cluster']['nodes'][0]['advertise_ip']

    def download_gravity(self, download_request):
        self._host.SshDirect.execute(download_request)

    def gravity_make_executable(self, gravity_path):
            self._host.SshDirect.execute(f"sudo chmod +x {gravity_path}")

    def join(self, master_ip, join_token, role='node', cloud_provider='generic'):
        self._host.SshDirect.execute(f'sudo gravity join {master_ip} --token={join_token} --role={role} --cloud-provider={cloud_provider}')


plugins.register('Gravity', Gravity)
