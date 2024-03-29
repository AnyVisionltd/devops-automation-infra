import base64
import os
import logging
from kubernetes.client import ApiException
import kubernetes
from kubernetes.stream import stream
from automation_infra.utils import waiter
import uuid


def get_pods_by_label(kubectl_client, label, namespace='default'):
    v1 = kubernetes.client.CoreV1Api(kubectl_client)
    pods = v1.list_namespaced_pod(namespace=namespace, label_selector=label)
    return pods.items


def get_nodes_by_label(client, label):
    v1 = kubernetes.client.CoreV1Api(client)
    return v1.list_node(label_selector=label).items


def get_stateful_set(client, name, namespace="default"):
    v1 = kubernetes.client.AppsV1Api(client)
    return v1.read_namespaced_stateful_set(name=name, namespace=namespace)


def get_deployment(client, name, namespace="default"):
    v1 = kubernetes.client.AppsV1Api(client)
    return v1.read_namespaced_deployment(name=name, namespace=namespace)


def get_config_map_envs(client, name, namespace="default"):
    v1 = kubernetes.client.CoreV1Api(client)
    return v1.read_namespaced_config_map(name, namespace).data


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
        create_generic_secret(client=client, namespace='default', name='imagepullsecret',
                              type='kubernetes.io/dockerconfigjson', data=data)
    except ApiException as e:
        if e.status == 409:
            logging.debug("imagepullsecret is already exists")
        else:
            raise e


def is_stateful_set_ready(client, name, namespace='default'):
    v1 = kubernetes.client.AppsV1Api(client)
    sts = v1.read_namespaced_stateful_set_status(name=name, namespace=namespace)
    return sts.status.replicas == sts.status.ready_replicas


def is_deployment_ready(client, name, namespace='default'):
    v1 = kubernetes.client.AppsV1Api(client)
    deployment = v1.read_namespaced_deployment(name=name, namespace=namespace)
    return deployment.status.replicas == deployment.status.ready_replicas


def is_daemon_set_ready(client, name, namespace='default'):
    v1 = kubernetes.client.AppsV1Api(client)
    ds = v1.read_namespaced_daemon_set(name=name, namespace=namespace)
    return ds.status.desired_number_scheduled == ds.status.number_ready


def pod_exec(kubectl_client, namespace, name, command, executable="/bin/bash"):
    corev1api = kubernetes.client.CoreV1Api(kubectl_client)
    response = stream(corev1api.connect_get_namespaced_pod_exec,
                      name, namespace, command=[executable, "-c"] + command.split(),
                      stderr=True, stdin=False, stdout=True, tty=False)
    return response


def get_secret_data(kubectl_client, namespace, name, path, decode=True):
    corev1api = kubernetes.client.CoreV1Api(kubectl_client)
    secret = corev1api.read_namespaced_secret(namespace=namespace, name=name)
    return base64.b64decode(secret.data[path]) if decode else secret.data[path]


def scale_stateful_set(client, replicas, name, namespace='default', timeout=30):
    v1 = kubernetes.client.AppsV1Api(client)
    v1.patch_namespaced_stateful_set_scale(name=name, namespace=namespace, body={'spec': {'replicas': replicas}})
    waiter.wait_for_predicate(
        lambda: v1.read_namespaced_stateful_set_scale(name=name, namespace=namespace).status.replicas
                == replicas, timeout=timeout)


def scale_deployment(client, replicas, name, namespace='default'):
    v1 = kubernetes.client.AppsV1Api(client)
    v1.patch_namespaced_deployment_scale(name=name, namespace=namespace, body={'spec': {'replicas': replicas}})
    waiter.wait_for_predicate(
        lambda: v1.read_namespaced_deployment_scale(name=name, namespace=namespace).status.replicas
                == replicas, timeout=30)


def delete_pvc(client, name, namespace='default', clear_data=False):
    v1 = kubernetes.client.CoreV1Api(client)
    if clear_data:
        pv_name = v1.read_namespaced_persistent_volume_claim(name=name, namespace=namespace).spec.volume_name
        v1.patch_persistent_volume(name=pv_name, body={'spec': {'persistentVolumeReclaimPolicy': 'Delete'}})
    v1.delete_namespaced_persistent_volume_claim(name=name, namespace=namespace)


def delete_stateful_set_data(client, name, namespace='default', clear_data=False, timeout=60):
    v1_app = kubernetes.client.AppsV1Api(client)
    v1_core = kubernetes.client.CoreV1Api(client)
    sts_spec = v1_app.read_namespaced_stateful_set(name=name, namespace=namespace).spec
    replicas = sts_spec.replicas

    scale_stateful_set(client, 0, name, namespace, timeout=timeout)
    if sts_spec.volume_claim_templates:
        claim_templates = [volume.metadata.name for volume in sts_spec.volume_claim_templates]
        pvcs_to_delete = []

        for template in claim_templates:
            for i in range(0, replicas):
                pvcs_to_delete.append(f"{template}-{name}-{i}")

        for pvc in pvcs_to_delete:
            delete_pvc(client, pvc, namespace, clear_data)
            waiter.wait_for_predicate(lambda: pvc not in [pvc_object.metadata.name for pvc_object in
                                                          v1_core.list_namespaced_persistent_volume_claim(
                                                              namespace).items],
                                      timeout=10, interval=0.5)
    scale_stateful_set(client, replicas, name, namespace, timeout=timeout)
    waiter.wait_for_predicate(lambda: is_stateful_set_ready(client, name), timeout=timeout)


def delete_deployment_data(client, name, namespace='default', clear_data=False):
    v1_app = kubernetes.client.AppsV1Api(client)
    deployment_spec = v1_app.read_namespaced_deployment(name=name, namespace=namespace).spec
    replicas = deployment_spec.replicas

    scale_deployment(client, 0, name, namespace)

    pvcs_to_delete = [volume.persistent_volume_claim.claim_name for volume in deployment_spec.template.spec.volumes
                      if volume.persistent_volume_claim]
    for pvc in pvcs_to_delete:
        delete_pvc(client, pvc, namespace, clear_data)

    scale_deployment(client, replicas, name, namespace)


def recycle_pvc(client, pvc_name, namespace='default', timeout=60):
    k8s_client = kubernetes.client
    v1 = k8s_client.CoreV1Api(client)
    try:
        v1.read_namespaced_persistent_volume_claim(name=pvc_name, namespace=namespace)
    except ApiException as e:
        if e.status == 404:
            raise ApiException(f"Couldn't find pvc {pvc_name} in namespace {namespace}")

    container = kubernetes.client.V1Container(
        name="pv-cleaner",
        command=["/bin/sh", "-c", "rm -rf /scrub/*"],
        image="k8s.gcr.io/busybox",
        volume_mounts=[k8s_client.V1VolumeMount(name="pvc-volume", mount_path="/scrub")]
    )

    volume = k8s_client.V1Volume(
        name="pvc-volume",
        persistent_volume_claim=k8s_client.V1PersistentVolumeClaimVolumeSource(claim_name=pvc_name))
    pod_spec = k8s_client.V1PodSpec(volumes=[volume], containers=[container], restart_policy="Never")
    pod_name = f"pv-cleaner-{str(uuid.uuid4())[:6]}"
    pod = k8s_client.V1Pod(metadata=k8s_client.V1ObjectMeta(name=pod_name), spec=pod_spec)

    v1 = k8s_client.CoreV1Api(client)
    v1.create_namespaced_pod(namespace=namespace, body=pod)

    try:
        waiter.wait_for_predicate(
            lambda: v1.read_namespaced_pod(
                name=pod_name, namespace=namespace).status.phase == "Succeeded", timeout=timeout)

    except TimeoutError as e:
        logging.debug(v1.read_namespaced_pod(name=pod_name, namespace=namespace).status)
        raise e

    v1.delete_namespaced_pod(name=pod_name, namespace=namespace)


def get_job_status(client, job_name, namespace='default'):
    v1 = kubernetes.client.BatchV1Api(client)
    return v1.read_namespaced_job(namespace=namespace, name=job_name).status


def wait_for_job_to_succeed(client, job_name, namespace='default', timeout=60):
    waiter.wait_for_predicate(lambda: get_job_status(client, namespace=namespace, job_name=job_name).succeeded == 1,
                              timeout=timeout)


def is_cluster_ready(client):
    v1 = kubernetes.client.CoreV1Api(client)
    nodes = v1.list_node().items
    ready_nodes = []
    for node in nodes:
        for cond in node.status.conditions:
            if cond.type == "Ready" and cond.status == "True":
                ready_nodes.append(node)

    return len(nodes) == len(ready_nodes)


def label_node(client, node_name, labels):
    v1 = kubernetes.client.CoreV1Api(client)
    body = {
        "metadata": {
            "labels": labels
        }
    }
    v1.patch_node(node_name, body)


def add_label_to_node(client, node_name, key, value):
    v1 = kubernetes.client.CoreV1Api(client)
    body = {
        "metadata": {
            "labels": {
                key: value
            }
        }
    }
    v1.patch_node(node_name, body)


def taint_node(client, node_name, taints):
    v1 = kubernetes.client.CoreV1Api(client)
    list_of_taints = []

    for label, effect in taints.items():
        k, v = label.split('=')
        list_of_taints.append(kubernetes.client.V1Taint(key=k, value=v, effect=effect))

    body = {
        "spec": {
            "taints": list_of_taints
        }
    }

    v1.patch_node(node_name, body)


def delete_pods_by_label(client, label, namespace="default"):
    pods_to_delete = [pod.metadata.name for pod in get_pods_by_label(client, label=label, namespace=namespace)]
    v1 = kubernetes.client.CoreV1Api(client)
    for pod in pods_to_delete:
        v1.delete_namespaced_pod(name=pod, namespace=namespace)


def edit_statefulset(client, name, namespace='default', new_env_var=None):
    v1_app = kubernetes.client.AppsV1Api(client)
    v1_app.read_namespaced_stateful_set(name, namespace)
    sts_info = v1_app.read_namespaced_stateful_set(name=name, namespace=namespace)
    sts_info.spec.template.spec.containers[0].env.append(new_env_var)
    v1_app.replace_namespaced_stateful_set(name, namespace, sts_info)

def add_env_to_workload(client, name, namespace='default',workload_type='deployment', envs=None):
    v1_app = kubernetes.client.AppsV1Api(client)
    if workload_type =='deployment':
        deployment_info = v1_app.read_namespaced_deployment(name=name, namespace=namespace)
        for env in envs:
            deployment_info.spec.template.spec.containers[0].env.append(env)
        v1_app.replace_namespaced_deployment(name, namespace, deployment_info)
    if workload_type == 'statefulset':
        stateful_set_info = v1_app.read_namespaced_stateful_set(name=name, namespace=namespace)
        for env in envs:
            stateful_set_info.spec.template.spec.containers[0].env.append(env)
        v1_app.replace_namespaced_stateful_set(name, namespace, stateful_set_info)


def add_env_to_deployment(client, name, namespace='default', envs=None):
    v1_app = kubernetes.client.AppsV1Api(client)
    v1_app.read_namespaced_deployment(name, namespace)
    deployment_info = v1_app.read_namespaced_deployment(name=name, namespace=namespace)
    for env in envs:
        deployment_info.spec.template.spec.containers[0].env.append(env)
    v1_app.replace_namespaced_deployment(name, namespace, deployment_info)


def change_env_from_deployment(client, name, env_name, namespace='default', new_env_var=None):
    v1_app = kubernetes.client.AppsV1Api(client)
    v1_app.read_namespaced_deployment(name, namespace)
    deployment_info = v1_app.read_namespaced_deployment(name=name, namespace=namespace)
    desired_env_index = -1
    envs = deployment_info.spec.template.spec.containers[0].env
    for index, env in enumerate(envs):
        if env.name == env_name:
            desired_env_index = index
            break
    envs[desired_env_index] = new_env_var
    v1_app.replace_namespaced_deployment(name, namespace, deployment_info)

def disable_liveness_probe(client, name, namespace='default'):
    v1_app = kubernetes.client.AppsV1Api(client)
    v1_app.read_namespaced_deployment(name, namespace)
    deployment_info = v1_app.read_namespaced_deployment(name=name, namespace=namespace)
    deployment_info.spec._template.spec.containers[0].liveness_probe = None
    v1_app.replace_namespaced_deployment(name, namespace, deployment_info)
