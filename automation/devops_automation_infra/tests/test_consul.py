
from pytest_automation_infra.helpers import hardware_config
from devops_automation_infra.plugins.consul import Consul

@hardware_config(hardware={"host": {'gpu' :1}})
def test_consul(base_config):
    consul_pg = base_config.hosts.host.Consul
    services = consul_pg.get_services()
    assert 'camera-service' in services
    consul_pg.put_key("Test/service/", "51")
    assert int(consul_pg.get_key("Test/service/")) == 51
