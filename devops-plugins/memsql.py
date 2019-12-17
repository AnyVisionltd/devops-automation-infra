from contextlib import closing

from munch import Munch
import pymysql
import sshtunnel

from infra.model import plugins


class Memsql(object):
    HOST = 'memsql.tls.ai'
    PORT = '3306'

    def __init__(self, host):
        self.tunnel = sshtunnel.open_tunnel((host.ip, host.SSH.TUNNEL_PORT),
                                   ssh_username=host.user, ssh_password=host.password, ssh_pkey=host.keyfile,
                                   remote_bind_address=(self.HOST, self.PORT))
        self.tunnel.start()
        self._connection = None

    @property
    def connection(self):
        if self._connection is None:
            self._connection = self._get_connection()
        return self._connection

    def _get_connection(self):
        connection = pymysql.connect(host='localhost',
                                     port=self.tunnel.local_bind_port,
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

    def insert_suspect(self, sus_details):
        query = '''insert into suspects sus'''
        self.upsert(query)


plugins.register('Memsql', Memsql)
