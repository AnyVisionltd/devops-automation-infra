import kubernetes

from automation_infra.utils import waiter
from devops_automation_infra.utils import kubectl


def clear_data(cluster):
    client = cluster.Kubectl.client()
    kubectl.delete_stateful_set_data(client, "vernemq", timeout=200)
    coreV1 = kubernetes.client.CoreV1Api(client)
    coreV1.delete_namespaced_pod("vernemq-0", namespace='default')
    appV1 = kubernetes.client.AppsV1Api(client)
    waiter.wait_for_predicate_nothrow(
        lambda: appV1.read_namespaced_stateful_set('vernemq', 'default').status.ready_replicas == 1)
