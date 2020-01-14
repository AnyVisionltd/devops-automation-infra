from contextlib import closing
import pymysql

from infra.model import plugins
from base_plugin import TunneledPlugin
from pytest_automation_infra import helpers


class Memsql(TunneledPlugin):
    def __init__(self, host):
        super().__init__(host)
        self.DNS_NAME = 'memsql.tls.ai' if not helpers.is_k8s(self._host.SSH) else 'memsql.default.svc.cluster.local'
        self.PORT = 3306
        self._connection = None

    @property
    def connection(self):
        if self._connection is None:
            self._connection = self._get_connection()
        return self._connection

    def _get_connection(self):
        self.start_tunnel(self.DNS_NAME, self.PORT)
        connection = pymysql.connect(host='localhost',
                                     port=self.local_bind_port,
                                     user='root',
                                     password='password',
                                     cursorclass=pymysql.cursors.DictCursor)

        return connection

    def upsert(self, query):
        with closing(self.connection.cursor()) as cursor:
            res = cursor.execute(query)
        self.connection.commit()
        return res

    def fetch_all(self, query):
        with closing(self.connection.cursor(pymysql.cursors.DictCursor)) as cursor:
            cursor.execute(query)
            res = cursor.fetchall()
        return res

    def fetch_one(self, query):
        with closing(self.connection.cursor(pymysql.cursors.DictCursor)) as cursor:
            cursor.execute(query)
            res = cursor.fetchone()
        return res

    def fetch_count(self, query):
        with closing(self.connection.cursor(pymysql.cursors.DictCursor)) as cursor:
            cursor.execute(query)
            res = cursor.fetchone()
        return res['count']


plugins.register('Memsql', Memsql)
