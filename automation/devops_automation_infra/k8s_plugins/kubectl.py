import kubernetes
from kubernetes.client import ApiClient

from devops_automation_infra.plugins.tunnel_manager import TunnelManager
from devops_automation_infra.k8s_plugins.k8s_master import K8SMaster
from infra.model import cluster_plugins


class Kubectl:
    def __init__(self, cluster):
        self._cluster = cluster
        self._master = self._cluster.K8SMaster()

    @property
    def _tunnel(self):
        ssh = self._master.SshDirect
        svc_ip = ssh.execute('sudo kubectl get svc kubernetes -o jsonpath={.spec.clusterIP}')
        svc_port = ssh.execute('sudo kubectl get svc kubernetes -o jsonpath={.spec.ports[0].port}')
        tunnel = self._master.TunnelManager.get_or_create('kubectl', svc_ip, svc_port, ssh.get_transport())
        return tunnel

    def _create_config(self, **kwargs):
        ssh = self._master.SshDirect
        api_token = kwargs.pop("api_token",
                               ssh.execute('''sudo kubectl get secrets -n kube-system -o jsonpath="{.items[?(@.metadata.annotations['kubernetes\.io/service-account\.name']=='default')].data.token}"|base64 --decode'''))
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

    def verify_functionality(self):
        api = kubernetes.client.CoreV1Api(self.client())
        res = api.list_pod_for_all_namespaces(watch=False)
        for i in res.items:
            print("%s\t%s\t%s" % (i.status.pod_ip, i.metadata.namespace, i.metadata.name))


cluster_plugins.register('Kubectl', Kubectl)

