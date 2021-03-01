from devops_automation_infra.k8s_plugins.k8s_master import K8SMaster
from infra.model import cluster_plugins


class Gravity:
    def __init__(self, cluster):
        self._cluster = cluster
        self._master = self._cluster.K8SMaster()

    def exec(self, command):
        return self._master.SshDirect.execute(f"sudo gravity exec {command}")


cluster_plugins.register('Gravity', Gravity)