import json
import logging
import os
import time
from datetime import datetime
import yaml
import requests

from automation_infra.plugins.ssh_direct import SSHCalledProcessError
from automation_infra.utils import waiter
from infra.model import cluster_plugins
from devops_automation_infra.k8s_plugins.kubectl import Kubectl
from devops_automation_infra.k8s_plugins.gravity import Gravity
from devops_automation_infra.utils import kubectl as kubectl_utils


class Catalog:
    def __init__(self, catalog_url=None, catalog_user=None, catalog_password=None):
        self.catalog_url = catalog_url
        self.catalog_user = catalog_user
        self.catalog_password = catalog_password


class Helm:
    def __init__(self, cluster):
        self._cluster = cluster

    def cli_execute(self, cmd,timeout=1200):
        return self._execute(cmd,timeout)

    def _execute(self, cmd,timeout=None):
        ssh = self._cluster.K8SMaster().SshDirect
        try:
            ssh.execute("which helm")
        except SSHCalledProcessError:
            raise FileNotFoundError("Helm binary is missing on master")
        if timeout is not None:
            return ssh.execute(cmd, int(timeout))
        else:
            return ssh.execute(cmd)

    # def refresh_catalog(self, catalog_name):
    #     self.clear_cache()
    #     self.cli_execute(f"rancher catalog refresh --wait {catalog_name}")

    # def clear_cache(self):
    #     remove_cache_cmd = "rm -rf management-state/catalog-cache/*"
    #     rancher_pod_name = [pod for pod in kubectl_utils.get_pods_by_label(self._cluster.Kubectl.client(), namespace="cattle-system", label="app=rancher")
    #                         if pod.status.phase == "Running"][0].metadata.name
    #     return kubectl_utils.pod_exec(self._cluster.Kubectl.client(), namespace="cattle-system",
    #                                   name=rancher_pod_name, command=remove_cache_cmd)

    # def add_catalog(self, url, branch, name, username, password):
    #     data = {"type": "catalog", "kind": "helm", "branch": branch,
    #             "url": url, "name": name, "username": username,
    #             "password": password}
    #     res = requests.post(f"{self.base_url}/v3/catalog",
    #                         headers=self.auth_header,
    #                         data=json.dumps(data),
    #                         verify=False)
    #     # 409 is ok since it means the  catalog already exists
    #     assert res.status_code == 201 or res.status_code == 409
    #     self.refresh_catalog(name)

    # def delete_catalog(self, catalog_name):
    #     res = requests.post(f"{self.base_url}/v3/catalog/{catalog_name}",
    #                         headers=self.auth_header,
    #                         verify=False)
    #     assert res.status_code == 404

    # def wait_for_app(self, app_name, timeout):
    #     logging.info(f"Waiting for application to be available. see {self.base_url} for status")
    #     self.cli_execute(f"rancher wait {app_name} --timeout {timeout}",timeout)

    # def upgrade_app(self, app_name, version, wait=True, timeout="120", **kwargs):
    #     cmd_options = ""
    #     for k, v in kwargs.items():
    #         cmd_options += f" --set {k}={v}"
    #         cmd_options += f" {app_name} {version}"
    #     cmd = f"rancher app upgrade {cmd_options}"
    #     self.cli_execute(cmd)
    #     logging.debug(cmd)
    #     if wait:
    #         self.wait_for_app(app_name, timeout)

    def get_app_version(self, app_name):
        cmd = f"helm list --filter {app_name} -o yaml"
        app_yaml = yaml.load(self.cli_execute(cmd))
        chart_version = app_yaml['chart']
        chart_version.replace(f"{app_name}-", "")
        return chart_version

    def install_app(self, app_name, version, image_pull_policy="Always", docker_registry="", namespace="default", catalog=Catalog(),
                    wait=True, timeout="120", force=True, release_name=None,  **kwargs):
        if not release_name:
            release_name = app_name

        kwargs["global.localRegistry"] = docker_registry
        kwargs["global.pullPolicy"] = image_pull_policy
        cmd_options = ""
        if self.app_exists(app_name) and force:
            logging.info(f"{app_name} is Already exists, Running upgrade...")

        chart_url = f"{catalog.catalog_url}/charts/{app_name}-{version}.tgz"
        helm_cmd = f"helm upgrade --install {release_name} {chart_url}"

        if catalog.catalog_user and catalog.catalog_password:
            helm_cmd += f" --username {catalog.catalog_user} --password {catalog.catalog_password}"

        for k, v in kwargs.items():
            cmd_options += f" --set {k}={v}"
        cmd_options += f" --namespace {namespace} --atomic"
        cmd = f"{helm_cmd} {cmd_options}"

        if wait:
            cmd += f" --wait --timeout {timeout}s"

        logging.debug(cmd)
        self.cli_execute(cmd)

        # Due to Helm bug when app shows it's active few seconds after deployment
        time.sleep(15)

    def delete_app(self, app_name):
        # TODO: Check if rancher app delete waits until all resources are deleted
        self.cli_execute(f"helm delete {app_name}")

    def app_exists(self, app_name):
        try:
            self.cli_execute(f"helm status {app_name}")
        except Exception:
            return False
        return True

cluster_plugins.register("Helm", Helm)
