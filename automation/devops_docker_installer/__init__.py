import logging
import os
import pytest
import pathlib

from automation_infra.utils import waiter
from pytest_automation_infra import helpers

from automation_infra.plugins.admin import Admin
from devops_automation_infra.plugins.memsql import Memsql
from devops_automation_infra.plugins.postgresql import Postgresql
from devops_automation_infra.plugins.docker_compose import DockerCompose

TMP_DIR = "/tmp/habertest"

def remove_compose_files(host, remote_compose_dir):
    host.SshDirect.execute(f"sudo rm -rf {remote_compose_dir}")


def put_compose_files(host, core_product_dir, remote_compose_dir):
    logging.debug(f"uploading docker-compose-core to {remote_compose_dir}")
    host.SshDirect.execute(f"mkdir -p {remote_compose_dir}")
    host.SshDirect.upload(f'{core_product_dir}/*', f'{remote_compose_dir}')


def remote_stop_compose(host, remote_compose_file_path):
    host.DockerCompose.compose_down(remote_compose_file_path)


def remote_pull_compose(host, remote_compose_file_path):
    host.DockerCompose.compose_pull(remote_compose_file_path)


def remote_up_compose(host, remote_compose_file_path):
    host.DockerCompose.compose_up(remote_compose_file_path)


def pytest_addoption(parser):
    parser.addoption("--skip-docker-setup", action="store_true", default=False,
                     help="skip down, pull and up to containers, "                                                                           
                          "only do pretest setup")
    parser.addoption("--skip-docker-down", action="store_true", default=True,
                     help="skip down at installer fixture session end")
    parser.addoption("--yaml-file", action="store", default="docker-compose-devops.yml",
                     help="yaml file to pull and up")


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
    return
    host = next(iter(base_config.hosts.values()))
    compose_yaml_file = request.config.getoption("--yaml-file")
    docker_compose_dir = os.path.realpath(f'{os.path.split(__file__)[0]}/devops_automation_infra/docker-compose')
    remote_compose_dir = f"{host.SshDirect.home_dir}/compose_v2"
    remote_compose_file_path = f"{remote_compose_dir}/{compose_yaml_file}"
    if request.config.getoption("--skip-docker-setup"):
        logging.debug("skipping docker pull and up")
    else:
        put_compose_files(host, docker_compose_dir, remote_compose_dir)
        helpers.do_docker_login(host.SshDirect)
        remote_stop_compose(host, remote_compose_file_path)
        try:
            remote_pull_compose(host, remote_compose_file_path)
            remote_up_compose(host, remote_compose_file_path)
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
