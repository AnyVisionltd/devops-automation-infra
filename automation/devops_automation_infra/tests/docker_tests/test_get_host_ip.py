import logging

from devops_automation_infer.utils.host import get_host_ip
from pytest_automation_infra.helpers import hardware_config


@hardware_config(hardware={"host": {}})
def test_get_host_ip(base_config):
    ip = get_host_ip(base_config.hosts.host)
    logging.info(f"get_host_ip got ip {ip}")
    assert ip
