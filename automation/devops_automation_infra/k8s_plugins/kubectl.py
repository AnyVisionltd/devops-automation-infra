import kubernetes
from kubernetes.client import ApiClient

from automation_infra.plugins.ssh_direct import SSHCalledProcessError
from devops_automation_infra.plugins.tunnel_manager import TunnelManager
from devops_automation_infra.k8s_plugins.k8s_master import K8SMaster
from infra.model import cluster_plugins
from  automation_infra.utils import waiter


class Kubectl:
    def __init__(self, cluster):
        self._cluster = cluster
        self._api_token = None
        self._k3d_port = '6443'

    @property
    def _master(self):
        return  self._cluster.K8SMaster()

    @property
    def _tunnel(self):
        ssh = self._master.SshDirect
        #svc_ip = ssh.execute('sudo kubectl get svc kubernetes -o jsonpath={.spec.clusterIP}')
        #svc_port = ssh.execute('sudo kubectl get svc kubernetes -o jsonpath={.spec.ports[0].port}')
        svc_ip = "127.0.0.1"
        svc_port = 6443
        tunnel = self._master.TunnelManager.get_or_create('kubectl', svc_ip, svc_port, ssh.get_transport())
        return tunnel

    def _is_k3d(self):
        ssh = self._master.SshDirect
        try:
            ssh.execute("docker ps | grep k3s > /dev/null 2>&1")
            return True
        except SSHCalledProcessError:
            return False

    def _create_config(self, **kwargs):
        ssh = self._master.SshDirect
        self._create_service_account()
        api_token = self._api_token
        config = kubernetes.client.Configuration()
        if self._is_k3d():
            config.host = f"https://{self._master}:{self._k3d_port}"
        else:
            tunnel = self._tunnel
            config.host = f"https://{tunnel.local_endpoint}"
        config.verify_ssl = kwargs.pop("verify_ssl", False)
        config.api_key["authorization"] = api_token
        config.api_key_prefix['authorization'] = 'Bearer'
        for k, v in kwargs.items():
            setattr(config, k, v)
        return config

    def _create_service_account(self):
        if self._api_token:
            return
        ssh = self._master.SshDirect
        import pdb; pdb.set_trace()
        try:
            ssh.execute("sudo kubectl create sa automation-admin")
            ssh.execute("sudo kubectl create clusterrolebinding automation-admin --serviceaccount=default:automation-admin --clusterrole=cluster-admin")
        except SSHCalledProcessError as e:
            pass

        get_sa_token = lambda: ssh.execute('''sudo kubectl get secrets -n default -o jsonpath="{.items[?(@.metadata.annotations['kubernetes\.io/service-account\.name']=='automation-admin')].data.token}"|base64 --decode''').strip()
        waiter.wait_for_predicate(get_sa_token, timeout=90)
        self._api_token = get_sa_token()

    def client(self, **kwargs):
        config = self._create_config(**kwargs)
        return ApiClient(config)

    def verify_functionality(self):
        api = kubernetes.client.CoreV1Api(self.client())
        res = api.list_pod_for_all_namespaces(watch=False)
        for i in res.items:
            print("%s\t%s\t%s" % (i.status.pod_ip, i.metadata.namespace, i.metadata.name))


cluster_plugins.register('Kubectl', Kubectl)

