import json
import logging

from automation_infra.utils.waiter import wait_for_predicate
from infra.model import plugins
from automation_infra.plugins.ssh_direct import SshDirect, SSHCalledProcessError
from pytest_automation_infra.helpers import hardware_config
import packaging.version


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
        self._ssh_direct.execute(f'{self.compose_bin_path} -f {compose_file_path} down', timeout=60 * 20)

    def compose_pull(self, compose_file_path):
        logging.debug(f"pulling docker images from compose {compose_file_path}")
        self._ssh_direct.execute(f'{self.compose_bin_path} -f {compose_file_path} pull -q', timeout=60 * 60)

    def compose_up(self, compose_file_path, *services):
        services_cmd = " ".join(services)
        logging.debug(f"starting compose {compose_file_path} services: ")
        self._ssh_direct.execute(f'{self.compose_bin_path} -f {compose_file_path} up -d {services_cmd}', timeout=60 * 20)

    def restart_container_by_service_name(self, compose_file_path, container):
        try:
            logging.debug(f"restarting container {container}")
            self._ssh_direct.execute(f"{self.compose_bin_path} -f {compose_file_path} restart {container}")
        except SSHCalledProcessError as e:
            if 'No such service' in e.stderr:
                raise Exception("unable to find the service " + container + "\nmsg: " + e.stderr)
            else:
                raise Exception(e.stderr)

    @property
    def version(self):
        cmd = f"{self.compose_bin_path} version --short"
        version = self._ssh_direct.execute(cmd).strip()
        return packaging.version.parse(version)

    def path_from_container_id(self, container_id):
        labels = self._host.Docker.labels(container_id)
        compose_workdir = labels.get("com.docker.compose.project.working_dir", None)
        compose_config = labels.get("com.docker.compose.project.config_files")
        if compose_workdir is None:
            # This feature is only enabled since 1.25.2 (Jan 2020)
            if self.version < packaging.version.Version("1.25.2"):
                raise Exception("Compose version is outdated!!!! update docker-compose")
            raise Exception(f"service {container_id} not created by compose")

        # Now depends where compose was started the "compose filename" can be not relative to workdir
        # So now lets start looking and their shared ancestor
        compose_file = compose_config.split("/")[-1]
        return f"{compose_workdir}/{compose_file}"

    def purge_service(self, compose_file_path, service_name):
        cmd = f"{self.compose_bin_path} -f {compose_file_path} rm -s -f {service_name}"
        self._ssh_direct.execute(cmd)

    def service_docker_id(self, compose_file_path, service_name):
        cmd = f"{self.compose_bin_path} -f {compose_file_path} ps -a -q {service_name}"
        return self._ssh_direct.execute(cmd).strip()

    def run_sevice_with_environment(self, compose_file_path, service_name, environment_variables, doker_name=None, restart_policy="no", ports_override=None, command=None):
        env_pairs = " ".join(f"-e {k}={v}" for k, v in environment_variables.items())
        name_cmd = f"--name {doker_name}" if doker_name is not None else ""
        ports_command = " ".join([f" -p {port[0]}:{port[1]}"  for port in ports_override]) if ports_override is not None else "--service-ports"
        command = command or ""
        cmd = f"{self.compose_bin_path} -f {compose_file_path} run --no-deps --use-aliases {ports_command} -d {name_cmd} {env_pairs} {service_name} {command}"
        container_name = self._ssh_direct.execute(cmd).strip()
        self._host.Docker.change_restart_policy(container_name, policy=restart_policy)

    def service_image_fqdn(self, compose_file_path, service_name):
        cmd = f"{self.compose_bin_path} -f {compose_file_path} images -- {service_name} | tail -n -1"
        image_descriptor = self._ssh_direct.execute(cmd).strip().split()
        return f"{image_descriptor[1]}:{image_descriptor[2]}"

    def adjust_service_environment(self, compose_file_path, service_name, environment_variables, doker_name=None, restart_policy=None, ports_override=None, command=None):
        # If restart policy is not defined lets try to figure it out
        if restart_policy is None:
            docker_id = self.service_docker_id(compose_file_path, service_name)
            restart_policy = self._host.Docker.inspect(docker_id)['HostConfig']['RestartPolicy']['Name']
        self.purge_service(compose_file_path, service_name)
        self.run_sevice_with_environment(compose_file_path, service_name, environment_variables, doker_name=doker_name, restart_policy=restart_policy,
                                         ports_override=ports_override, command=command)

    def create_service(self, compose_file_path, service_name):
        cmd = f"{self.compose_bin_path} -f {compose_file_path} up --no-start --no-deps --force-recreate --remove-orphans {service_name}"
        self._ssh_direct.execute(cmd)

    def recreate_service(self, compose_file_path, service_name):
        self.purge_service(compose_file_path, service_name)
        self.create_service(compose_file_path, service_name)

    def refresh_compose(self, compose_file_path):
        cmd = f"{self.compose_bin_path} -f {compose_file_path} up --no-start --no-deps"
        self._ssh_direct.execute(cmd)

    def run_foreground(self, compose_file_path, *services):
        services_to_refresh = " ".join([service for service in services])
        cmd = f"{self.compose_bin_path} -f {compose_file_path} up --no-deps --no-recreate --no-color {services_to_refresh}"
        self._ssh_direct.execute(cmd)

    def restart_services(self, compose_file_path, *services):
        services_to_refresh = " ".join([service for service in services])
        cmd = f"{self.compose_bin_path} -f {compose_file_path} restart {services_to_refresh}"
        self._ssh_direct.execute(cmd)

    def services(self, compose_file_path):
        cmd = f"docker-compose -f {compose_file_path} config  --services"
        return self._ssh_direct.execute(cmd).strip().split('\n')

    def service_images(self, compose_file_path):
        cmd = f"docker-compose -f {compose_file_path} ps -q -a"
        return self._ssh_direct.execute(cmd).strip().split('\n')


plugins.register("DockerCompose", DockerCompose)
