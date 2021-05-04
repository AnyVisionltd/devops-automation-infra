import logging

from automation_infra.utils import waiter
from infra.model import cluster_plugins
from automation_infra.plugins.ssh_direct import SshDirect


class K8SMaster:
    def __init__(self, cluster):
        self._cluster = cluster

    def __call__(self):
        masters = self.list_masters()
        if len(masters) > 0:
            return next(iter(masters))
        else:
            raise Exception("Couldn't find running masters nodes")

    def list_masters(self):
        masters = []
        for host in self._cluster.hosts.values():
            try:
                waiter.wait_nothrow(lambda: host.SshDirect.execute("sudo kubectl get po"), timeout=150)
                masters.append(host)
            except:
                continue
        return masters


cluster_plugins.register('K8SMaster', K8SMaster)
