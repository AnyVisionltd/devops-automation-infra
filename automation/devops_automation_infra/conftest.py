import logging
import pytest

from automation_infra.utils.initializer import init_plugins as init_infra_plugins
from devops_automation_infra.utils.initializer import init_plugins as init_devops_plugins
from pytest_automation_infra import determine_scope


@pytest.fixture(scope=determine_scope)
def clean_up_all_deployments_and_svcs(base_config):
    k8s = base_config.hosts.host1.K8s
    k8s.delete_deployment(name="", all=True)
    k8s.delete_svc(svc_name="", all=True)
    yield
    k8s.delete_deployment(name="", all=True)
    k8s.delete_svc(svc_name="", all=True)


@pytest.hookimpl(trylast=True)
def pytest_runtest_setup(item):
    logging.info("running dev-ops pre-test cleaner.")
    hosts = item.funcargs['base_config'].hosts
    for name, host in hosts.items():
        # multi-threaded
        init_infra_plugins(host)
        init_devops_plugins(host)
        host.clean_between_tests()
