import json
import logging
import requests

from automation_infra.plugins.ssh_direct import SSHCalledProcessError
from infra.model import cluster_plugins
from devops_automation_infra.k8s_plugins.kubectl import Kubectl
from devops_automation_infra.k8s_plugins.gravity import Gravity
from devops_automation_infra.utils import kubectl as kubectl_utils


class Rancher:
    def __init__(self, cluster, port="9443"):
        self._cluster = cluster
        self._port = port
        self.BASE_URL = f"https://{self._cluster.master.ip}:{self._port}"
        self.auth_header = {"Authorization": f"Bearer {self.token}"}
    
    @property
    def port(self):
        return self._port

    @property
    def kubectl_client(self):
        return self._cluster.Kubectl.client
    
    @property
    def gravity(self):
        return self._cluster.Gravity
        
    @property
    def namespace(self):
        return "cattle-system"

    @property
    def token(self):
        rancher_secret = kubectl_utils.get_secret_data(self.kubectl_client, namespace="kube-system",
                                                       name="rancher-cli-token", path="cli2.json")
        return json.loads(rancher_secret)["Servers"]["rancherDefault"]["tokenKey"]

    def cli_login(self):
        cmd = f"rancher login {self.BASE_URL} --token {self.token} --skip-verify"
        res = self.gravity.exec(cmd)
        # Check login was successful
        assert "Saving config to" in res

    def refresh_catalog(self, catalog_name):
        self.clear_rancher_cache()
        self.gravity.exec(f"rancher catalog refresh --wait {catalog_name}")

    def project_details(self):
        res = requests.get(f"{self.BASE_URL}/v3/projects", headers=self.auth_header, verify=False)
        assert res.status_code == 200
        projects = res.json()['data']
        return [project for project in projects if project['name'] == 'Default'][0]

    def clear_rancher_cache(self):
        remove_cache_cmd = "rm -rf management-state/catalog-cache/*"
        rancher_pod_name = kubectl_utils.get_pod_names_by_labels(self.kubectl_client,
                                                                 namespace=self.namespace, label="app=rancher")[0]
        return kubectl_utils.pod_exec(self.kubectl_client, namespace=self.namespace,
                                      name=rancher_pod_name, command=remove_cache_cmd)

    def add_catalog(self, url, branch, name, username, password):
        data = {"type": "catalog", "kind": "helm", "branch": branch,
                "url": url, "name": name, "username": username,
                "password": password}
        res = requests.post(f"{self.BASE_URL}/v3/catalog",
                            headers=self.auth_header,
                            data=json.dumps(data),
                            verify=False)
        # 409 is ok since it means the  catalog already exists
        assert res.status_code == 201 or res.status_code == 409

    def delete_catalog(self, catalog_name):
        res = requests.post(f"{self.BASE_URL}/v3/catalog/{catalog_name}",
                            headers=self.auth_header,
                            verify=False)
        assert res.status_code == 404

    def wait_for_app(self, app_name, timeout):
        logging.info(f"Waiting for application to be available. see {self.BASE_URL} for status")
        self.gravity.exec(f"rancher wait {app_name} --timeout {timeout}")

    def upgrade_app(self, app_name, version, wait=True, timeout="120", **kwargs):
        cmd_options = ""
        for k, v in kwargs.items():
            cmd_options += f" --set {k}={v}"
            cmd_options += f" {app_name} {version}"
        cmd = f"rancher app upgrade {cmd_options}"
        self.gravity.exec(cmd)
        logging.debug(cmd)
        if wait:
            self.wait_for_app(app_name, timeout)

    def install_app(self, app_name, version, image_pull_policy="Always", docker_registry="", namespace="default",
                    wait=True, timeout="120", force=True, **kwargs):
        kwargs["global.localRegistry"] = docker_registry
        kwargs["global.pullPolicy"] = image_pull_policy
        cmd_options = ""
        if self.app_exists(app_name) and force:
            logging.info(f"{app_name} is Already exists, Running upgrade...")
            self.upgrade_app(app_name, version, **kwargs)
        else:
            rancher_cmd = "rancher app install"
            for k, v in kwargs.items():
                cmd_options += f" --set {k}={v}"
            cmd_options += f" --version {version} --namespace {namespace} {app_name} {app_name} --no-prompt"
            cmd = f"{rancher_cmd} {cmd_options}"
            logging.debug(cmd)
            self.gravity.exec(cmd)
            if wait:
                self.wait_for_app(app_name, timeout)

    def delete_app(self, app_name):
        self.gravity.exec(f"rancher app delete {app_name}")

    def app_exists(self, app_name):
        res = requests.get(f"{self.BASE_URL}/v3/project/local:p-8n6zr/apps/p-8n6zr%3A{app_name}",
                           headers=self.auth_header,
                           verify=False)
        assert res.status_code == 200 or res.status_code == 404
        return res.status_code != 404


cluster_plugins.register("Rancher", Rancher)

