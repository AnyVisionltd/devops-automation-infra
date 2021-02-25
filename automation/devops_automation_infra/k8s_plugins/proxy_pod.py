import logging
import os, yaml
import subprocess

from kubernetes.client import ApiException

from automation_infra.utils import waiter
from infra.model import cluster_plugins
import kubernetes
from automation_infra.plugins.ssh_direct import SshDirect, SSHCalledProcessError

class ProxyPod(object):

    def __init__(self, cluster):
        self._cluster = cluster
        self._ssh_direct = self._cluster.master.SshDirect
        self.ds_name = 'automation-proxy-daemonset'
        self.k8s_v1_client = kubernetes.client.CoreV1Api(self._cluster.Kubectl.client())

    @property
    def running(self):
        try:
            self.k8s_v1_client.read_namespaced_daemon_set(name=self.ds_name, namespace='default')
        except ApiException as e:
            if e.status == 404:
                return False
            else:
                raise e
        return True

    def restart(self):
        self.run()


cluster_plugins.register("ProxyPod", ProxyPod)
