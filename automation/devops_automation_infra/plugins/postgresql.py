from contextlib import closing
import psycopg2
import psycopg2.extras

from infra.model import plugins
from automation_infra.plugins.base_plugin import TunneledPlugin


class Postgresql(TunneledPlugin):
    def __init__(self,host):
        super().__init__(host)
        self.DNS_NAME = 'postgres.tls.ai'
        self.PORT = 5432
        self._connection = None

    @property
    def connection(self):
        if self._connection is None:
            self._connection = self._get_connection()
        return self._connection

    def _get_connection(self):
        self.start_tunnel(self.DNS_NAME, self.PORT)
        connection = psycopg2.connect(host='localhost',
                                     port=self.local_bind_port,
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

plugins.register('Postgresql', Postgresql)