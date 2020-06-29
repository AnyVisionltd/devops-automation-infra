import json
import logging
import base64
import requests
import yaml
import time

from automation_infra.plugins.ssh_direct import SSHCalledProcessError
from pytest_automation_infra.helpers import hardware_config
from infra.model import plugins
from pytest_automation_infra import helpers


class Rancher(object):

    def __init__(self, host):
        self._host = host
        self.HOSTNAME = "rancher.anv"
        self.BASE_URL = f"https://{self.HOSTNAME}"
        self.auth_header = {"Authorization": f"Bearer {self.token}"}
        self.add_rancher_dns()
        
    @property
    def token(self):
        rancher_secret = json.loads(base64.b64decode(self._host.SshDirect.execute("sudo gravity exec kubectl get secrets -n kube-system rancher-cli-token  -o=jsonpath='{.data.cli2\.json}'")))
        rancher_token = rancher_secret["Servers"]["rancherDefault"]["tokenKey"]
        return rancher_token

    @property
    def default_project_id(self):
        return self.project_details()["id"]
    
    def add_rancher_dns(self):
        with open('/etc/hosts', 'r+') as f:
            content = f.read()
            f.seek(0, 0)
            f.write(f"{self._host.ip}     {self.HOSTNAME}\n{content}")

    def cli_login(self):
        cmd = f"sudo gravity exec rancher login {self.BASE_URL} --token {self.token} --skip-verify"
        res = self._host.SshDirect.execute(cmd)
        # Check login was successful
        assert "Saving config to" in res
    
    def refresh_catalog(self, catalog_name):
        self.clear_rancher_cache()
        self._host.SshDirect.execute(f"sudo gravity exec rancher catalog refresh --wait {catalog_name}")

    def project_details(self):
        res = requests.get(f"{self.BASE_URL}/v3/projects", headers=self.auth_header, verify=False)
        assert res.status_code == 200
        projects = res.json()['data']
        return [project for project in projects if project['name'] == 'Default'][0]
    
    def clear_rancher_cache(self):
        self._host.SshDirect.execute(f"kubectl get po -n cattle-system -l app=rancher | tail -n +2 | awk {{'print $1'}} | xargs -I pod_name kubectl exec -n cattle-system pod_name -- sh -c 'rm -rf management-state/catalog-cache/*'")

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
        self._host.SshDirect.execute(f"sudo gravity exec rancher wait {app_name} --timeout {timeout}")

    
    def upgrade_app(self, app_name, version, wait=True, timeout="120", **kwargs):
        cmd_options = ""
        for k, v in kwargs.items():
            cmd_options += f" --set {k}={v}"
            cmd_options += f" {app_name} {version}"
        cmd = f"sudo gravity exec rancher app upgrade {cmd_options}"
        self._host.SshDirect.execute(cmd)
        logging.debug(cmd)
        if wait:
            self.wait_for_app(app_name, timeout)

    def install_app(self, app_name, version, image_pull_policy="Always", docker_registry="", namespace="default", wait=True, timeout="120", force=True, **kwargs):
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
            cmd = f"sudo gravity exec {rancher_cmd} {cmd_options}"
            logging.debug(cmd)
            self._host.SshDirect.execute(cmd)
            if wait:
                self.wait_for_app(app_name, timeout)
        
    def delete_app(self, app_name):
        self._host.SshDirect.execute(f"sudo gravity exec rancher app delete {app_name}")

    def app_exists(self, app_name):
        res = requests.get(f"{self.BASE_URL}/v3/project/local:p-8n6zr/apps/p-8n6zr%3A{app_name}",
                        headers=self.auth_header,
                        verify=False)
        assert res.status_code == 200 or res.status_code == 404
        return res.status_code != 404


plugins.register("Rancher", Rancher)
