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


class Rancher(object):
    RANCHER_BASE_URL = "https://rancher.anv"

    def __init__(self, host):
        self._host = host

    def _generate_temp_token(self):
        payload = {"username": "admin", "password": "admin", "ttl": 60000}
        res = requests.post(url=f"https://rancher.anv/v3-public/localProviders/local?action=login",
                            data=json.dumps(payload),
                            verify=False)
        return res.json()['token']

    def _generate_permanent_token(self, token):
        payload = {"type": "token", "description": "automation"}
        headers = {"Authorization": f"Bearer {token}"}
        res = requests.post(url=f"https://rancher.anv/v3/token",
                            data=json.dumps(payload),
                            headers=headers,
                            verify=False)
        return res.json()['token']

    def login(self):
        temp_token = self._generate_temp_token()
        perma_token = self._generate_permanent_token(temp_token)
        cmd = f"sudo gravity exec rancher login {self.RANCHER_BASE_URL} --token {perma_token} --skip-verify"
        res = self._host.SshDirect.execute(cmd)
        # Check login was successful
        assert "Saving config to" in res

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
            # return False if ("deploying" or "installing") in self.app_list() else True
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


# @pytest.fixture(scope=determine_scope, autouse=True)
# def clean_up_core_p(base_config):
#     rancher = base_config.hosts.host1.Rancher
#     rancher.delete_app(app_name="core-app")
#     rancher.delete_app(app_name="core-init")
#     rancher.delete_app(app_name="core-data")

@hardware_config(hardware={"host1": {}})
def test(base_config):
    base_config.hosts.host1.Rancher.login()
    wait_for_predicate(lambda: base_config.hosts.host1.Rancher.install_app(app_name="core-data"),
                       timeout=300)
    wait_for_predicate(lambda: base_config.hosts.host1.Rancher.install_app(app_name="core-init"), timeout=30)
    wait_for_predicate(lambda: base_config.hosts.host1.Rancher.install_app(app_name="core-app"), timeout=120,
                       interval=10)
