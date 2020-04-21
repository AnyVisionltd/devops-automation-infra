import json
import logging

from automation_infra.utils.waiter import wait_for_predicate, wait_for_predicate_nothrow
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

    def scale(self, resource, replicas=20):
        return self._host.SshDirect.execute(f"sudo gravity exec kubectl scale {resource} --replicas={replicas}")

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
        return self.scale(f"deployment {name}", f"--replicas={replicas} {options_string}")

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

    def add_pipeng_replicas(self, replicas=1, hosts=[]):
        if replicas <= len(self.nodes()):
            for host in hosts:
                self.prepare_node_for_pipeng(host)
            self.scale_pipeng(replicas=replicas)
            wait_for_predicate(lambda: self.number_pipeng_ready_pods() == replicas, timeout=120)
        else:
            logging.warning(" All nodes already meet the requirements for PIPENG")

    def nodes(self):
        return json.loads(self._host.SshDirect.execute(f"kubectl get nodes --output json"))['items']

    def prepare_node_for_pipeng(self, host):
        pipe_label = 'pipe=true'
        nvidia_driver_label = 'nvidia-driver=true'
        node_name = self.host_to_node_name(host)

        self.label_node(node_name, pipe_label, nvidia_driver_label)
        wait_for_predicate_nothrow(lambda: host.SshDirect.gpu_count() > 0, timeout=500)
        self.taint_node(node_name, options='pipe=true:NoSchedule')

    def host_to_node_name(self, host):
        return host.SshDirect.execute("ip route get 1 | awk '{print $(NF-2);exit}'").strip()

    def label_node(self, node_name, *labels, **kwargs):
        options_string = convert_kwargs_to_options_string(kwargs, format_with_equals_sign=True)
        try:
            return self._host.SshDirect.execute(f"kubectl label node {node_name} {' '.join(labels)} {options_string}")
        except SSHCalledProcessError as e:
            if "already has a value" in e.output:
                logging.warning(f"Node already has this Node: {node_name} already has these {labels}")
                pass

    def taint_node(self, node_name, options, **kwargs):
        options_string = convert_kwargs_to_options_string(kwargs, format_with_equals_sign=True)
        try:
            return self._host.SshDirect.execute(f"kubectl taint node {node_name} {options} {options_string} ")
        except SSHCalledProcessError as e:
            if "already has" in e.output:
                logging.warning(f"Node:{node_name} already tainted with this taint: {options}")
                pass

    def scale_pipeng(self, replicas):
        return self.scale(f"sts pipeng", f"--replicas={replicas}")

    def number_pipeng_ready_pods(self):
        pipeng_sts = self.get_statefulset('pipeng')
        return pipeng_sts['status']['readyReplicas']

    def get_statefulset(self,name):
        res = self._host.SshDirect.execute(f"sudo gravity exec kubectl get statefulset {name} --output json")
        return json.loads(res)


plugins.register("K8s", K8s)


@hardware_config(hardware={'host1': {'gpu': 1}, 'host2': {'gpu': 1}, 'host3': {'gpu': 1}, 'host5': {'gpu': 1}})
def test_scale_pipeng(base_config):
    base_config.hosts.host1.K8s.add_pipeng_replicas(replicas=4, hosts=[base_config.hosts.host5])
