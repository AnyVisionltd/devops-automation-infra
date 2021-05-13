from infra.model import cluster_plugins
from devops_automation_infra.utils import s3
import boto3


class Seaweed:
    def __init__(self, cluster):
        self._cluster = cluster
        self.DNS = 'seaweedfs-s3.default.svc.cluster.local'
        self.PORT = 8333
        self.filer_host = 'seaweedfs-filer.default.svc.cluster.local'
        self.filer_port = 8888

    @property
    def _master(self):
        return self._cluster.K8SMaster()

    @property
    def _tunnel(self):
        return self._master.TunnelManager.get_or_create("Seaweed-s3", self.DNS, self.PORT)

    def create_client(self):
        host, port = self._tunnel.host_port
        return boto3.client('s3', endpoint_url=f"http://{host}:{port}",
                          aws_secret_access_key='any',
                          aws_access_key_id='any')

cluster_plugins.register('Seaweed', Seaweed)
