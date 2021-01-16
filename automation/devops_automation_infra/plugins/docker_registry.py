import logging
from infra.model import plugins
import devops_automation_infra.plugins.docker
from devops_automation_infra.utils import docker as docker_utils
from automation_infra.plugins import ssh_direct
import subprocess


def _run(cmd):
    return subprocess.check_output(cmd, shell=True).decode().strip()


class DockerRegistry(object):

    def __init__(self, host):
        self._host = host
        self._registry_port = 59497

    @property
    def tunnel(self):
        return self._host.TunnelManager.get_or_create('automation_registry', "127.0.0.1", self._registry_port)

    def start(self):
        if self._host.Docker.is_container_up("automation_registry"):
            return
        cmd = f"{self._host.Docker.bin_path} run -d --rm -p {self._registry_port}:5000 --name automation_registry registry:2"
        self._host.SshDirect.run_script(cmd)

    def stop(self):
        self._host.Docker.kill_container_by_service('automation_registry')

    @property
    def local_address(self):
        return f"127.0.0.1:{self.tunnel.local_port}"

    @property
    def address_on_remote(self):
        return f"127.0.0.1:{self._registry_port}"

    def _tunneled_image_name(self, image_fqdn):
        image_name = image_fqdn.split('/')[-1]
        return f"{self.local_address}/{image_name}"

    def _remote_image_name(self, image_fqdn):
        image_name = image_fqdn.split('/')[-1]
        return f"{self.address_on_remote}/{image_name}"

    def deploy(self, image_fqdn, remote_name=None):
        logging.info(f"Deploy {image_fqdn} to {self._host.ip}")
        self.start()
        temp_image = self._tunneled_image_name(image_fqdn)
        docker_utils.tag(image_fqdn, temp_image)
        remote_name = remote_name or image_fqdn
        try:
            docker_utils.push(temp_image)
            image_name_on_remote = self._remote_image_name(image_fqdn)
            self._host.Docker.pull(image_name_on_remote)
            self._host.Docker.tag(image_name_on_remote, remote_name)
            self._host.Docker.rmi(image_name_on_remote)
        finally:
            docker_utils.rmi(temp_image)


plugins.register("DockerRegistry", DockerRegistry)
