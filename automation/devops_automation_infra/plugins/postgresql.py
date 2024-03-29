import logging
from contextlib import closing
import psycopg2
import psycopg2.extras

from infra.model import plugins
from pytest_automation_infra.helpers import hardware_config, is_k8s


class Postgresql(object):
    def __init__(self, host):
        self._host = host
        self.DNS_NAME = 'postgres.tls.ai' if not is_k8s(self._host.SshDirect) else 'postgres.default.svc.cluster.local'
        self.PORT = 5432
        self._connection = None

    @property
    def connection(self):
        if self._connection is None:
            self._connection = self._get_connection()
        return self._connection

    def _get_connection(self):
        tunnel = self._host.TunnelManager.get_or_create('postgres', self.DNS_NAME, self.PORT)
        connection = psycopg2.connect(host=tunnel.host_port[0],
                                     port=tunnel.host_port[1],
                                     user='anv_admin',
                                     password='password',
                                     database = 'anv_db')

        return connection

    def upsert(self, query):
        with closing(self.connection.cursor()) as cursor:
            cursor.execute(query)
            self.connection.commit()

    def fetch_all(self, query):
        with closing(self.connection.cursor(cursor_factory=psycopg2.extras.DictCursor)) as cursor:
            cursor.execute(query)
            res = cursor.fetchall()
        return res

    def fetch_one(self, query):
        with closing(self.connection.cursor(cursor_factory=psycopg2.extras.DictCursor)) as cursor:
            cursor.execute(query)
            res = cursor.fetchone()
        return res

    def fetch_count(self, query):
        with closing(self.connection.cursor(cursor_factory=psycopg2.extras.DictCursor)) as cursor:
            cursor.execute(query)
            res = cursor.fetchone()
        return res['count']

    def ping(self):
        dbs = self.fetch_all("select datname as db from pg_database")

    def reset_state(self):
        dbs = self.fetch_all("select datname as db from pg_database")
        # TODO: what needs to be truncated here exactly? I see the following dbs:
        #postgres  || anv_db    || template1 || template0 || kong

    def verify_functionality(self):
        # TODO: check flow logic here.
        dbs = self.fetch_all("select datname as db from pg_database")
        logging.info("<<<<<<<POSTGRES PLUGIN FUNCTIONING PROPERLY>>>>>>>>>>>>>")


plugins.register('Postgresql', Postgresql)


@hardware_config(hardware={"host": {}})
def test_basic(base_config):
    pg = base_config.hosts.host.Postgresql
    pg.verify_functionality()

