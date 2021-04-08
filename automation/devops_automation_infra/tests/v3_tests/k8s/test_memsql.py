import logging

from devops_automation_infra.k8s_plugins.memsql import Memsql
from pytest_automation_infra.helpers import hardware_config
from devops_automation_infra.installers import k8s
from devops_automation_infra.utils import memsql

@hardware_config(hardware={"host1": {"hardware_type": "vm", "base_image": "gravity_infra_230"}},
                 grouping={"cluster1": {"hosts": ["host1"], "installer": "k8s"}})
def test_memsql(base_config):
    cluster = base_config.clusters.cluster1
    memsql_client = cluster.Memsql.connection()
    memsql.truncate_all(memsql_client)