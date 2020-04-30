from devops_automation_infra.plugins.memsql import Memsql
from devops_automation_infra.plugins.seaweed import Seaweed
from devops_automation_infra.plugins.kafka import Kafka
from devops_automation_infra.plugins.consul import Consul

from devops_automation_infra.utils import consul as consul_util


def init_plugins(host):
    """This method inits devops-automation-infra plugins (if necessary) so that when
        host.clean_between_tests is called the plugins exist for the host.
        New plugins implemented in this repo should be added to this list."""
    host.Memsql
    host.Consul
    host.Kafka
    host.Seaweed
    consul_util.backup_consul_keys(host)
