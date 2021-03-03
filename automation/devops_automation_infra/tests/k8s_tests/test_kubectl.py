import logging

from devops_automation_infra.k8s_plugins.kubectl import Kubectl
from devops_automation_infra.k8s_plugins.proxy_daemonset import ProxyDaemonSet
from pytest_automation_infra.helpers import hardware_config


@hardware_config(hardware={"host1": {"hardware_type": "vm", "base_image": "gravity_infra_230"}},
                 grouping={"cluster1": {"hosts": ["host2"]}})
def test_kubectl(base_config):
    host = base_config.hosts.host1
    ssh = host.SshDirect
    cluster = base_config.clusters.cluster1
    base_config.clusters.cluster1.ProxyDaemonSet._num_ready_pods()
    cluster.Kubectl.verify_functionality()
    logging.info(base_config.clusters.cluster1.ProxyDaemonSet)


