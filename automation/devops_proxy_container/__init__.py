import logging
import os
import re

import pytest

from automation_infra.utils import waiter
from devops_automation_infra.plugins.proxy_container import ProxyContainer
from devops_automation_infra.plugins.ssh import SSH
from devops_automation_infra.plugins.tunnel_manager import TunnelManager


def pytest_addhooks(pluginmanager):
    from devops_proxy_container import hooks
    pluginmanager.add_hookspecs(hooks)


@pytest.hookimpl(tryfirst=True)
def pytest_after_base_config(base_config, request):
    for host in base_config.hosts.values():
        logging.info("deploying proxy_container on remote")
        host.ProxyContainer.run()
        logging.info("waiting for SSH connection to proxy_container")
        waiter.wait_nothrow(lambda: host.SSH.connect(port=host.tunnelport), timeout=60)
    # import pdb; pdb.set_trace()
    # Install product devops_docker_installer is invoked
    request.config.hook.pytest_after_proxy_container(base_config=base_config, request=request)


@pytest.hookimpl(tryfirst=True)
def pytest_clean_between_tests(host, item):
    logging.info("running devops clean_between_tests")
    host.TunnelManager.clear()
    host.ProxyContainer.restart()
    waiter.wait_nothrow(host.SSH.connect, timeout=30)


def pytest_download_logs(host, dest_dir):
    host.SshDirect.execute('sudo chmod ugo+rw /tmp/automation_infra && '
                           'docker logs automation_proxy &> /tmp/automation_proxy.log && '
                           'sudo mv /tmp/automation_proxy.log /storage/logs/automation_proxy.log')
    dest_gz = '/tmp/automation_infra/logs.tar.gz'
    host.SSH.compress("/storage/logs/", dest_gz)
    host.SSH.download(re.escape(dest_dir), dest_gz)
    download_consul_logs(host, dest_dir)


def download_consul_logs(host, dest_dir):
    consul_log_dir = os.path.join(dest_dir, "consul")
    os.makedirs(consul_log_dir, exist_ok=True)
    host.Docker.download_container_logs("consul", consul_log_dir, tail=1000)


@pytest.hookimpl(trylast=True)
def pytest_after_test(item, base_config):
    for host in base_config.hosts.values():
        host.ProxyContainer.kill()
