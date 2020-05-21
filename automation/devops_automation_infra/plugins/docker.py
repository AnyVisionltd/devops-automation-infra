import logging

from infra.model import plugins
from automation_infra.plugins.ssh_direct import SshDirect, SSHCalledProcessError
from pytest_automation_infra.helpers import hardware_config


class Docker(object):

    def __init__(self, host):
        self._host = host
        self._ssh_direct = self._host.SshDirect
        self._docker_bin =  self._docker_bin_path()

    def _docker_bin_path(self):
        try:
            return self._ssh_direct.execute("which docker").strip()
        except:
            raise Exception("docker not installed")

    def _running_container_by_name_cmd(self, name_regex):
        return f'{self._docker_bin} ps --format "{{{{.Names}}}}" --filter Name=".*{name_regex}.*"'

    def _container_by_name_cmd(self, name_regex):
        return f'{self._docker_bin} ps -a --format "{{{{.Names}}}}" --filter Name=".*{name_regex}.*"'

    def _container_ip_address_cmd(self):
        return f'{self._docker_bin} inspect -f "{{{{range .NetworkSettings.Networks}}}}{{{{.IPAddress}}}}{{{{end}}}}"'

    def restart_container_by_service_name(self, service_name):
        logging.debug(f"restarting container {service_name}")
        cmd = self._container_by_name_cmd(service_name) + f"| xargs --no-run-if-empty {self._docker_bin} restart"
        self._ssh_direct.execute(cmd)

    def kill_container_by_service(self, service_name, signal='KILL'):
        logging.debug(f"Kill container {service_name}")
        cmd = self._running_container_by_name_cmd(service_name) + f"| xargs --no-run-if-empty {self._docker_bin} kill --signal={signal}"
        self._ssh_direct.execute(cmd)

    def run_container_by_service(self, servce_name):
        cmd = self._container_by_name_cmd(servce_name) + f"| xargs -I{{}} {self._docker_bin} start {{}}"
        self._ssh_direct.execute(cmd)

    def run_cmd_in_service(self, service_name, cmd):
        cmd = self._running_container_by_name_cmd(service_name) + f"| xargs -I{{}} {self._docker_bin} exec {{}} {cmd}"
        return self._ssh_direct.execute(cmd).strip()

    def service_ip_address(self, service_name):
        cmd = self._running_container_by_name_cmd(service_name) + f"| xargs -I{{}} {self._container_ip_address_cmd()} {{}}"
        return  self._ssh_direct.execute(cmd).strip()


plugins.register("Docker", Docker)
