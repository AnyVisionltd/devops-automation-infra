import logging
import time
import pytest

from automation_infra.utils import waiter
from devops_automation_infra.plugins.docker import Docker
from pytest_automation_infra.helpers import hardware_config
from devops_automation_infra.plugins.consul import Consul


@hardware_config(hardware={"host": {}})
def test_consul(base_config):
    host = base_config.hosts.host
    consul_pg = base_config.hosts.host.Consul
    host.Docker.run_container_by_service("_consul")
    consul_pg.ping()
    consul_pg.verify_functionality()
    logging.info(f"<<<<<<<<<<<<<CONSUL PLUGIN FUNCTIONING PROPERLY>>>>>>>>>>>>>")
    logging.info(f"cleaning and restarting container..")
    host.Docker.kill_container_by_service("_consul")
    with pytest.raises(Exception):
        consul_pg.ping()
    host.Consul.clear_and_start()
    start = time.time()
    waiter.wait_for_predicate_nothrow(consul_pg.ping)
    logging.info(f"waited for consul ping: {time.time() - start}")
    consul_pg.verify_functionality()
    logging.info(f"<<<<<<<<<<<<<CONSUL PLUGIN FUNCTIONING PROPERLY>>>>>>>>>>>>>")




