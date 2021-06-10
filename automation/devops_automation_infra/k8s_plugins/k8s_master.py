from infra.model import cluster_plugins
from automation_infra.plugins.ssh_direct import SshDirect
from automation_infra.utils import concurrently, waiter
from functools import partial

class K8SMaster:
    def __init__(self, cluster):
        self._cluster = cluster

    def __call__(self):
        jobs = {host.ip:
                partial(self._kubectl, host)
                for host in self._cluster.hosts.values()}

        bg = concurrently.Background(jobs)
        bg.start()
        master_ip = next(iter(bg.wait(return_when=concurrently.Completion.WAIT_FIRST_SUCCESS).keys()))
        master = next(host for host in self._cluster.hosts.values() if host.ip == master_ip)
        if not master:
            raise Exception("Couldn't find running masters nodes")

        return master


    def _kubectl(self, host):
        return waiter.wait_nothrow(lambda: host.SshDirect.execute("sudo kubectl get po"), timeout=150)

cluster_plugins.register('K8SMaster', K8SMaster)
