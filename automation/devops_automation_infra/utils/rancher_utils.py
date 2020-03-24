import pytest

from automation_infra.utils.waiter import wait_for_predicate
from pytest_automation_infra import determine_scope
from devops_automation_infra.plugins.rancher import Rancher
from pytest_automation_infra.helpers import hardware_config


@pytest.fixture(scope=determine_scope, autouse=True)
def clean_up_core_product(base_config):
    rancher = base_config.hosts.host1.Rancher
    wait_for_predicate(lambda: rancher.delete_app(app_name="core-app"), timeout=30)
    wait_for_predicate(lambda: rancher.delete_app(app_name="core-init"), timeout=30)
    wait_for_predicate(lambda: rancher.delete_app(app_name="core-data"), timeout=30)
    yield
    wait_for_predicate(lambda: rancher.delete_app(app_name="core-app"), timeout=30)
    wait_for_predicate(lambda: rancher.delete_app(app_name="core-init"), timeout=30)
    wait_for_predicate(lambda: rancher.delete_app(app_name="core-data"), timeout=30)


def install_core_project_v2(base_config):
    rancher = base_config.hosts.host1.Rancher
    rancher.cli_login()
    wait_for_predicate(lambda: rancher.install_app(app_name="core-data"), timeout=300)
    wait_for_predicate(lambda: rancher.install_app(app_name="core-init"), timeout=300)
    wait_for_predicate(lambda: rancher.install_app(app_name="core-app"), timeout=300,
                       interval=10)
    assert "deploying" or "installing" not in rancher.app_list(), \
        "Not all rancher installation finish successfully"


@hardware_config(hardware={"host1": {}})
def test(base_config):
    install_core_project_v2(base_config)
