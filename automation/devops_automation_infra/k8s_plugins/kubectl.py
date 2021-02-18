import kubernetes
from kubernetes.client import ApiClient


class Kubectl:
    def __init__(self, cluster):
        self._cluster = cluster

    def create_kubeconfig(self):
        self._cluster.Gravity.generate_kubectl_config()

    def create_config(self, **kwargs):
        config = kubernetes.client.Configuration()
        config.host = self._cluster.endpoint  # TODO: add this property to cluster!!
        config.verify_ssl = False
        for k, v in kwargs.items():
            setattr(config, k, v)
        return config

    def _client(self, configuration):
        return ApiClient(configuration)

    def _api(self, client):
        return kubernetes.client.CoreV1Api(client)

    def api(self, **kwargs):
        config = self.create_config(**kwargs)
        client = self._client(config)
        api = self._api(client)
        return api

    def verify_functionality(self):
        api = self.api()
        res = api.list_pod_for_all_namespaces(watch=False)
        for i in res.items:
            print("%s\t%s\t%s" % (i.status.pod_ip, i.metadata.namespace, i.metadata.name))
