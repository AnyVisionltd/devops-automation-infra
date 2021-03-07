import logging
import os
import re

import pytest

from automation_infra.utils import waiter
from devops_automation_infra.k8s_plugins.proxy_daemonset import ProxyDaemonSet
from devops_automation_infra.plugins.ssh import SSH
from devops_automation_infra.plugins.tunnel_manager import TunnelManager
from automation_infra.utils import concurrently


def pytest_addhooks(pluginmanager):
    from devops_proxy_container import hooks
    pluginmanager.add_hookspecs(hooks)


@pytest.hookimpl(tryfirst=True)
def pytest_after_base_config(base_config, request):
    for cluster in base_config.clusters.values():
        logging.info("deploying proxy_container on remote")
        cluster.ProxyDaemonSet.run()
    logging.info("waiting for SSH connection to proxy_container")
    for host in base_config.hosts.values():
        waiter.wait_nothrow(lambda: host.SSH.connect(port=host.tunnelport), timeout=60)
    logging.info("Successfully connected to proxy pods")
    # Install product devops_docker_installer is invoked
    request.config.hook.pytest_after_proxy_container(base_config=base_config, request=request)


@pytest.hookimpl(tryfirst=True)
def pytest_clean_base_btwn_tests(base_config, item):
    logging.info("running devops clean_base_btwn_tests")
    concurrently.run([lambda: cluster.ProxyDaemonSet.restart() for cluster in base_config.clusters.values()])
    for host in base_config.hosts.values():
        waiter.wait_nothrow(host.SSH.connect, timeout=30)


@pytest.hookimpl(tryfirst=True)
def pytest_clean_between_tests(host, item):
    logging.info("running devops clean_between_tests")
    host.TunnelManager.clear()


def pytest_download_logs(host, dest_dir):
    host.SshDirect.execute('sudo chmod ugo+rw /tmp/automation_infra &&'
                           'docker ps | grep automation-proxy-daemonset | grep -v k8s_POD | awk {\'print $1\'} |'
                           'xargs docker logs &> /storage/logs/automation_proxy.log')
    dest_gz = f"/tmp/logs.tar.gz"
    host.SSH.compress("/storage/logs/", dest_gz)
    host.SSH.download(re.escape(dest_dir), dest_gz)
    # download_consul_logs(host, dest_dir) # TODO: Update to kubernetes consul logs


@pytest.hookimpl(trylast=True)
def pytest_after_test(item, base_config):
    concurrently.run([lambda: cluster.ProxyDaemonSet.kill() for cluster in base_config.clusters.values()])
