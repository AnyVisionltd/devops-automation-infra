import time

import yaml

import cluster_plugins_library


class Gravity:
    def __init__(self, cluster):
        self._cluster = cluster
        self._master = self._cluster.master

    def generate_kubectl_config(self):
        self._open_communication()
        self._get_secret()
        self._tsh_login()

    def _open_communication(self):
        ssh = self._master.SshDirect
        yaml_filename = f"auth_gateway_{time.time()}.yaml"
        ssh.execute(f"sudo gravity exec gravity resource get authgateway --format=yaml > /tmp/{yaml_filename}")
        auth_gateway = yaml.load(ssh.execute(f"cat /tmp/{yaml_filename}"))
        auth_gateway['spec']['public_addr'] = [self._master.ip]
        ssh.execute(f"sudo gravity exec gravity resource create -f /host/tmp/{yaml_filename}")

    def _get_secret(self):
        ssh = self._master.SshDirect
        password = ssh.execute(
            "sudo kubectl -n kube-system get secret gravity-secret -o=jsonpath='{.data.password}' | base64 --decode").strip()
        return password

    def _tsh_login(self):
        pass
        # subprocess.run(f"sshpass -p {password} tsh login --proxy {host.ip}:32009 --user admin --insecure")
        # self._master.SshDirect.execute("gravity exec kubectl tsh login {username} {password from get_secret}")


cluster_plugins_library.register('Gravity', Gravity)
