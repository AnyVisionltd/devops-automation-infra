import logging

from pytest_automation_infra.helpers import hardware_config
from devops_automation_infra.plugins.memsql import Memsql


@hardware_config(hardware={"host": {'gpu' :1}})
def test_basic(base_config):
    memsql = base_config.hosts.host.Memsql
    dbs = memsql.fetch_all("show databases")
    logging.info("<<<<<<<MEMSQL PLUGIN FUNCTIONING PROPERLY>>>>>>>>>>>>.")
