from pymongo import MongoClient

from infra.model import plugins
from pytest_automation_infra import helpers
from pytest_automation_infra.helpers import hardware_config
from automation_infra.plugins.tunnel_manager import TunnelManager


class Mongodb:
    def __init__(self, host):
        self._host = host
        self.DNS_NAME = 'mongodb.tls.ai' if not helpers.is_k8s(
            self._host.SshDirect) else 'mongodb.default.svc.cluster.local'
        self.PORT = 27017

    @property
    def client(self):
        return self._get_client()

    @property
    def tunnel(self):
        tunnel = self._host.TunnelManager.get_or_create('mongodb', self.DNS_NAME, self.PORT)
        return tunnel

    def _get_client(self, credentials=None):
        uri = f"mongodb://{self.tunnel.local_endpoint}" if not credentials else \
            f"mongodb://{credentials['username']}:{credentials['password']}@{self.tunnel.local_endpoint}"
        client = MongoClient(uri)
        return client

    @staticmethod
    def ping(mongodb_conn):
        try:
            mongodb_dbs_list = mongodb_conn.list_database_names()
            assert len(mongodb_dbs_list) > 0
        except Exception:
            raise Exception("failed to connect to mongodb")

    def verify_functionality(self):
        mongodb_conn = self.client
        self.ping(mongodb_conn=mongodb_conn)


plugins.register('Mongodb', Mongodb)


@hardware_config(hardware={"host": {}})
def test_basic(base_config):
    host = next(iter(base_config.hosts.values()))
    mongodb = host.Mongodb
    mongodb.verify_functionality()
