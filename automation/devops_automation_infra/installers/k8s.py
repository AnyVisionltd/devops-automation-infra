from datetime import datetime
import logging
import os
import gossip
import re
from automation_infra.utils import waiter
from compose_util.compose_manager import ComposeManager
from compose_util.compose_options import add_cmdline_options


from automation_infra.plugins.ssh_direct import SshDirect
from devops_automation_infra.plugins.ssh import SSH
from devops_automation_infra.k8s_plugins.proxy_daemonset import ProxyDaemonSet
from automation_infra.utils import concurrently
from devops_automation_infra.installers import ssh


@gossip.register('session', tags=['k8s', 'devops_k8s'])
def deploy_proxy_pod(cluster, request):
    concurrently.run([lambda: ssh.ssh_direct_connect_session(host, request) for host in cluster.hosts.values()])
    logging.info("Deploying proxy daemon-set")
    cluster.ProxyDaemonSet.run()
    for host in cluster.hosts.values():
        waiter.wait_nothrow(lambda: host.SSH.connect(port=host.tunnelport), timeout=60)


@gossip.register('session_install', tags=['devops_k8s'])
def install_devops_product(cluster, request):
    # TODO: Add installation of devops product
    pass


@gossip.register('setup', tags=['docker', 'devops_k8s'])
def clean(cluster, request):
    concurrently.run([lambda: ssh.ssh_direct_connect_session(host, request) for host in cluster.hosts.values()])
    logging.info("running devops clean_base_btwn_tests")
    cluster.ProxyDaemonSet.restart()
    for host in cluster.hosts.values():
        waiter.wait_nothrow(host.SSH.connect, timeout=30)


@gossip.register('teardown', tags=['k8s', 'devops_k8s'])
def download(cluster, request):
    logs_dir = request.config.getoption("--logs-dir", f'logs/{datetime.now().strftime("%Y_%m_%d__%H%M_%S")}')
    concurrently.run([lambda: download_host_logs(host, os.path.join(logs_dir, host.alias))
                      for host in cluster.hosts.values()])
    # concurrently.run([lambda: download_consul_logs(host, os.path.join(logs_dir, host.alias))
    #                   for host in cluster.hosts.values() if host.Docker.container_by_name("consul")])


def download_host_logs(host, dest_dir):
    os.makedirs(dest_dir, exist_ok=True)
    host.SshDirect.execute('sudo sh -c "journalctl > /tmp/journal.log"')
    host.SshDirect.download(dest_dir, '/tmp/journal.log')
    host.SshDirect.execute('sudo chmod ugo+rw /storage/logs &&'
                           'sudo docker ps | grep automation-proxy-daemonset | grep -v k8s_POD | awk {\'print $1\'} |'
                           'xargs sudo docker logs &> /storage/logs/automation_proxy.log')
    dest_gz = '/tmp/logs.tar.gz'
    host.SSH.compress("/storage/logs/", dest_gz)
    host.SSH.download(re.escape(dest_dir), dest_gz)


def download_consul_logs(host, dest_dir):
    consul_log_dir = os.path.join(dest_dir, "consul")
    os.makedirs(consul_log_dir, exist_ok=True)
    host.Docker.download_container_logs("consul", consul_log_dir, tail=1000)