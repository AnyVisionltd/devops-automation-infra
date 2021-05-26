import logging

from automation_infra.utils import waiter
from infra.model import cluster_plugins
from automation_infra.plugins.ssh_direct import SshDirect


class K8SMaster:
    def __init__(self, cluster):
        self._cluster = cluster

    def __call__(self):
        masters = waiter.wait_nothrow(lambda: self.list_masters(), timeout=150)
        if len(masters) > 0:
            return masters[0]
        else:
            raise Exception("Couldn't find running masters nodes")

    def list_masters(self):
        masters = []
        for host in self._cluster.hosts.values():
            try:
                host.SshDirect.execute("sudo kubectl get po")
                masters.append(host)
            except:
                continue
        return masters


cluster_plugins.register('K8SMaster', K8SMaster)
