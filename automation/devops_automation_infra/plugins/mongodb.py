from pymongo import MongoClient
import logging

from infra.model import plugins
from automation_infra.plugins.base_plugin import TunneledPlugin
from pytest_automation_infra.helpers import hardware_config


class Mongodb(object):
    def __init__(self, host):
        self._host = host
        self.DNS_NAME = 'mongodb.tls.ai'
        self.PORT = 27017

    def connection(self, dbname):
        return self._get_connection(dbname=dbname)

    @property
    def tunnel(self):
        tunnel = self._host.TunnelManager.get_or_create('mongodb', self.DNS_NAME, self.PORT)
        return tunnel

    def _get_connection(self, dbname):
        _tunnel = self.tunnel
        username = 'user' #TODO change it to the actual username which will be in K8s
        password = 'password' #TODO change it to the actual password which will be in K8s
        tunneled_host = _tunnel.host_port[0]
        tunneled_port = _tunnel.host_port[1]
        auth_source_db = 'admin'
        """
        currently works when putting cardentials on mongo in compose
        uri = f"mongodb://{username}:{password}@{tunneled_host}:{tunneled_port}/{dbname}?authSource={auth_source_db}"
        """
        uri = f"mongodb://{tunneled_host}:{tunneled_port}/{dbname}?authSource={auth_source_db}" #currently works due to no cradentials on mongo in compose
        connection = MongoClient(uri)
        return connection

    def ping(self, mongodb_conn):
        try:
            mongodb_conn.list_database_names()
        except Exception:
            raise Exception("failed to connect to mongodb")

    def verify_functionality(self):
        mongodb_conn = self.connection(dbname='admin')
        mongodb_dbs_list = mongodb_conn.list_database_names()
        assert len(mongodb_dbs_list) > 0
        logging.info("<<<<<<<MONGODB PLUGIN FUNCTIONING PROPERLY>>>>>>>>>>>>>")


plugins.register('Mongodb', Mongodb)


@hardware_config(hardware={"host": {}})
def test_basic(base_config):
    mongodb = base_config.hosts.host.Mongodb
    mongodb.verify_functionality()
