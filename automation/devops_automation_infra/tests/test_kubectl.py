import subprocess
import time

import yaml

from devops_automation_infra.k8s_plugins.gravity import Gravity
from devops_automation_infra.k8s_plugins.kubectl import Kubectl
from pytest_automation_infra.helpers import hardware_config


@hardware_config(hardware={"host1": {"hardware_type": "ai_camera", },
                           "host2": {"hardware_type": "vm", "base_image": "k8s_base", "installer": "k8s"},
                           "host3": {"hardware_type": "table", "node_type": "memsql"}},
                 grouping={"cluster1": {"hosts": ["host1", "host2"]},
                           "cluster2": {"hosts": ["host3"]}})
def example_decorator():
    pass


@hardware_config(hardware={"host1": {"hardware_type": "ai_camera", }},
                 grouping={"cluster1": {"hosts": ["host1"]}})
def test_kubectl(base_config):
    host = base_config.hosts.host1
    ssh = host.SshDirect
    cluster = base_config.clusters.cluster1
    import pdb; pdb.set_trace()

    cluster.Kubectl.verify_functionality()
    # password = cluster.Gravity._get_secret()

    # subprocess.run(f"sshpass -p {password} tsh login --proxy {host.ip}:32009 --user admin --insecure")


