import logging

from devops_automation_infra.plugins import docker_registry
import subprocess
import uuid
from pytest_automation_infra.helpers import hardware_config

@hardware_config(hardware={"host": {}})
def test_docker_registry(base_config):
    logging.info("Pull alpine docker so that we will have it")
    subprocess.run("sudo docker pull docker.io/library/alpine:latest", shell=True)
    remote_name = f"docker.io/library/alpine:{str(uuid.uuid4())}"
    host = base_config.hosts.host
    host.DockerRegistry.deploy("docker.io/library/alpine:latest", remote_name=remote_name)
    remote_images = host.Docker.image_ids(remote_name)
    assert len(remote_images) == 1
