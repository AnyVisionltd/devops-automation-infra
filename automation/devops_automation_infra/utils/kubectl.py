import base64
import os
import logging
from kubernetes.client import ApiException
import kubernetes
from kubernetes.stream import stream


def get_pods_by_label(kubectl_client, label, namespace='default'):
    v1 = kubernetes.client.CoreV1Api(kubectl_client)
    pods = v1.list_namespaced_pod(namespace=namespace, label_selector=label)
    return pods.items


def create_generic_secret(client, name, data, namespace='default', type='Opaque'):
    v1 = kubernetes.client.CoreV1Api(client)
    sec = kubernetes.client.V1Secret()
    sec.metadata = kubernetes.client.V1ObjectMeta(name=name)
    sec.type = type
    sec.data = data
    v1.create_namespaced_secret(namespace=namespace, body=sec)


def create_image_pull_secret(client, docker_config_path=None):
    if not docker_config_path:
        docker_config_path = f"{os.environ['userhome']}/.docker/config.json"
    with open(docker_config_path, 'rb') as f:
        data = {'.dockerconfigjson': base64.b64encode(f.read()).decode()}

    try:
        create_generic_secret(client=client, namespace='default', name='imagepullsecret', type='kubernetes.io/dockerconfigjson', data=data)
    except ApiException as e:
        if e.status == 409:
            logging.debug("imagepullsecret is already exists")
        else:
            raise e


def is_stateful_set_ready(client, name, namespace='default'):
    v1 = kubernetes.client.AppsV1Api(client)
    sts = v1.read_namespaced_stateful_set_status(name=name, namespace=namespace)
    return sts.status.replicas == sts.status.ready_replicas


def get_pod_names_by_labels(kubectl_client, namespace, label):
    pod_list = get_pods_by_label(kubectl_client, namespace, label)
    return [pod.metadata.name for pod in pod_list]


def pod_exec(kubectl_client, namespace, name, command, executable="/bin/bash"):
    corev1api = kubernetes.client.CoreV1Api(kubectl_client)
    response = stream(corev1api.connect_get_namespaced_pod_exec,
                  name, namespace, command=[executable, "-c"] + command.split(),
                  stderr=True, stdin=False, stdout=True, tty=False)
    return response


def get_secret_data(kubectl_client, namespace, name, path, decode=True):
    corev1api = kubernetes.client.CoreV1Api(kubectl_client)
    secret_list = corev1api.list_namespaced_secret(namespace)
    for secret in secret_list.items:
        if secret.metadata.name == name:
            return base64.b64decode(secret.data[path]) if decode else secret.data[path]