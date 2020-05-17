import json
import logging

from automation_infra.utils.waiter import wait_for_predicate, wait_for_predicate_nothrow, await_changing_result
from devops_automation_infra.utils.k8s_utils import write_configmap_json_to_tmp_dir
from infra.model import plugins
from automation_infra.plugins.ssh_direct import SshDirect, SSHCalledProcessError
from devops_automation_infra.utils.cmd_utils import convert_kwargs_to_options_string
from pytest_automation_infra.helpers import hardware_config


class K8s(object):

    def __init__(self, host):
        self._host = host

    @property
    def version(self, options=""):
        res = json.loads(self._host.SshDirect.execute(f"sudo gravity exec kubectl version {options} --output json"))
        return res['serverVersion']['gitVersion']

    def scale(self, name, resource_type="statefulset", replicas=1, options=""):
        return self._host.SshDirect.execute(f"sudo gravity exec kubectl scale {resource_type} --replicas={replicas} {options} {name}")

    def create(self, resource, options=""):
        try:
            return self._host.SshDirect.execute(f"sudo gravity exec kubectl create {resource} {options}")
        except SSHCalledProcessError as e:
            # We dont't want to fail immediately in case the k8s isn't available for a moment
            if "error: failed to discover supported resources" in e.output:
                return False

    def expose(self, resource, options=""):
        return self._host.SshDirect.execute(f"sudo gravity exec kubectl expose {resource} {options}")

    def get(self, resource, options=""):
        res = self._host.SshDirect.execute(f"sudo gravity exec kubectl get {resource} {options} --output json")
        return json.loads(res)

    def apply(self, command=""):
        return self._host.SshDirect.execute(f"sudo gravity exec kubectl apply {command}")

    def delete(self, resource, options=""):
        try:
            return self._host.SshDirect.execute(f"sudo gravity exec kubectl delete {resource} {options}")
        except SSHCalledProcessError as e:
            # We don't want to fail in case their isn't anything to delete
            if "not found" in e.output:
                pass
            logging.error(e.output)

    def get_pods(self, options=""):
        """
        :param options: all options the get pods commands can recevie from the normal k8s cli
        for example: --selector, --namespace etc...
        """
        return self.get(f"pods {options}")

    def create_deployment(self, name, image, **kwargs):
        options_string = convert_kwargs_to_options_string(kwargs)
        return self.create(f"deployment {name}", f"--image={image} {options_string}")

    def scale_deployment(self, name, replicas=100, **kwargs):
        options_string = convert_kwargs_to_options_string(kwargs)
        return self.scale(name, "deployment", replicas, options_string)

    def expose_deployment(self, name, port=30015, **kwargs):
        options_string = convert_kwargs_to_options_string(kwargs)
        return self.expose(f"deployment {name}", f"--type=LoadBalancer --port={port} {options_string}")

    def count_pods(self):
        res = self.get_pods()
        return len(res['items'])

    def get_deployment(self, name, **kwargs):
        options_string = convert_kwargs_to_options_string(kwargs)
        return self.get(f"deployment {name}", options_string)

    def delete_svc(self, svc_name, **kwargs):
        options_string = convert_kwargs_to_options_string(kwargs, format_with_equals_sign=True)
        self.delete(f"svc {svc_name}", options_string)

    def delete_deployment(self, name="", **kwargs):
        options_string = convert_kwargs_to_options_string(kwargs, format_with_equals_sign=True)
        self.delete(f"deployment {name}", options_string)

    def replace_config_map(self, config_map_file_path):
        self._host.SshDirect.execute(f"sudo gravity exec kubectl replace -f {config_map_file_path}")

    def get_deployments_pod_internal_ips(self, name):
        try:
            res = self.get_pods_using_selector_labels(label_value=name)
            # The place the PodIP is keept in k8s is different dependin on version
            if self.version >= "v1.17.0":
                return [pod['status']['podIPs'][0]['ip'] for pod in res['items']]
            elif self.version >= "v1.14.8":
                return [pod['status']['podIP'] for pod in res['items']]
        except KeyError as e:
            logging.error(f"Unable to get all deployments pods ips \n {e}")

    def insert_kv_into_configmap(self, key_value, service):
        configmap_name = self.configmap_name(service)
        configmap_json = self.configmap_json(configmap_name)
        updated_configmap_json = self.update_configmap(configmap_json, key_value)
        self.deploy_configmap(updated_configmap_json, service)

    def configmap_name(self, name):
        configmaps_json = self.get_configmaps()
        for configmap in configmaps_json['items']:
            if name in configmap['metadata']['name']:
                return configmap['metadata']['name']
        logging.error("Failed to get configmap name")

    def get_configmaps(self):
        return self.get(resource="configmaps")

    def configmap_json(self, name, **kwargs):
        options_string = convert_kwargs_to_options_string(kwargs)
        return self.get(resource=f"configmaps {name}", options=options_string)

    def update_configmap(self, configmap, kv):
        for key, value in kv.items():
            configmap['data'].update({f"{key.upper()}": value})
        return configmap

    def deploy_configmap(self, updated_configmap_json, service):
        local_host_configmap_path = write_configmap_json_to_tmp_dir(
            configmap_file_name=f"updated-configmap-{service}",
            configmap_json=updated_configmap_json
        )
        self._host.SshDirect.put(local_host_configmap_path, remotedir="/tmp")
        # /host is required to work with gravity mounted file system
        configmap_host_under_test_path = f"/host{local_host_configmap_path}"
        self.replace_config_map(configmap_host_under_test_path)
        self.restart_pod_by_service_name(service)

    def replace_config_map(self, config_map_file_path):
        self._host.SshDirect.execute(f"sudo gravity exec kubectl replace -f {config_map_file_path}")

    def restart_pod_by_service_name(self, service_name):
        self.delete_pod_by_service_name(service_name)
        wait_for_predicate(lambda: self.number_ready_pods_in_deployment(service_name) == 1)

    def delete_pod_by_service_name(self, service_name, **kwargs):
        service_name_selector_query = f"--selector=app=={service_name}"
        options_string = convert_kwargs_to_options_string(kwargs)
        self.delete(resource=f"pod {service_name_selector_query}", options=options_string)

    def number_ready_pods_in_deployment(self, name):
        try:
            res = self.get_deployment(name)
            return res['status']['readyReplicas']
        # The readyReplicas value isn't initialized by the k8s api immediately after the adding
        # of replicas so we need to wait for it to appear
        except KeyError:
            return 0

    def get_pods_using_selector_labels(self, label_value, label_name="app"):
        return self.get_pods(f"--selector={label_name}={label_value} --output json")

    def nodes(self):
        return json.loads(self._host.SshDirect.execute(f"kubectl get nodes --output json"))['items']

    def host_to_node_name(self, host):
        return host.SshDirect.execute("ip route get 1 | awk '{print $(NF-2);exit}'").strip()

    def label_node(self, node_name, *labels):
        try:
            return self._host.SshDirect.execute(f"kubectl label node {node_name} {' '.join(labels)}")
        except SSHCalledProcessError as e:
            if "already has a value" in e.output:
                logging.warning(f"Node already has this Node: {node_name} already has these {labels}")
                pass

    def taint_node(self, node_name, options):

        try:
            return self._host.SshDirect.execute(f"kubectl taint node {node_name} {options}")
        except SSHCalledProcessError as e:
            if "already has" in e.output:
                logging.warning(f"Node:{node_name} already tainted with this taint: {options}")
                pass

    def get_statefulset(self, name):
        res = self._host.SshDirect.execute(f"sudo gravity exec kubectl get statefulset {name} --output json")
        return json.loads(res)

    def get_all_sts_replicas_number(self, name):
        res = self.get_statefulset(name)
        return res['status']['replicas']

    def update_deployment_image(self, name, image):
        self._host.SshDirect.execute(f"sudo gravity exec kubectl set image deployments/{name} {name}={image}")
        # Indicates the updating of the image was for all pods successfully
        num_ready_pods = await_changing_result(self.number_ready_pods_in_deployment(name), ...)
        assert num_ready_pods == len(self.get_pods_using_selector_labels(label_value=name)['items'])

    def all_deployments_pods_running(self, name):
        return wait_for_predicate_nothrow(lambda: self.number_ready_pods_in_deployment(name) ==
                                           len(self.get_pods_using_selector_labels(label_value=name)['items']))


plugins.register("K8s", K8s)
