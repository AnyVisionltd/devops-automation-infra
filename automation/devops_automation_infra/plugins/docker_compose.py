import json
import logging

from automation_infra.utils.waiter import wait_for_predicate
from infra.model import plugins
from automation_infra.plugins.ssh_direct import SshDirect, SSHCalledProcessError
from pytest_automation_infra.helpers import hardware_config


class DockerCompose(object):

    def __init__(self, host):
        self._host = host
        self._ssh_direct = self._host.SshDirect
        self.compose_bin_path = self.docker_compose_bin_path()

    def docker_compose_bin_path(self):
        try:
            return self._ssh_direct.execute("which docker-compose").strip()
        except:
            raise Exception("docker-compose not installed")

    def compose_down(self, compose_file_path):
        logging.debug(f"stopping compose {compose_file_path}")
        self._ssh_direct.execute(f'{self.compose_bin_path} -f {compose_file_path} down', timeout=60*20)

    def compose_pull(self, compose_file_path):
        logging.debug(f"pulling docker images from compose {compose_file_path}")
        self._ssh_direct.execute(f'{self.compose_bin_path} -f {compose_file_path} pull', timeout=60*60)

    def compose_up(self, compose_file_path, *services):
        services_cmd = " ".join(services)
        logging.debug(f"starting compose {compose_file_path} services: ")
        self._ssh_direct.execute(f'{self.compose_bin_path} -f {compose_file_path} up -d {services_cmd}', timeout=60*20)


    def restart_container_by_service_name(self, compose_file_path, container):
        try:
            logging.debug(f"restarting container {container}")
            self._ssh_direct.execute(f"{self.compose_bin_path} -f {compose_file_path} restart {container}")
        except SSHCalledProcessError as e:
            if 'No such service' in e.stderr:
                raise Exception("unable to find the service " + container +"\nmsg: " + e.stderr)
            else:
                raise Exception(e.stderr)


plugins.register("DockerCompose", DockerCompose) 