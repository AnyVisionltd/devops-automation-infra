import re

import pytest

from automation_infra.utils import waiter
from devops_automation_infra.plugins.proxy_container import ProxyContainer
from devops_automation_infra.plugins.ssh import SSH
from devops_automation_infra.plugins.tunnel_manager import TunnelManager


@pytest.hookimpl(tryfirst=True)
def pytest_after_base_config(base_config):
    for host in base_config.hosts.values():
        host.ProxyContainer.run()
        waiter.wait_nothrow(lambda: host.SSH.connect(port=host.tunnelport), timeout=60)


def pytest_clean_between_tests(host, item):
    host.TunnelManager.clear()
    host.ProxyContainer.restart()
    waiter.wait_nothrow(host.SSH.connect, timeout=30)


def pytest_download_logs(host, dest_dir):
    host.SshDirect.execute('sudo chmod ugo+rw /tmp/automation_infra && '
                           'docker logs automation_proxy &> /tmp/automation_proxy.log && '
                           'sudo mv /tmp/automation_proxy.log /storage/logs/automation_proxy.log')
    # logging.debug(f"ls on /storage/logs: {host.SshDirect.execute('ls /storage/logs -lh')}")
    dest_gz = '/tmp/automation_infra/logs.tar.gz'
    host.SSH.compress("/storage/logs/", dest_gz)
    host.SSH.download(re.escape(dest_dir), dest_gz)


@pytest.hookimpl(trylast=True)
def pytest_after_test(item, base_config):
    for host in base_config.hosts.values():
        host.ProxyContainer.kill()
