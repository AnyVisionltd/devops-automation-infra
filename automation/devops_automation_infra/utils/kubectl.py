import base64
import json
import os
import logging
from kubernetes.client import ApiException
import kubernetes

def create_generic_secret(client, name, data, namepace='default', type='Opaque'):
    v1 = kubernetes.client.CoreV1Api(client)
    sec = kubernetes.client.V1Secret()
    sec.metadata = kubernetes.client.V1ObjectMeta(name=name)
    sec.type = type
    sec.data = data
    v1.create_namespaced_secret(namespace=namepace, body=sec)


def create_image_pull_secret(client, docker_config_path=None):
    if not docker_config_path:
        docker_config_path = f"{os.environ['userhome']}/.docker/config.json"
    with open(docker_config_path, 'rb') as f:
        data = {'.dockerconfigjson': base64.b64encode(f.read()).decode()}

    try:
        create_generic_secret(client=client, namepace='default', name='imagepullsecret', type='kubernetes.io/dockerconfigjson', data=data)
    except ApiException as e:
        if e.status == 409:
            logging.debug("imagepullsecret is already exists")
        else:
            raise e


def is_stateful_set_ready(client, name, namespace='default'):
    v1 = kubernetes.client.AppsV1Api(client)
    sts = v1.read_namespaced_stateful_set_status(name=name, namespace=namespace)
    return sts.status.replicas == sts.status.ready_replicas