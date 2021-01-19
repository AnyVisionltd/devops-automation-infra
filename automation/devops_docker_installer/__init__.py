import logging
import os
import pytest
import pathlib
import compose_installer_util

from automation_infra.utils import waiter
from pytest_automation_infra import helpers

from automation_infra.plugins.admin import Admin
from devops_automation_infra.plugins.memsql import Memsql
from devops_automation_infra.plugins.postgresql import Postgresql
from devops_automation_infra.plugins.docker_compose import DockerCompose


TMP_DIR = "/tmp/habertest"


def _wait_infra_services_up(host):
    waiter.wait_nothrow(host.Memsql.ping, timeout=60)
    waiter.wait_nothrow(host.Postgresql.ping, timeout=60)


def already_ran(request):
    return os.path.exists(f"{TMP_DIR}/{request.session.id}/{os.path.basename(__file__)}")


def leave_trace(request):
    # TODO: What I want to do here is leave a trace saying that this plugin ran
    #  and doesnt need to run again on this machine:
    base_dir = f"{TMP_DIR}/{request.session.id}"
    pathlib.Path(base_dir).mkdir(parents=True, exist_ok=True)
    pathlib.Path(f"{base_dir}/{os.path.basename(__file__)}").touch()


@pytest.hookimpl(tryfirst=True)
def pytest_after_proxy_container(base_config, request):
    # import pdb; pdb.set_trace()
    if already_ran(request):
        logging.info("devops installer already ran")
        return
    logging.info("running devops installer..")
    host = next(iter(base_config.hosts.values()))
    compose_yaml_file = request.config.getoption("--yaml-file")
    docker_compose_dir = os.path.realpath(f'{os.path.split(__file__)[0]}/../devops_automation_infra/docker-compose')
    remote_compose_dir = f"{host.SshDirect.home_dir}/compose_v2"
    remote_compose_file_path = f"{remote_compose_dir}/{compose_yaml_file}"
    if request.config.getoption("--skip-docker-setup"):
        logging.debug("skipping docker pull and up")
    else:
        compose_installer_util.put_compose_files(host, docker_compose_dir, remote_compose_dir)
        helpers.do_docker_login(host.SshDirect)
        compose_installer_util.remote_stop_compose(host, remote_compose_file_path)
        try:
            compose_installer_util.remote_pull_compose(host, remote_compose_file_path)
            compose_installer_util.remote_up_compose(host, remote_compose_file_path)
            _wait_infra_services_up(host)
        except Exception as e:
            logging.exception(f"Failed to run compose")
            raise e

    leave_trace(request)
    # import pdb; pdb.set_trace()
    logging.info("devops install finished!")
    # yield  # This is to allow stopping dockers for teardown
    # import pdb; pdb.set_trace()
    # if not request.config.getoption("--skip-docker-down") and not request.config.getoption("--skip-docker-setup"):
    #     logging.debug("stopping docker-compose-core")
    #     remote_stop_compose(host, remote_compose_file_path)
    #     logging.debug("stopped")
