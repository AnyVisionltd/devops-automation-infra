import json

from automation_infra.utils.waiter import wait_for_predicate


def create_deployment_with_replicas(host, name, docker_image, amount_of_replicas):
    wait_for_predicate(lambda: host.K8s.create_deployment(name, docker_image), timeout=120)
    host.K8s.scale_deployment(name, int(amount_of_replicas))
    host.K8s.expose_deployment(name)


def write_configmap_json_to_tmp_dir(configmap_file_name, configmap_json):
    with open(f"/tmp/{configmap_file_name}", "w") as config_map_file:
        json.dump(configmap_json, config_map_file)
    return f"/tmp/{configmap_file_name}"

