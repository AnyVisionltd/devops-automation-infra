import logging
from distutils.util import strtobool

from automation_infra.utils.waiter import wait_for_predicate_nothrow
from infra.model import plugins
from automation_infra.plugins.ssh_direct import SshDirect, SSHCalledProcessError
from pytest_automation_infra.helpers import hardware_config

from devops_automation_infra.utils.host import get_host_ip


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
        self.try_executing_and_verbosely_log_error(cmd)

    def kill_container_by_service(self, service_name, signal='KILL'):
        logging.debug(f"Kill container {service_name}")
        cmd = self._running_container_by_name_cmd(
            service_name) + f"| xargs --no-run-if-empty {self._docker_bin} kill --signal={signal}"
        self.try_executing_and_verbosely_log_error(cmd)

    def run_container_by_service(self, servce_name):
        cmd = self._container_by_name_cmd(servce_name) + f"| xargs -I{{}} {self._docker_bin} start {{}}"
        self.try_executing_and_verbosely_log_error(cmd)

    def run_cmd_in_service(self, service_name, cmd):
        cmd_escaped = cmd.replace("'", "\\'")
        cmd = self._running_container_by_name_cmd(service_name) + f"| xargs -I{{}} {self._docker_bin} exec {{}} sh -c $'{cmd_escaped}'"
        return self.try_executing_and_verbosely_log_error(cmd).strip()

    def service_ip_address(self, service_name):
        cmd = self._running_container_by_name_cmd(
            service_name) + f"| xargs -I{{}} {self._container_ip_address_cmd()} {{}}"
        container_ip = self._ssh_direct.execute(cmd).strip()
        # if a service is found but has no ip, it is assumed to be in host-mode.
        # "container does not have its own IP-address when using host mode networking"
        # (from https://docs.docker.com/network/host/)
        return container_ip or get_host_ip(self._host)

    def wait_container_down(self, name_regex, timeout_command=100):
        container_name = self.container_by_name(name_regex)
        cmd = f'{self._docker_bin} wait {container_name}'
        self.try_executing_and_verbosely_log_error(cmd, timeout=timeout_command)

    def copy_file_to_container(self, service_name, file_path, docker_dest_path):
        filename = file_path.split("/")[-1]
        remote_file = f'/tmp/{filename}'
        self._host.SshDirect.upload(file_path, remote_file)

        container_name = self.container_by_name(service_name)

        cmd = f'{self._docker_bin} cp {remote_file} {container_name}:{docker_dest_path}'
        self.try_executing_and_verbosely_log_error(cmd)

    def _first_network_by_name(self, name_regex):
        """
               can cause error if we have 2 containers that pass the regex and have different networks
        """
        return self._ssh_direct.execute(
            f'{self._docker_bin} ps -a --format "{{{{.Networks}}}}" --filter Name=".*{name_regex}.*"').strip().split()[
            0]

    def _first_image_by_name(self, name_regex):
        container_name = self.container_by_name(name_regex)
        cmd = f'{self._docker_bin} inspect --format="{{{{.Config.Image}}}}" {container_name}'
        execute = self.try_executing_and_verbosely_log_error(cmd).strip()
        return execute

    def container_by_name(self, name_regex):
        return self._ssh_direct.execute(self._container_by_name_cmd(name_regex)).strip().split()[0]

    def remove_containers_by_name(self, *container_names):
        cmd = f"{self._docker_bin} rm -f {' '.join(container_names)}"
        self.try_executing_and_verbosely_log_error(cmd, timeout=100)

    def run_container_by_service_with_env(self, service_name, envs={}, remove_container_after_execute=False,
                                          is_detach_mode=True, **kwargs):
        docker_args = ""
        for setting, value in kwargs.items():
            docker_args += f' {setting} {value} '
        for setting, value in envs.items():
            docker_args += f' -e {setting}={value}'
        if remove_container_after_execute:
            docker_args += " --rm "
        network = self._first_network_by_name(service_name)
        image_name = self._first_image_by_name(service_name)
        if is_detach_mode:
            docker_args += ' -d '
        cmd = f"{self._docker_bin} run {docker_args} --network {network} {image_name}"
        self.try_executing_and_verbosely_log_error(cmd, timeout=10000)

    def stop_all_containers(self):
        cmd = f"{self._docker_bin} stop $({self._docker_bin} ps -a -q)"
        self.try_executing_and_verbosely_log_error(cmd, timeout=100)

    def number_of_running_containers(self):
        cmd = f"{self._docker_bin} ps | wc -l"
        result = self.try_executing_and_verbosely_log_error(cmd, timeout=100)
        return 0 if result == 1 else result - 1

    def stop_container(self, name_regex):
        service_name = self.container_by_name(name_regex)
        cmd = f"{self._docker_bin} stop {service_name}"
        self.try_executing_and_verbosely_log_error(cmd, timeout=100)

    def start_container(self, name_regex):
        service_name = self.container_by_name(name_regex)
        cmd = f"{self._docker_bin} start {service_name}"
        self.try_executing_and_verbosely_log_error(cmd, timeout=100)

    def is_container_up(self, name_regex):
        service_name = self.container_by_name(name_regex)
        cmd = f"{self._docker_bin} inspect -f '{{{{.State.Running}}}}' {service_name}"
        return self.try_executing_and_verbosely_log_error(cmd, timeout=100).strip() == 'true'

    def wait_container_up(self, name_regex, timeout=60, interval=1):
        wait_for_predicate_nothrow(lambda: self.is_container_up(name_regex), timeout=timeout, interval=interval)

    def try_executing_and_verbosely_log_error(self, cmd, timeout=None):
        try:
            return self._ssh_direct.execute(cmd, timeout=timeout)
        except:
            logging.exception(f"caught exception trying to execute command: {cmd}")
            logging.info(f"docker ps output: {self._ssh_direct.execute(f'{self._docker_bin} ps')}")
            logging.info(f"sudo netstat -ntlp | grep docker: {self._ssh_direct.execute('sudo netstat -ntlp | grep docker')}")
            logging.info(f"sudo ps -ef | grep docker | grep port: {self._ssh_direct.execute('sudo ps -ef | grep docker | grep port')}")
            raise



plugins.register("Docker", Docker)
