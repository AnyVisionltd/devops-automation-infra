import base64

import kubernetes
from kubernetes.client import ApiClient
from kubernetes.stream import stream

from devops_automation_infra.plugins.tunnel_manager import TunnelManager
from infra.model import cluster_plugins


class Kubectl:
    def __init__(self, cluster):
        self._cluster = cluster
        self._master = self._cluster.master

    @property
    def _tunnel(self):
        ssh = self._master.SshDirect
        svc_ip = ssh.execute('kubectl get svc kubernetes -o jsonpath={.spec.clusterIP}')
        svc_port = ssh.execute('kubectl get svc kubernetes -o jsonpath={.spec.ports[0].port}')
        tunnel = self._master.TunnelManager.get_or_create('kubectl', svc_ip, svc_port, ssh.get_transport())
        return tunnel

    def _create_config(self, **kwargs):
        ssh = self._master.SshDirect
        api_token = kwargs.pop("api_token",
                               ssh.execute('''kubectl get secrets -n kube-system -o jsonpath="{.items[?(@.metadata.annotations['kubernetes\\.io/service-account\\.name']=='default')].data.token}"|base64 --decode'''))
        tunnel = self._tunnel
        config = kubernetes.client.Configuration()
        config.host = f"https://{tunnel.local_endpoint}"
        config.verify_ssl = kwargs.pop("verify_ssl", False)
        config.api_key["authorization"] = api_token
        config.api_key_prefix['authorization'] = 'Bearer'
        for k, v in kwargs.items():
            setattr(config, k, v)
        return config

    def client(self, **kwargs):
        config = self._create_config(**kwargs)
        return ApiClient(config)

    def v1api(self):
        return kubernetes.client.CoreV1Api(self.client())

    def verify_functionality(self):
        api = kubernetes.client.CoreV1Api(self.client())
        res = api.list_pod_for_all_namespaces(watch=False)
        for i in res.items:
            print("%s\t%s\t%s" % (i.status.pod_ip, i.metadata.namespace, i.metadata.name))


cluster_plugins.register('Kubectl', Kubectl)

