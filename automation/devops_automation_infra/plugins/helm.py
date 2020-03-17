import json
import logging

from automation_infra.plugins.ssh_direct import SSHCalledProcessError
from infra.model import plugins


class Helm(object):

    def __init__(self, host):
        self._host = host

    def add_repo(self, repo_name, repo_url):
        self.repo(f"add {repo_name} {repo_url}")
        self.repo_update()

    def list(self, options):
        return self._host.SshDirect.execute(f"sudo gravity exec helm list {options}")

    def apps_list(self):
        return json.loads(self._host.SshDirect.execute("sudo gravity exec helm list -q --output json"))

    def repo_update(self, flags=None):
        flags = flags or ""
        self.repo(f"update {flags}")

    def repo(self, command):
        return self._host.SshDirect.execute(f"sudo gravity exec helm repo {command}")

    def install(self, name, chart, flags=None):
        flags = flags or ""
        return self._host.SshDirect.execute(f"sudo gravity exec helm install --name {name} {chart} {flags}")

    def delete(self, name, flags=None):
        flags = flags or ""
        try:
            return self._host.SshDirect.execute(f"sudo gravity exec helm delete name {name} {flags}")
        except SSHCalledProcessError as e:
            # We don't want to fail in case their isn't anything to delete
            if "not found" in e.output:
                pass
            logging.error(e.output)




plugins.register("Helm", Helm)
