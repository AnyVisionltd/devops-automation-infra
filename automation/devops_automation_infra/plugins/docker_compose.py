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
        self._ssh_direct.execute(f'{self.compose_bin_path} -f {compose_file_path} down', timeout=60*20)

    def compose_pull(self, compose_file_path):
        logging.debug(f"pulling docker images from compose {compose_file_path}")
        self._ssh_direct.execute(f'{self.compose_bin_path} -f {compose_file_path} pull -q', timeout=60*60)

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
                logging.error("Compose version is outdated!!!! update docker-compose")
            raise Exception(f"service {container_id} not created by compose")

        # Now depends where compose was started the "compose filename" can be not relative to workdir
        # So now lets start looking and their shared ancestor
        compose_file = compose_config.split("/")[-1]
        return f"{compose_workdir}/{compose_file}"

    def purge_service(self, compose_file_path, service_name):
        cmd = f"{self.compose_bin_path} -f {compose_file_path} rm -s -f {service_name}"
        self._ssh_direct.execute(cmd)

    def run_sevice_with_environment(self, compose_file_path, service_name, environment_variables, doker_name=None):
        env_pairs = " ".join(f"-e {k}={v}" for k, v in environment_variables.items())
        name_cmd = f"--name {doker_name}" if doker_name is not None else ""
        cmd = f"{self.compose_bin_path} -f {compose_file_path} run --no-deps --use-aliases --service-ports -d {name_cmd} {env_pairs} {service_name}"
        self._ssh_direct.execute(cmd)

    def service_image_fqdn(self, compose_file_path, service_name):
        cmd = f"{self.compose_bin_path} -f {compose_file_path} images -- {service_name} | tail -n -1"
        image_descriptor = self._ssh_direct.execute(cmd).strip().split()
        return f"{image_descriptor[1]}:{image_descriptor[2]}"

    def adjust_service_environment(self, compose_file_path, service_name, environment_variables, doker_name=None):
        self.purge_service(compose_file_path, service_name)
        self.run_sevice_with_environment(compose_file_path, service_name, environment_variables, doker_name=doker_name)


plugins.register("DockerCompose", DockerCompose) 