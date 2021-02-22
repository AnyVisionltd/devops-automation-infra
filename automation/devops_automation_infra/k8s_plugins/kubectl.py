import kubernetes
from kubernetes.client import ApiClient
import cluster_plugins_library


class Kubectl:
    def __init__(self, cluster):
        self._cluster = cluster
        self._master = self._cluster.master

    @property
    def _tunnel(self):
        ssh = self._master.SshDirect
        svc_ip = ssh.execute('kubectl get svc kubernetes -o jsonpath={.spec.clusterIP}')
        svc_port = ssh.execute('kubectl get svc kubernetes -o jsonpath={.spec.ports[0].port}')
        tunnel = self._master.TunnelManager.get_or_create('kubectl', svc_ip, svc_port)
        return tunnel

    @property
    def _config(self, **kwargs):
        ssh = self._master.SshDirect
        api_token = ssh.execute('''kubectl get secrets -n kube-system -o jsonpath="{.items[?(@.metadata.annotations['kubernetes\.io/service-account\.name']=='default')].data.token}"|base64 --decode''')
        tunnel = self._tunnel()
        config = kubernetes.client.Configuration()
        config.host = f"https://{tunnel.host_port[0]}:{tunnel.host_port[1]}"
        config.verify_ssl = False
        config.api_key["authorization"] = api_token
        config.api_key_prefix['authorization'] = 'Bearer'
        for k, v in kwargs.items():
            setattr(config, k, v)
        return config

    def _client(self, configuration):
        return ApiClient(configuration)

    def _api(self, client):
        return kubernetes.client.CoreV1Api(client)

    def api(self, **kwargs):
        config = self._config(**kwargs)
        client = self._client(config)
        api = self._api(client)
        return api

    def verify_functionality(self):
        api = self.api()
        res = api.list_pod_for_all_namespaces(watch=False)
        for i in res.items:
            print("%s\t%s\t%s" % (i.status.pod_ip, i.metadata.namespace, i.metadata.name))


cluster_plugins_library.register('Kubectl', Kubectl)