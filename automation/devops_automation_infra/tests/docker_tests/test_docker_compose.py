import logging

from devops_automation_infra.plugins import docker
from devops_automation_infra.plugins import docker_compose
from pytest_automation_infra.helpers import hardware_config

DUMMY_COMPOSE_FILE = """
version: "3.9"
services:
  sasha-compose-test:
    image: "hello-world:latest"
"""


@hardware_config(hardware={"host": {}})
def test_compose(base_config):
    host = base_config.hosts.host
    temp_file = host.mktemp()
    host.SshDirect.put_contents(DUMMY_COMPOSE_FILE, temp_file)
    compose = base_config.hosts.host.DockerCompose

    logging.info("Remove all containers with this name .. leftovers")
    old_container = host.Docker.container_by_name("sasha-compose-test")
    if old_container:
        host.Docker.remove_containers_by_name(old_container)

    logging.info("Pull and up")
    assert host.Docker.container_by_name("sasha-compose-test") is None
    compose.compose_pull(temp_file)
    compose.compose_up(temp_file)

    logging.info("Verify we have a container")
    test_container = host.Docker.container_by_name("sasha-compose-test")
    assert test_container is not None
    compose_path = compose.path_from_container_id(test_container)
    assert compose_path == temp_file

    compose.compose_down(temp_file)
    assert host.Docker.container_by_name("sasha-compose-test") is None

