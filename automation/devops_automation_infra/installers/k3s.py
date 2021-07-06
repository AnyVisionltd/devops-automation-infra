import logging
import time
# import k8s
import gossip
from functools import partial

import kubernetes

from automation_infra.utils import concurrently, waiter
from devops_automation_infra.k8s_plugins.kubectl import Kubectl
from automation_infra.plugins.ssh_direct import SshDirect
from devops_automation_infra.utils import kubectl
from devops_automation_infra.installers import k8s


@gossip.register('session', tags=['k3s', 'devops_k3s'])
def setup_cluster(cluster, request):
    for host_name, config in request.function.__hardware_reqs.items():
        host = dict(cluster.hosts.items())[host_name]
        host.k3s_config = config['k3s_config']
        host.internal_ip = host.SshDirect.execute("hostname -I | awk {'print $1'}").strip()

    logging.info("Setting up k3s cluster")
    hosts = list(cluster.hosts.values())
    masters = [host for host in hosts if host.k3s_config["role"] == "master"]

    if not masters:
        raise Exception("Couldn't find any master node")
    main_master = next(iter(masters))
    main_master.k8s_name = "k3s-master"

    main_master.SshDirect.execute(
        "curl -sfL https://get.k3s.io | sh -s - --cluster-init --cluster-reset --cluster-reset-restore-path=/root/k3s-infra-1174-snapshot || true")
    waiter.wait_nothrow(lambda: main_master.SshDirect.execute("journalctl --since='1 min ago' | grep 'restart without'"))
    main_master.SshDirect.execute(
        "curl -sfL https://get.k3s.io | sh -s - --node-name=k3s-master --disable='servicelb,traefik,local-storage,metrics-server'")

    main_master.SshDirect.execute("sudo chmod o+r /etc/rancher/k3s/k3s.yaml")
    cluster_token = main_master.SshDirect.execute("sudo cat /var/lib/rancher/k3s/server/token").strip()
    cluster_ip = main_master.SshDirect.execute("hostname -I").strip()
    waiter.wait_nothrow(lambda: main_master.SshDirect.execute("kubectl get nodes"))

    nodes = [host for host in hosts if host.k3s_config['role'] == "node"]
    masters.remove(main_master)

    jobs = {}
    nodes_jobs = {f"{host.alias}": partial(_join_agent, host, cluster_ip, cluster_token) for host in nodes}
    masters_jobs = {f"{master.alias}": partial(_join_master, master, cluster_ip, cluster_token) for master in masters}
    jobs.update(nodes_jobs)
    jobs.update(masters_jobs)
    if jobs:
        concurrently.run(jobs)

    logging.info("Waiting for cluster to be Ready...")
    k8s_client = cluster.Kubectl.client()
    v1 = kubernetes.client.CoreV1Api(k8s_client)
    waiter.wait_for_predicate(lambda: len(v1.list_node().items) == len(hosts), timeout=30)
    logging.info(f"Number of nodes in cluster: {len(v1.list_node().items)}")
    waiter.wait_for_predicate(lambda: kubectl.is_cluster_ready(k8s_client), timeout=60)

    logging.info("Adding node labels and taints")
    _label_and_taint_nodes(k8s_client, hosts)

    # k8s.deploy_proxy_pod(cluster, request)


def _join_agent(host, cluster_ip, cluster_token):
    join_cmd = f"curl -sfL https://get.k3s.io | K3S_URL=https://{cluster_ip}:6443 K3S_TOKEN={cluster_token} sh -s -"
    host.SshDirect.execute(join_cmd)
    waiter.wait_nothrow(lambda: host.SshDirect.execute("systemctl is-active --quiet k3s-agent"), timeout=60)


def _join_master(host, cluster_ip, cluster_token):
    join_cmd = f"curl -sfL https://get.k3s.io | K3S_URL=https://{cluster_ip}:6443 K3S_TOKEN={cluster_token} sh -s - server || true"
    ssh = host.SshDirect
    ssh.execute("sudo systemctl stop k3s")
    ssh.execute("sudo rm -rf /var/lib/rancher/k3s/server")
    ssh.execute(join_cmd)
    ssh.execute("sudo chmod o+r /etc/rancher/k3s/k3s.yaml")
    waiter.wait_nothrow(lambda: host.SshDirect.execute("sudo kubectl get nodes"), timeout=60)


def _label_and_taint_nodes(k8s_client, hosts):
    v1 = kubernetes.client.CoreV1Api(k8s_client)

    for host in hosts:
        """
        In order to link between host from hardware request and k8s node, we need to check if the internal ip
        listed in etcd matches the internal ip of the host, for the initials master there's no need to do so
        because we already know what's his k8s node name (k3s-master). 
        """
        if not hasattr(host, "k8s_name"):
            for k8s_node in v1.list_node().items:
                if host.internal_ip == k8s_node.status.addresses[0].address:
                    host.k8s_name = k8s_node.metadata.name

            if not hasattr(host, "k8s_name"):
                raise Exception(f"Failed to find k8s node that matches host {host.alias} ip: {host.internal_ip}")

        if "labels" in host.k3s_config:
            kubectl.label_node(k8s_client, host.k8s_name, host.k3s_config['labels'])

        if "taints" in host.k3s_config:
            kubectl.taint_node(k8s_client, host.k8s_name, host.k3s_config['taints'])