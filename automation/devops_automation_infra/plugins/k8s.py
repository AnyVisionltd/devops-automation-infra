import json
import logging

from infra.model import plugins
from automation_infra.plugins.ssh_direct import SshDirect, SSHCalledProcessError
from pytest_automation_infra import helpers
from devops_automation_infra.utils.cmd_utils import convert_kwargs_to_options_string


class K8s(object):

    def __init__(self, host):
        self._host = host

    @property
    def version(self, options=""):
        res = json.loads(self._host.SshDirect.execute(f"sudo gravity exec kubectl version {options} --output json"))
        return res['serverVersion']['gitVersion']

    def scale(self, resource, replicas=20):
        return self._host.SshDirect.execute(f"sudo gravity exec kubectl scale {resource} {replicas}")

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

    def get_pods_using_selector(self, selector, selector_type="app"):
        return self.get_pods(f"--selector={selector_type}={selector}")

    def get_deployment(self, name, **kwargs):
        options_string = convert_kwargs_to_options_string(kwargs)
        return self.get(f"deployment {name}", options_string)

    def delete_svc(self, svc_name, **kwargs):
        options_string = convert_kwargs_to_options_string(kwargs, format_with_equals_sign=True)
        self.delete(f"svc {svc_name}", options_string)

    def delete_deployment(self, name="", **kwargs):
        options_string = convert_kwargs_to_options_string(kwargs, format_with_equals_sign=True)
        self.delete(f"deployment {name}", options_string)

    def get_ready_deployment_pods(self, name):
        try:
            res = self.get_deployment(name)
            return res['status']['readyReplicas']
        # The readyReplicas value isn't initialized by the k8s api immediately after the adding
        # of replicas so we need to wait for it to appear
        except KeyError:
            return 0

    def get_deployments_pod_internal_ips(self, name):
        try:
            res = self.get_pods_using_selector(selector=name)
            # The place the PodIP is keept in k8s is different dependin on version
            if self.version >= "v1.17.0":
                return [pod['status']['podIPs'][0]['ip'] for pod in res['items']]
            elif self.version >= "v1.14.8":
                return [pod['status']['podIP'] for pod in res['items']]
        except KeyError as e:
            logging.error(f"Unable to get all deployments pods ips \n {e}")


plugins.register("K8s", K8s)
