import logging

from devops_automation_infra.k8s_plugins.gravity import Gravity
from devops_automation_infra.k8s_plugins.kafka import Kafka
from devops_automation_infra.plugins.tunnel_manager import TunnelManager
from pytest_automation_infra.helpers import hardware_config


@hardware_config(hardware={"host1": {"hardware_type": "ai_camera", },
                           "host2": {"hardware_type": "vm", "base_image": "k8s_base", "installer": "k8s"},
                           "host3": {"hardware_type": "table", "node_type": "memsql"}},
                 grouping={"cluster1": {"hosts": ["host1", "host2"]},
                           "cluster2": {"hosts": ["host3"]}})
def example_decorator():
    return True


@hardware_config(hardware={"host1": {"hardware_type": "ai_camera"}},
                 grouping={"cluster1": {"hosts": ["host1"]}})
def test_kafka(base_config):
    host = base_config.hosts.host1
    ssh = host.SshDirect
    cluster = base_config.clusters.cluster1
    base_config.clusters.cluster1.Kafka.ping()


