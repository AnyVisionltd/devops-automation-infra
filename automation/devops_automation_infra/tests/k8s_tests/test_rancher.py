from pytest_automation_infra.helpers import hardware_config
from devops_automation_infra.plugins.Rancher import Rancher

@hardware_config(hardware={"host": {}})
def test_first(base_config):
    rancher = base_config.hosts.host.Rancher
    rancher.cli_login()
    rancher.project_details()
    rancher.clear_rancher_cache()