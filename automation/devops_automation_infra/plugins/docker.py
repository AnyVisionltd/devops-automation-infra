import logging

from infra.model import plugins
from automation_infra.plugins.ssh_direct import SshDirect, SSHCalledProcessError
from pytest_automation_infra.helpers import hardware_config


class Docker(object):

    def __init__(self, host):
        self._host = host
        self._ssh_direct = self._host.SshDirect
        self._docker_bin = self._docker_bin_path()

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
        cmd = self._running_container_by_name_cmd(
            service_name) + f"| xargs --no-run-if-empty {self._docker_bin} kill --signal={signal}"
        self._ssh_direct.execute(cmd)

    def run_container_by_service(self, servce_name):
        cmd = self._container_by_name_cmd(servce_name) + f"| xargs -I{{}} {self._docker_bin} start {{}}"
        self._ssh_direct.execute(cmd)

    def run_cmd_in_service(self, service_name, cmd):
        cmd = self._running_container_by_name_cmd(service_name) + f"| xargs -I{{}} {self._docker_bin} exec {{}} {cmd}"
        return self._ssh_direct.execute(cmd).strip()

    def service_ip_address(self, service_name):
        cmd = self._running_container_by_name_cmd(
            service_name) + f"| xargs -I{{}} {self._container_ip_address_cmd()} {{}}"
        return self._ssh_direct.execute(cmd).strip()

    def wait_container_down(self, name_regex, timeout_command=100):
        container_name = self.container_by_name(name_regex)
        cmd = f'{self._docker_bin} wait {container_name}'
        self._ssh_direct.execute(cmd, timeout=timeout_command)

    def _first_network_by_name(self, name_regex):
        """
               can cause error if we have 2 containers that pass the regex and have different networks
        """
        return self._ssh_direct.execute(
            f'{self._docker_bin} ps -a --format "{{{{.Networks}}}}" --filter Name=".*{name_regex}.*"').strip().split()[0]

    def _first_image_by_name(self, name_regex):
        container_name = self.container_by_name(name_regex)
        cmd = f'{self._docker_bin} inspect --format="{{{{.Config.Image}}}}" {container_name}'
        execute = self._ssh_direct.execute(cmd).strip()
        return execute

    def container_by_name(self, name_regex):
        return self._ssh_direct.execute(self._container_by_name_cmd(name_regex)).strip().split()[0]

    def remove_containers_by_name(self, *container_names):
        cmd = f"{self._docker_bin} rm -f {' '.join(container_names)}"
        self._ssh_direct.execute(cmd, timeout=100)

    def run_container_by_service_with_env(self, service_name, envs={},remove_container_after_execute=False, is_detach_mode=True, **kwargs):
        docker_args = ""
        for setting, value in kwargs.items():
            docker_args += f' {setting} {value} '
        for setting, value in envs.items():
            docker_args += f' -e {setting}={value}'
        if remove_container_after_execute:
            docker_args += " --rm "
        network = self._first_network_by_name(service_name)
        image_name=self._first_image_by_name(service_name)
        if is_detach_mode:
            docker_args += ' -d '
        cmd = f"{self._docker_bin} run {docker_args} --network {network} {image_name}"
        self._ssh_direct.execute(cmd, timeout=10000)

    def clear_logs(self):
        self._ssh_direct.execute("sudo truncate -s 0 /var/lib/docker/containers/*/*-json.log")


plugins.register("Docker", Docker)