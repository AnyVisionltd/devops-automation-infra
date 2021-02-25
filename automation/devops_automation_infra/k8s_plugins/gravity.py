import subprocess
import time

import yaml

from infra.model import cluster_plugins


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
        dumped_auth_gateway = yaml.dump(auth_gateway)
        ssh.execute(f"echo \"{dumped_auth_gateway}\" >  /tmp/{yaml_filename}")
        ssh.execute(f"sudo gravity exec gravity resource create -f /host/tmp/{yaml_filename}")

    def _get_secret(self):
        ssh = self._master.SshDirect
        password = ssh.execute(
            "sudo kubectl -n kube-system get secret gravity-secret -o=jsonpath='{.data.password}' | base64 --decode").strip()
        return password

    def _tsh_login(self, password):
        output = subprocess.run(f"tsh login --proxy {self._master.ip}:32009 --user admin --insecure", shell=True)
        with open("/dev/pts/1", "wb+", buffering=0) as term:
            term.write(password.encode())
        # self._master.SshDirect.execute("gravity exec kubectl tsh login {username} {password from get_secret}")

    def exec(self, command):
        return self._master.SshDirect.execute(f"sudo gravity exec {command}")


cluster_plugins.register('Gravity', Gravity)
