import logging
from infra.model import plugins
from devops_automation_infra.plugins import docker
from automation_infra.plugins import ssh_direct
import subprocess


def _run(cmd):
    return subprocess.check_output(cmd, shell=True).decode().strip()


class DockerRegistry(object):

    def __init__(self, host):
        self._host = host
        self._registry_port = 59497

    @property
    def _local_docker_path(self):
        return subprocess.check_output(['which', 'docker']).strip().decode()

    @property
    def _tunneled_port(self):
        tunnel = self._host.TunnelManager.get_or_create('automation_registry', "127.0.0.1", self._registry_port)
        return tunnel.local_port

    def start(self):
        if self._host.Docker.is_container_up("automation_registry"):
            return
        cmd = f"{self._host.Docker.bin_path} run -d --rm -p {self._registry_port}:5000 --name automation_registry registry:2"
        self._host.SshDirect.run_script(cmd)

    def stop(self):
        self._host.Docker.kill_container_by_service('automation_registry')

    def _tunneled_image_name(self, image_fqdn):
        image_name = image_fqdn.split('/')[-1]
        return f"127.0.0.1:{self._tunneled_port}/{image_name}"

    def _remote_image_name(self, image_fqdn):
        image_name = image_fqdn.split('/')[-1]
        return f"127.0.0.1:{self._registry_port}/{image_name}"

    def _tag_image(self, image_fqdn):
        tunneled_image_fqdn = self._tunneled_image_name(image_fqdn)
        # Have to do it in sudo as containerize has access permissions of root only
        # on docker sock
        cmd = f"sudo {self._local_docker_path} tag {image_fqdn} {tunneled_image_fqdn}"
        _run(cmd)
        return tunneled_image_fqdn

    def _untag_image(self, image_fqdn):
        tunneled_image_fqdn = self._tunneled_image_name(image_fqdn)
        cmd = f"sudo {self._local_docker_path} rmi {tunneled_image_fqdn}"
        _run(cmd)

    def _push(self, image_fqdn):
        cmd = f"sudo {self._local_docker_path} push {image_fqdn}"
        _run(cmd)

    def deploy(self, image_fqdn, remote_name=None):
        logging.info(f"Deploy {image_fqdn} to {self._host.ip}")
        self.start()
        temp_image = self._tag_image(image_fqdn)
        self._push(temp_image)
        self._untag_image(image_fqdn)
        image_name_on_remote = self._remote_image_name(image_fqdn)
        self._host.Docker.pull(image_name_on_remote)
        remote_name = remote_name or image_fqdn
        self._host.Docker.tag(image_name_on_remote, remote_name)
        self._host.Docker.rmi(image_name_on_remote)


plugins.register("DockerRegistry", DockerRegistry)
