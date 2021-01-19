import logging
import yaml
import re
import os, io
from devops_automation_infra.plugins.docker import Docker
from devops_automation_infra.plugins.docker_compose import DockerCompose
from pytest_automation_infra import helpers


class ComposeEditor(object):
    def __init__(self, compose):
        self.compose = compose

    @classmethod
    def from_file(cls, file_path):
        with open(file_path, "r") as file:
            yaml_content = yaml.safe_load(file)
            return cls(yaml_content)

    def update_service(self, service_name, key, value):
        self.compose['services'][service_name][key] = value

    def service_key(self, service_name, key):
        return self.compose['services'][service_name][key]

    def service_image(self, service_name):
        image_path = self.service_key(service_name, 'image').split(':')
        image_dict = {
            "name": image_path[0],
            "version": image_path[1]
        }
        return image_dict


def remove_compose_files(host, remote_compose_dir):
    host.SshDirect.execute(f"sudo rm -rf {remote_compose_dir}")


def put_compose_files(host, core_product_dir, remote_compose_dir):
    logging.debug(f"uploading docker-compose-core to {remote_compose_dir}")
    host.SshDirect.execute(f"mkdir -p {remote_compose_dir}")
    host.SshDirect.upload(f'{core_product_dir}/docker-compose/*', f'{remote_compose_dir}')


def remote_stop_compose(host, remote_compose_file_path):
    host.DockerCompose.compose_down(remote_compose_file_path)


def remote_pull_compose(host, remote_compose_file_path):
    host.DockerCompose.compose_pull(remote_compose_file_path)


def remote_up_compose(host, remote_compose_file_path):
    host.DockerCompose.compose_up(remote_compose_file_path)


def _put_compose_dir_on_host_under_test(compose, core_product_dir, host, remote_compose_dir, remote_compose_file_path):
    put_compose_files(host, core_product_dir, remote_compose_dir)
    put_compose_host_under_test(compose, host, remote_compose_file_path)


def _compose_pull_and_up(compose, host, remote_compose_file_path):
    try:
        logging.info(f"Pull compose {remote_compose_file_path}")
        remote_pull_compose(host, remote_compose_file_path)
        logging.info(f"Up compose {remote_compose_file_path}")
        remote_up_compose(host, remote_compose_file_path)
    except Exception as e:
        logging.exception(f"Failed to run compose {compose.dumps()}")
        raise e


def put_compose_host_under_test(compose, host, remote_compose_file_path):
    with io.StringIO() as stream:
        compose.dumps(stream)
        host.SshDirect.put_contents(stream.getvalue(), remote_compose_file_path)


def _tag_services(compose_yaml_file, core_product_dir, request):
    service_lst = request.config.getoption("--services").split(',')
    tag = request.config.getoption("--services-tag").replace("/", "_")
    core_compose_file_path = f'{core_product_dir}/docker-compose/{compose_yaml_file}'
    logging.info("change relevant data on compose")
    compose = ComposeEditor.from_file(core_compose_file_path)
    if service_lst and tag:
        logging.info("templating compose yaml..")
        for service in service_lst:
            image = compose.service_image(service)
            new_image_name = image["name"] + ":" + tag
            compose.update_service(service, 'image', new_image_name)
    return compose


def _sanitize_nodeid(filename):
    filename = filename.replace('::()::', '/')
    filename = filename.replace('::', '/')
    filename = re.sub(r'\[(.+)\]', r'-\1', filename)
    return filename


def pytest_runtest_teardown(item):
    base_config = item.funcargs.get('base_config')
    if not base_config:
        logging.error("base_config fixture wasnt initted properly, cant download logs")
        return
    host = next(iter(base_config.hosts.values()))
    # We use this to get consul logs from docker
    logs_dir = os.path.join(item.config.option.logger_logsdir, _sanitize_nodeid(item.nodeid))
    consul_log_dir = os.path.join(logs_dir, "consul")
    os.makedirs(consul_log_dir, exist_ok=True)
    host.Docker.download_container_logs("consul", consul_log_dir, tail=1000)
