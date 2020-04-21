import concurrent
import logging
import pytest

from automation_infra.utils import initializer as infra_initializer
from devops_automation_infra.utils import initializer as devops_initializer
from pytest_automation_infra import determine_scope


@pytest.fixture(scope=determine_scope)
def clean_up_all_deployments_and_svcs(base_config):
    k8s = base_config.hosts.host1.K8s
    k8s.delete_deployment(name="", all=True)
    k8s.delete_svc(svc_name="", all=True)
    yield
    k8s.delete_deployment(name="", all=True)
    k8s.delete_svc(svc_name="", all=True)


def setup(host):
    infra_initializer.init_plugins(host)
    devops_initializer.init_plugins(host)
    host.clean_between_tests()


@pytest.hookimpl(trylast=True)
def pytest_runtest_setup(item):
    logging.info("running dev-ops pre-test cleaner.")
    hosts = item.funcargs['base_config'].hosts
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
         futures = executor.map(setup, [host for name, host in hosts.items()])

    for future in futures:
        pass
