import logging
import os, yaml
import subprocess

from kubernetes.client import ApiException

from automation_infra.utils import waiter
from devops_automation_infra.plugins.tunnel_manager import TunnelManager
from infra.model import cluster_plugins
import kubernetes
from automation_infra.plugins.ssh_direct import SshDirect, SSHCalledProcessError

def _memoize(function):
    from functools import wraps
    memo = {}

    @wraps(function)
    def wrapper(*args):
        if args in memo:
            return memo[args]
        else:
            rv = function(*args)
            memo[args] = rv
            return rv

    return wrapper


class ProxyDaemonSet(object):

    def __init__(self, cluster):
        self._cluster = cluster
        self._ssh_direct = self._cluster.master.SshDirect
        self.ds_name = 'automation-proxy-daemonset'
        self._k8s_client = None

    @_memoize
    def _automation_proxy_version(self):
        ds_version = os.environ.get("PROXY_DAEMONSET_VERSION", "")
        if ds_version:
            return ds_version
        version_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../../proxy_container/version.sh")
        return subprocess.check_output([version_file]).split()[0].decode()


    @property
    def running(self): # TODO: Maybe in future verify pod is not running via SSHDirect
        try:
            self.k8s_v1_client.read_namespaced_daemon_set(name=self.ds_name, namespace='default')
        except ApiException as e:
            if e.status == 404:
                return False
            else:
                raise e
        return True

    @property
    def k8s_v1_client(self):
        if not self._k8s_client:
            self._k8s_client = kubernetes.client.AppsV1Api(self._cluster.Kubectl.client())
        return self._k8s_client

    def run(self):
        self.kill()
        logging.debug("Deploying automation-proxy DaemonSet")
        with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "../../proxy_container/daemonset.yaml")) as f:
            ds_yaml = yaml.safe_load(f)
        ds_yaml['spec']['template']['spec']['containers'][0]['image'] = f'gcr.io/anyvision-training/automation-proxy:{self._automation_proxy_version()}'
        try:
            res = self.k8s_v1_client.create_namespaced_daemon_set(namespace="default", body=ds_yaml)
        except ApiException as e:
            logging.exception("Exception when calling AppsV1Api->create_namespaced_daemon_set: %s\n" % e)

        waiter.wait_nothrow(lambda: self._num_ready_pods() == len(self._cluster.hosts), timeout=30)
        logging.debug(f"Deployment created. status={res.metadata.name}")

    def kill(self):
        #import ipdb; ipdb.set_trace()
        if not self.running:
            logging.debug("nothing to remove")
            return
        logging.debug("trying to remove automation-proxy daemonset")
        try:
            self.k8s_v1_client.delete_namespaced_daemon_set(name=self.ds_name, namespace='default')
        except ApiException as e:
            logging.exception("Exception when calling AppsV1Api->create_namespaced_daemon_set: %s\n" % e)
        waiter.wait_for_predicate(lambda: not self.running)
        for host in self._cluster.hosts.values():
            host.TunnelManager.clear(all=False)
        logging.debug("removed successfully!")

    def restart(self):
        self.run()

    def _num_ready_pods(self):
        return self.k8s_v1_client.read_namespaced_daemon_set(name=self.ds_name, namespace="default").status.number_ready


cluster_plugins.register("ProxyDaemonSet", ProxyDaemonSet)
