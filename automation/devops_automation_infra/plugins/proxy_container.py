import logging
import os
import subprocess

from automation_infra.utils import waiter
from infra.model import plugins

from automation_infra.plugins.ssh_direct import SshDirect, SSHCalledProcessError
from devops_automation_infra.plugins.docker import Docker


def _memoize(function):
    from functools import wraps
    memo = {}

    @wraps(function)
    def wrapper(*args):
        if args in memo:
            return memo[args]
        else:
            rv = function(*args)
            memo[args] = rv
            return rv

    return wrapper

class ProxyContainer(object):

    def __init__(self, host):
        self._host = host
        self._ssh_direct = self._host.SshDirect
        self.docker = self._host.Docker
        self._docker_bin_path = self.docker._docker_bin_path()

    @_memoize
    def _automation_proxy_version(self):
        version_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../../proxy_container/version.sh")
        return subprocess.check_output([version_file]).split()[0].decode()

    @property
    def running(self):
        return bool(self._ssh_direct.execute(f"{self._docker_bin_path} ps -aq --filter 'name=automation_proxy'"))

    def check_for_legacy_containers(self):
        ssh = self._ssh_direct
        container_names = ssh.execute("%s ps | awk '{print $NF}' | grep compose || true " % self._docker_bin_path).split()
        if not container_names:
            return
        common_prefix = os.path.commonprefix(container_names)
        if not common_prefix or common_prefix[-1] not in '_-':
            raise Exception(f"Found containers with different prefixes: {container_names}. "
                            f"Please prune accordingly and rerun test.")

    def run(self):
        self.check_for_legacy_containers()
        ssh_direct = self._ssh_direct
        removed = self.kill()

        self.docker.login()

        logging.debug("running docker")
        run_cmd = f'{self._docker_bin_path} run -d --rm ' \
                  f'--volume=/tmp/automation_infra/:/tmp/automation_infra ' \
                  f'--volume=/etc/hosts:/etc/hosts ' \
                  f'--volume=/var/log/journal:/var/log/journal ' \
                  f'--volume=/storage/logs:/storage/logs ' \
                  f'--privileged ' \
                  f'--network=host ' \
                  f'--name=automation_proxy gcr.io/anyvision-training/automation-proxy:{self._automation_proxy_version()}'
        assert not ssh_direct.execute(f"{self._docker_bin_path} ps -aq --filter 'name=automation_proxy'"), \
            "you want to run automation_proxy but it already exists, please remove it beforehand!"
        try:
            ssh_direct.execute(run_cmd)
        except SSHCalledProcessError as e:
            if "endpoint with name automation_proxy already exists in network host" in e.stderr:
                ssh_direct.execute(f"{self._docker_bin_path} network disconnect --force host automation_proxy")
                ssh_direct.execute(run_cmd)
            else:
                raise e
        logging.debug("docker is running")

    def kill(self):
        if not self.running:
            logging.debug("nothing to remove")
            return True
        logging.debug("trying to remove docker container")
        self._ssh_direct.execute(f"{self._docker_bin_path} kill automation_proxy")
        waiter.wait_for_predicate(lambda: not self.running)
        logging.debug("removed successfully!")
        return True

    def restart(self):
        self.kill()
        waiter.wait_for_predicate(lambda: not self.running)
        self.run()


plugins.register("ProxyContainer", ProxyContainer)
