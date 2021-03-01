import base64
import json
import kubernetes
from kubernetes.stream import stream


def get_pod_names_by_labels(kubectl_client, namespace, label):
    corev1api = kubernetes.client.CoreV1Api(kubectl_client())
    pod_list = corev1api.list_namespaced_pod(namespace=namespace, label_selector=label)
    return [pod.metadata.name for pod in pod_list.items]


def pod_exec(kubectl_client, namespace, name, command, executable="/bin/bash"):
    corev1api = kubernetes.client.CoreV1Api(kubectl_client())
    response = stream(corev1api.connect_get_namespaced_pod_exec,
                  name, namespace, command=[executable, "-c"] + command.split(),
                  stderr=True, stdin=False, stdout=True, tty=False)
    return response


def get_secret_data(kubectl_client, namespace, name, path, decode=True):
    corev1api = kubernetes.client.CoreV1Api(kubectl_client())
    secret_list = corev1api.list_namespaced_secret(namespace)
    for secret in secret_list.items:
        if secret.metadata.name == name:
            return base64.b64decode(secret.data[path]) if decode else secret.data[path]