import logging

from pytest_automation_infra.helpers import hardware_config
from devops_automation_infra.plugins.consul import Consul


@hardware_config(hardware={"host": {'gpu' :1}})
def test_consul(base_config):
    consul_pg = base_config.hosts.host.Consul
    consul_pg.verify_functionality()

