from infra.model.host import Host
from infra.model import plugins
from automation_infra.plugins import connection
from automation_infra.plugins.ssh_direct import SshDirect


class SSH(SshDirect):
    def connect(self, port=2222, timeout=10, user="root", password="root"):
        # TODO: have handle security here
        host = Host.from_args(self._host.ip, user, password, port=port, alias=self._host.alias)
        self._connection = connection.Connection(host)
        self._connection.connect(timeout)

    @property
    def _using_keyfile(self):
        return False


plugins.register("SSH", SSH)
