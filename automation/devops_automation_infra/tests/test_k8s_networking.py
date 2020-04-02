import logging

from automation_infra.utils.waiter import wait_for_predicate, wait_for_predicate_nothrow
from automation_infra.plugins.ssh_direct import SshDirect, SSHCalledProcessError
from pytest_automation_infra.helpers import hardware_config
from devops_automation_infra.plugins.power import Power
from devops_automation_infra.plugins.gravity import Gravity
from devops_automation_infra.plugins.k8s import K8s
from devops_automation_infra.utils.k8s_utils import create_deployment_with_replicas
from devops_automation_infra.utils.health_check import host_is_active


def pod_is_live(host, ip, port, timeout=10):
    try:
        res = host.SshDirect.execute(f"curl --max-time {timeout} http://{ip}:{port}")
        return res
    except SSHCalledProcessError as e:
        logging.error(e.output)


@hardware_config(hardware={"host1": {}, "host2": {}})
def test_cluster_network_master_restart(base_config,
                                        clean_up_all_deployments_and_svcs,
                                        amount_of_replicas=100,
                                        docker_image_name='gcr.io/hello-minikube-zero-install/hello-node',
                                        deployment_name="test"):
    # Clean up before test starts
    base_config.hosts.host1.SshDirect.connect(timeout=60)
    create_deployment_with_replicas(base_config.hosts.host1, deployment_name, docker_image_name, amount_of_replicas)
    wait_for_predicate(
        lambda: base_config.hosts.host1.K8s.number_ready_pods_in_deployment(deployment_name) == amount_of_replicas,
        timeout=300)
    base_config.hosts.host1.Power.reboot()
    # Check host has started again
    wait_for_predicate_nothrow(lambda: host_is_active(base_config.hosts.host1.ip), timeout=60)
    base_config.hosts.host1.SshDirect.connect(timeout=60)
    wait_for_predicate(lambda: base_config.hosts.host1.Gravity.is_cluster_healthy(),
                       timeout=120,
                       interval=5)
    deployment_pod_ips = wait_for_predicate_nothrow(
        lambda: base_config.hosts.host1.K8s.get_deployments_pod_internal_ips(deployment_name),
        timeout=300)
    assert len(deployment_pod_ips) == amount_of_replicas
    for pod_ip in deployment_pod_ips:
        res = pod_is_live(base_config.hosts.host1, ip=pod_ip, port=8080)
        assert res == "Hello World!"
