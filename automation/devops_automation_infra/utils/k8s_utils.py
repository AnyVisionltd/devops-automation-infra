import base64
import json

from automation_infra.utils.waiter import wait_for_predicate
from kubernetes.stream import stream


def get_pod_names_by_labels(v1api, namespace, label):
    pod_names = []
    pod_list = v1api().list_namespaced_pod(namespace=namespace)
    for pod in pod_list.items:
        if pod.metadata.labels[label["key"]] == label["value"]:
            pod_names.append(pod.metadata.name)
    return pod_names


def pod_exec(v1api, namespace, name, command, executable="/bin/bash"):
    response = stream(v1api().connect_get_namespaced_pod_exec,
                  name, namespace, command=[executable, "-c"] + command.split(),
                  stderr=True, stdin=False, stdout=True, tty=False)
    return response


def get_secret_data(v1api, namespace, name, path, decode=True):
    secret_list = v1api().list_namespaced_secret(namespace)
    for secret in secret_list.items:
        if secret.metadata.name == name:
            return base64.b64decode(secret.data[path]) if decode else secret.data[path]


def create_deployment_with_replicas(host, name, docker_image, amount_of_replicas):
    wait_for_predicate(lambda: host.K8s.create_deployment(name, docker_image), timeout=120)
    host.K8s.scale_deployment(name, int(amount_of_replicas))
    host.K8s.expose_deployment(name)


def write_configmap_json_to_tmp_dir(configmap_file_name, configmap_json):
    with open(f"/tmp/{configmap_file_name}", "w") as config_map_file:
        json.dump(configmap_json, config_map_file)
    return f"/tmp/{configmap_file_name}"

