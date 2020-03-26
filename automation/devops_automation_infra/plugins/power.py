from automation_infra.plugins.ssh_direct import SshDirect
from automation_infra.utils.waiter import wait_for_predicate
from devops_automation_infra.utils.health_check import host_is_active
from infra.model import plugins


class Power(object):

    def __init__(self, host):
        self._host = host

    def reboot(self):
        # Reboots the bos and verify the reboot actually happened using a ping
        self._host.SshDirect.execute("sudo /sbin/reboot -f > /dev/null 2>&1 &", timeout=0.1)
        wait_for_predicate(lambda: not host_is_active(self._host.ip))


plugins.register("Power", Power)
