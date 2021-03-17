from datetime import datetime
import logging
import os
import gossip

from automation_infra.utils import waiter
from compose_util.compose_manager import ComposeManager
from compose_util.compose_options import add_cmdline_options
from devops_automation_infra.installers import ssh

from pytest_automation_infra import helpers

from devops_automation_infra.plugins.proxy_container import ProxyContainer
from automation_infra.plugins.ssh_direct import SshDirect
from devops_automation_infra.plugins.ssh import SSH
from devops_automation_infra.plugins.tunnel_manager import TunnelManager
from devops_automation_infra.plugins.docker_compose import DockerCompose
from automation_infra.plugins.ip_table import Iptables


from devops_automation_infra.plugins.consul import Consul
from devops_automation_infra.plugins.memsql import Memsql
from devops_automation_infra.plugins.postgresql import Postgresql


@gossip.register("runtest_setup")
def setup():
    pass


@gossip.register('session', tags=['docker', 'devops_docker'])
def deploy_proxy_container(host, request):
    ssh.ssh_direct_connect_session(host, request)
    host.ProxyContainer.run()
    waiter.wait_nothrow(host.SSH.connect, timeout=30)


@gossip.register('session_install', tags=['devops_docker'], provides=['devops_docker'])
def install_devops_product(host, request):
    logging.info("running devops installer..")
    if request.config.getoption("--sync-time"):
        helpers.sync_time(host)
    if not request.config.getoption("--skip-docker-setup"):
        compose_yaml_file = request.config.getoption("--yaml-file")
        docker_compose_dir = os.path.realpath(f'{os.path.split(__file__)[0]}/../docker-compose')
        remote_compose_dir = f"{host.SshDirect.home_dir}/compose_v2"
        local_yaml_path = os.path.join(docker_compose_dir, compose_yaml_file)
        host.DockerCompose.put_yaml(local_yaml_path, remote_compose_dir)
        remote_compose_yaml_path = os.path.join(remote_compose_dir, os.path.basename(local_yaml_path))
        ComposeManager.pull_and_up(host, remote_compose_yaml_path)
        waiter.wait_for_predicates(host.Postgresql.ping, host.Memsql.ping, host.Consul.ping, timeout=120)

    logging.info("devops install finished!")


@gossip.register('setup', tags=['docker', 'devops_docker'], provides=['devops'])
def clean(host, request):
    logging.info("running devops clean_between_tests")
    host.Iptables.reset_state()
    host.ProxyContainer.run()
    waiter.wait_nothrow(host.SSH.connect, timeout=30)
    host.Admin.flush_journal()
    host.Admin.log_to_journal(f">>>>> Test {request.node.nodeid} <<<<")


@gossip.register('teardown', tags=['docker', 'devops_docker'], provides=['devops'])
def download(host, request):
    logs_dir = request.config.getoption("--logs-dir", f'logs/{datetime.now().strftime("%Y_%m_%d__%H%M_%S")}')
    download_host_logs(host, logs_dir)


def download_host_logs(host, logs_dir):
    dest_dir = os.path.join(logs_dir, host.alias)
    os.makedirs(dest_dir, exist_ok=True)
    host.SshDirect.execute('sudo sh -c "journalctl > /tmp/journal.log"')
    host.SshDirect.download(dest_dir, '/tmp/journal.log')
