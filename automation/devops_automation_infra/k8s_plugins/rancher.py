import json
import logging
import os
import time

import yaml
import requests

from automation_infra.plugins.ssh_direct import SSHCalledProcessError
from infra.model import cluster_plugins
from devops_automation_infra.k8s_plugins.kubectl import Kubectl
from devops_automation_infra.k8s_plugins.gravity import Gravity
from devops_automation_infra.utils import kubectl as kubectl_utils


class Rancher:
    def __init__(self, cluster):
        self._cluster = cluster
        self._port = "9443"
        self.auth_header = {"Authorization": f"Bearer {self.token}"}
        self.alias = "rancher.anv"

    @property
    def base_url(self):
        return f"https://{self._cluster.K8SMaster().ip}:{self._port}"

    @property
    def token(self):
        rancher_secret = kubectl_utils.get_secret_data(self._cluster.Kubectl.client(), namespace="kube-system",
                                                       name="rancher-cli-token", path="cli2.json")
        return json.loads(rancher_secret)["Servers"]["rancherDefault"]["tokenKey"]

    @property
    def _default_project_id(self):
        return self.project_details()["id"]

    def cli_execute(self, cmd):
        self.cli_login()
        return self._execute(cmd)

    def _execute(self, cmd):
        ssh = self._cluster.K8SMaster().SshDirect
        try:
            ssh.execute("which rancher")
        except SSHCalledProcessError:
            return self._cluster.Gravity.exec(cmd)

        return ssh.execute(cmd)

    def cli_login(self):
        cmd = f"rancher login https://{self.alias} --token {self.token} --skip-verify"
        self._execute(f"echo '127.0.0.1 rancher.anv' | sudo tee /etc/hosts -a > /dev/null 2>&1")
        self._execute(cmd)

    def refresh_catalog(self, catalog_name):
        self.clear_cache()
        self.cli_execute(f"rancher catalog refresh --wait {catalog_name}")

    def project_details(self):
        res = requests.get(f"{self.base_url}/v3/projects", headers=self.auth_header, verify=False)
        assert res.status_code == 200
        projects = res.json()['data']
        return [project for project in projects if project['name'] == 'Default'][0]

    def clear_cache(self):
        remove_cache_cmd = "rm -rf management-state/catalog-cache/*"
        rancher_pod_name = [pod for pod in kubectl_utils.get_pods_by_label(self._cluster.Kubectl.client(), namespace="cattle-system", label="app=rancher")
                            if pod.status.phase == "Running"][0].metadata.name
        return kubectl_utils.pod_exec(self._cluster.Kubectl.client(), namespace="cattle-system",
                                      name=rancher_pod_name, command=remove_cache_cmd)

    def add_catalog(self, url, branch, name, username, password):
        data = {"type": "catalog", "kind": "helm", "branch": branch,
                "url": url, "name": name, "username": username,
                "password": password}
        res = requests.post(f"{self.base_url}/v3/catalog",
                            headers=self.auth_header,
                            data=json.dumps(data),
                            verify=False)
        # 409 is ok since it means the  catalog already exists
        assert res.status_code == 201 or res.status_code == 409
        self.refresh_catalog(name)

    def delete_catalog(self, catalog_name):
        res = requests.post(f"{self.base_url}/v3/catalog/{catalog_name}",
                            headers=self.auth_header,
                            verify=False)
        assert res.status_code == 404

    def wait_for_app(self, app_name, timeout):
        logging.info(f"Waiting for application to be available. see {self.base_url} for status")
        self.cli_execute(f"rancher wait {app_name} --timeout {timeout}")

    def upgrade_app(self, app_name, version, wait=True, timeout="120", **kwargs):
        cmd_options = ""
        for k, v in kwargs.items():
            cmd_options += f" --set {k}={v}"
            cmd_options += f" {app_name} {version}"
        cmd = f"rancher app upgrade {cmd_options}"
        self.cli_execute(cmd)
        logging.debug(cmd)
        if wait:
            self.wait_for_app(app_name, timeout)

    def get_app_version(self, app_name):
        cmd = f"rancher app ls {app_name} -o yaml"
        app_yaml = yaml.load(self.cli_execute(cmd))
        return app_yaml['Version']

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
            self.cli_execute(cmd)
            if wait:
                self.wait_for_app(app_name, timeout)
            # Due to Rancher bug when app shows it's active few seconds after deployment
            time.sleep(10)

    def delete_app(self, app_name):
        self.cli_execute(f"rancher app delete {app_name}")

    def app_exists(self, app_name):
        res = requests.get(f"{self.base_url}/v3/project/local:p-8n6zr/apps/p-8n6zr%3A{app_name}",
                           headers=self.auth_header,
                           verify=False)
        assert res.status_code == 200 or res.status_code == 404
        return res.status_code != 404


cluster_plugins.register("Rancher", Rancher)
