import logging
from distutils.util import strtobool

from automation_infra.utils.waiter import wait_for_predicate_nothrow
from infra.model import plugins
from automation_infra.plugins.ssh_direct import SshDirect, SSHCalledProcessError
from pytest_automation_infra.helpers import hardware_config
from automation_infra.utils import waiter

from devops_automation_infra.utils.host import get_host_ip
import json
import os
import ast

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

    def _container_id_by_name_cmd(self, name_regex):
        return f'{self._docker_bin} ps -a --format "{{{{.ID}}}}" --filter Name=".*{name_regex}.*"'

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

    def run_cmd_in_service_background(self, service_name, cmd):
        cmd_escaped = cmd.replace("'", "\\'")
        cmd = self._running_container_by_name_cmd(service_name) + f"| xargs -I{{}} {self._docker_bin} exec --detach {{}} sh -c $'{cmd_escaped}'"
        return self._ssh_direct.execute(cmd)

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

    def get_container_status(self, name_regex):
        container_name = self.container_by_name(name_regex)
        cmd = f"{self._docker_bin} inspect --format='{{{{.State.Status}}}}' {container_name}"
        return self.try_executing_and_verbosely_log_error(cmd).strip()

    def wait_for_container_status(self, name_regex, status, timeout=100):
        waiter.wait_for_predicate(lambda: self.get_container_status(name_regex) == status, timeout=timeout)

    def copy_file_to_container(self, service_name, file_path, docker_dest_path):
        filename = file_path.split("/")[-1]
        remote_file = f'/tmp/{filename}'
        self._host.SshDirect.upload(file_path, remote_file)

        container_name = self.container_by_name(service_name)

        cmd = f'{self._docker_bin} cp {remote_file} {container_name}:{docker_dest_path}'
        self.try_executing_and_verbosely_log_error(cmd)

    def copy_from_host_to_container(self, service_name, remote_dir, container_dir):
        container_name = self.container_by_name(service_name)
        cmd = f'{self._docker_bin} cp -a {remote_dir} {container_name}:{container_dir}'
        self._ssh_direct.execute(cmd)

    def _first_network_by_name(self, name_regex):
        """
               can cause error if we have 2 containers that pass the regex and have different networks
        """
        return self._ssh_direct.execute(
            f'{self._docker_bin} ps -a --format "{{{{.Networks}}}}" --filter Name=".*{name_regex}.*"').strip().split()[
            0]

    def _aliases_by_container_name(self, container_name):
        json_res = self._ssh_direct.execute(f'{self._docker_bin} inspect --format "{{{{json .NetworkSettings.Networks}}}}" {container_name}')
        res = json.loads(json_res)
        return next(iter(res.values()))["Aliases"]

    def _first_image_by_name(self, name_regex):
        container_name = self.container_by_name(name_regex)
        cmd = f'{self._docker_bin} inspect --format="{{{{.Config.Image}}}}" {container_name}'
        execute = self.try_executing_and_verbosely_log_error(cmd).strip()
        return execute

    def container_by_name(self, name_regex):
        return self._ssh_direct.execute(self._container_by_name_cmd(name_regex)).strip().split()[0]

    def container_ids_by_name(self, name_regex):
        return self._ssh_direct.execute(self._container_id_by_name_cmd(name_regex)).strip().split('\n')

    def remove_containers_by_name(self, *container_names):
        cmd = f"{self._docker_bin} rm -f {' '.join(container_names)}"
        self.try_executing_and_verbosely_log_error(cmd, timeout=100)

    def run_container_by_service_with_env(self, service_name, envs={}, remove_container_after_execute=False,
                                          is_detach_mode=True, **kwargs):
        docker_args = ""
        for setting, value in kwargs.items():
            docker_args += f' --{setting} {value} '
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

    def container_envs(self, service_name):
        container_name = self.container_by_name(service_name)
        cmd = f"{self._docker_bin} inspect -f '{{{{json .Config.Env }}}}' {container_name}"
        return {env.split("=")[0]:env.split("=")[1] for env in ast.literal_eval(self.try_executing_and_verbosely_log_error(cmd, timeout=10000))}

    def overwrite_and_run_container_by_service_with_env(self, service_name, envs={}, is_detach_mode=True, **kwargs):
        network = self._first_network_by_name(service_name)
        image_name = self._first_image_by_name(service_name)
        container_name = self.container_by_name(service_name)
        network_aliases = self._aliases_by_container_name(container_name)
        dns_aliases = [alias for alias in network_aliases if alias.endswith(".tls.ai")]

        self.remove_containers_by_name(container_name)

        docker_args = f" --name {container_name}"

        if dns_aliases:
            docker_args += f" --network-alias {dns_aliases[0]}"

        for setting, value in kwargs.items():
            docker_args += f' --{setting} {value} '
        for setting, value in envs.items():
            docker_args += f' -e {setting}={value}'
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
            logging.debug(f"caught exception trying to execute command: {cmd}", exc_info=True)
            logging.debug(f"docker ps output: {self._ssh_direct.execute(f'{self._docker_bin} ps')}")
            logging.debug(f"sudo netstat -ntlp | grep docker: {self._ssh_direct.execute('sudo netstat -ntlp | grep docker')}")
            logging.debug(f"sudo ps -ef | grep docker | grep port: {self._ssh_direct.execute('sudo ps -ef | grep docker | grep port')}")
            raise

    def inspect(self, container_id):
        cmd = f'{self._docker_bin} inspect {container_id}'
        return json.loads(self._ssh_direct.execute(cmd).strip())[0]

    def get_container_logs(self, name_regex, tail=30):
        container_name = self.container_by_name(name_regex)
        cmd = f"{self._docker_bin} logs {container_name} --tail {tail}"
        return self._ssh_direct.execute(cmd)

    def download_container_logs(self, name_regex, local_dest, tail=30):
        content = self.get_container_logs(name_regex, tail)
        log_path = os.path.join(local_dest, name_regex)
        with open(log_path, 'w') as f:
            f.write(content)

    def clear_container_logs(self, name_regex):
        container_name = self.container_by_name(name_regex)
        logpath = self.inspect(container_name)['LogPath']
        return self._ssh_direct.execute(f'truncate -s 0 {logpath}')

plugins.register("Docker", Docker)
