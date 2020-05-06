import json
import logging

from automation_infra.utils.waiter import wait_for_predicate
from infra.model import plugins
from automation_infra.plugins.ssh_direct import SshDirect, SSHCalledProcessError
from pytest_automation_infra.helpers import hardware_config


class Docker(object):

    def __init__(self, host):
        self._host = host
        self._ssh_direct = self._host.SshDirect
        self.docker_bin_path = self.docker_bin_path()

    def docker_bin_path(self):
        try:
            return self._ssh_direct.execute("which docker").strip()
        except:
            raise Exception("docker not installed")

    def restart_container_by_service_name(self, service_name):
        try:
            logging.debug(f"restarting container {service_name}")
            self._ssh_direct.execute(f'{self.docker_bin_path} restart $(docker ps --format "{{{{.Names}}}}" | grep {service_name})')
        except SSHCalledProcessError as e:
            if 'No such container' in e.stderr:
                raise Exception("unable to find the service " + service_name +"\nmsg: " + e.stderr)
            else:
                raise Exception(e.stderr)
            

plugins.register("Docker", Docker) 