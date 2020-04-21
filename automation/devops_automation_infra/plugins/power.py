from automation_infra.plugins.ssh_direct import SshDirect
from automation_infra.utils.waiter import wait_for_predicate
from devops_automation_infra.utils.health_check import host_is_active
from infra.model import plugins


class Power(object):

    def __init__(self, host):
        self._host = host

    def reboot(self, options=""):
        # Reboots the host and verifies using a ping
        host = self._host
        host.SshDirect.execute(f"sudo /sbin/reboot {options} > /dev/null 2>&1 &", timeout=0.1)
        wait_for_predicate(lambda: not host_is_active(host.ip), timeout=20)


plugins.register("Power", Power)
