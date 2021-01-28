import logging
import os
import pytest

from compose_util import compose_options
from compose_util.compose_manager import ComposeManager
from automation_infra.utils import waiter
from pytest_automation_infra import helpers


from automation_infra.plugins.admin import Admin
from devops_automation_infra.plugins.memsql import Memsql
from devops_automation_infra.plugins.consul import Consul
from devops_automation_infra.plugins.postgresql import Postgresql
from devops_automation_infra.plugins.docker import Docker
from devops_automation_infra.plugins.docker_compose import DockerCompose


def pytest_addoption(parser):
    compose_options.add_cmdline_options(parser)


@pytest.hookimpl(tryfirst=True)
def pytest_after_proxy_container(base_config, request):
    logging.info("running devops installer..")
    host = next(iter(base_config.hosts.values()))
    if request.config.getoption("--sync-time"):
        helpers.sync_time(base_config.hosts)
    if not request.config.getoption("--skip-docker-setup"):
        compose_yaml_file = request.config.getoption("--yaml-file")
        docker_compose_dir = os.path.realpath(f'{os.path.split(__file__)[0]}/../devops_automation_infra/docker-compose')
        remote_compose_dir = f"{host.SshDirect.home_dir}/compose_v2"
        local_yaml_path = os.path.join(docker_compose_dir, compose_yaml_file)
        host.DockerCompose.put_yaml(local_yaml_path, remote_compose_dir)
        remote_compose_yaml_path = os.path.join(remote_compose_dir, os.path.basename(local_yaml_path))
        ComposeManager.pull_and_up(host, remote_compose_yaml_path)
        waiter.wait_for_predicates(host.Postgresql.ping, host.Memsql.ping, host.Consul.ping)

    logging.info("devops install finished!")
