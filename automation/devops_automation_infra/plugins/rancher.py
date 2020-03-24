import json
import logging
import time
import pytest

import requests

from automation_infra.utils.waiter import wait_for_predicate_nothrow, wait_for_predicate
from infra.model import plugins
from automation_infra.plugins.ssh_direct import SshDirect, SSHCalledProcessError
from pytest_automation_infra import helpers, determine_scope
from pytest_automation_infra.helpers import hardware_config


# TODO: Add docker register to rancher.
# TODO: Run in with sshtunnel
# TODO: Decide wether tokeep the current init

class Rancher(object):

    RANCHER_BASE_URL = "https://rancher.anv"

    def __init__(self, host):
        self._host = host
        self.auth_header = {"Authorization": f"Bearer {self.token()}"}
        # super().__init__(host)
        # with open('/etc/hosts', 'r+') as f:
        #     content = f.read()
        #     f.seek(0, 0)
        #     f.write(f'127.0.0.1    rancher.anv\n{content}')
        # self.DNS_NAME = 'rancher.anv'
        # self.PORT = 443
        # self.start_tunnel(self.DNS_NAME, self.PORT, force_same_port=True)

    # def tunneled_temp_token(self):
    #     payload = {"username": "admin", "password": "admin", "ttl": 60000}
    #     response = requests.post(url=f"rancher.anv:{self.local_bind_port}/v3-public/localProviders/local?action=login",
    #                              data=json.dumps(payload),
    #                              verify=False)
    #     return response.json()['token']


    def _generate_temp_token(self):
        payload = {"username": "admin", "password": "admin", "ttl": 60000}
        res = requests.post(url=f"https://rancher.anv/v3-public/localProviders/local?action=login",
                            data=json.dumps(payload),
                            verify=False)
        assert res.status_code == 201
        return res.json()['token']

    def project_details(self):
        res = requests.get("https://rancher.anv/v3/projects", headers=self.auth_header, verify=False)
        assert res.status_code == 200
        projects = res.json()['data']
        return [project for project in projects if project['name'] == 'Default'][0]

    def token(self):
        temp_token = self._generate_temp_token()
        payload = {"type": "token", "description": "automation"}
        headers = {"Authorization": f"Bearer {temp_token}"}
        res = requests.post(url=f"https://rancher.anv/v3/token",
                            data=json.dumps(payload),
                            headers=headers,
                            verify=False)
        assert  res.status_code == 201
        if not self.token:
            self.token = res.json()["token"]
        return res.json()['token']

    def cli_login(self):
        cmd = f"sudo gravity exec rancher login {self.RANCHER_BASE_URL} --token {self.token()} --skip-verify"
        res = self._host.SshDirect.execute(cmd)
        # Check login was successful
        assert "Saving config to" in res


    def delete_catalog(self, catalog_name):
        project_details = self.project_details()
        catalog_to_delete = "p-krs5d:anyvision"
        res = requests.delete(f"https://rancher.anv/v3/projectCatalogs/{catalog_to_delete}")



    def add_catalog(self,
                    url="https://chart.tls.ai/pipeline-core",
                    branch="master",
                    name="anyvision",
                    username="anyvision",
                    password="Any4Vision!"):
        project_details = self.project_details()
        project_id = project_details['id']
        data = {"type": "projectcatalog", "kind": "helm", "branch": branch, "projectId": project_id,
                "url": url, "name": name, "username": username,
                "password": password}
        res = requests.post("https://rancher.anv/v3/projectcatalog",
                            headers=self.auth_header,
                            data=json.dumps(data),
                            verify=False)
        # 409 is ok since it means the  catalog already exists
        assert res.status_code == 201 or res.status_code == 409


    def install_app(self,
                    app_name,
                    image_pull_policy="Always",
                    image_register_overwrite="",
                    docker_image_registry_overwrite="anyvision-training/"):
        cmd = "sudo gravity exec rancher app install " \
              f"--set=global.localRegistry={image_register_overwrite} " \
              f"--set=global.pullPolicy={image_pull_policy} " \
              f"--set=global.repository={docker_image_registry_overwrite} " \
              f"--version 2.2.0-master --namespace default {app_name} {app_name} --no-prompt"
        try:
            self._host.SshDirect.execute(cmd)
        # If the app already exists and if so return True
        except SSHCalledProcessError as e:
            if "already exists" in e.output:
                pass
        finally:
            return False if "deploying" in self.app_list() \
                            or "installing" in self.app_list() else True

    def app_list(self):
        cmd = f"sudo gravity exec rancher app ls"
        res = self._host.SshDirect.execute(cmd)
        return res

    def delete_app(self, app_name):
        cmd = f"sudo gravity exec rancher app delete {app_name}"
        try:
            self._host.SshDirect.execute(cmd)
        except SSHCalledProcessError as e:
            if "Not found" in e.output:
                pass
        return False if "removing" in self.app_list() else True


plugins.register('Rancher', Rancher)


@hardware_config(hardware={"host1": {}})
def test(base_config):
    # res = requests.get("https://rancher.anv/v3/catalogs", verify=False)

    base_config.hosts.host1.Rancher.cli_login()
    base_config.hosts.host1.Rancher.add_catalog()

    # wait_for_predicate(lambda: base_config.hosts.host1.Rancher.install_app(app_name="core-data"),
    #                    timeout=300)
    # wait_for_predicate(lambda: base_config.hosts.host1.Rancher.install_app(app_name="core-init"), timeout=30)
    # wait_for_predicate(lambda: base_config.hosts.host1.Rancher.install_app(app_name="core-app"), timeout=120,
    #                    interval=10)
