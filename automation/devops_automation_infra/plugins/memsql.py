import logging
from contextlib import closing
import pymysql
from pymysql import InternalError

from infra.model import plugins
from automation_infra.plugins.base_plugin import TunneledPlugin
from pytest_automation_infra import helpers
from pytest_automation_infra.helpers import hardware_config


class Memsql(TunneledPlugin):
    def __init__(self, host):
        super().__init__(host)
        self.DNS_NAME = 'memsql.tls.ai' if not helpers.is_k8s(self._host.SshDirect) else 'memsql.default.svc.cluster.local'
        self.PORT = 3306
        self._connection = None

    @property
    def connection(self):
        if self._connection is None:
            self._connection = self._get_connection()
        return self._connection

    @property
    def password(self):
        assert helpers.is_k8s(self._host.SshDirect)
        return self._host.SshDirect.execute(
            "kubectl get secret --namespace default memsql-secret -o jsonpath='{.data.password}' | base64 --decode")

    def _get_connection(self):
        self.start_tunnel(self.DNS_NAME, self.PORT)
        memsql_password = "password" if not helpers.is_k8s(self._host.SshDirect) else self._host.SshDirect.execute("kubectl get secret --namespace default memsql-secret -o jsonpath='{.data.password}' | base64 --decode")
        connection = pymysql.connect(host='localhost',
                                     port=self.local_bind_port,
                                     user='root',
                                     password=memsql_password,
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

    def truncate(self, schema):
        truncate_commands = self.fetch_all(
            f"""select concat('truncate table ', TABLE_SCHEMA, '.', TABLE_NAME) as truncate_command
            from information_schema.tables t 
            where TABLE_SCHEMA = '{schema}'
            and TABLE_NAME not in ('DATABASECHANGELOG', 'DATABASECHANGELOGLOCK'); """)
        for command_dict in truncate_commands:
            try:
                logging.debug(f"running command {command_dict['truncate_command']}")
                self.upsert(command_dict['truncate_command'])
            except InternalError as e:
                command_dict['truncate_command']
                logging.debug("failed to truncate table")

    def ping(self):
        try:
            return self.fetch_all("show databases")
        except:
            raise ConnectionError("Error connecting to Memsql db")

    def reset_state(self):
        query = "show databases"
        res = self.fetch_all(query)
        dbs = [db['Database'] for db in res]
        for db in dbs:
            if db != 'information_schema':
                self.truncate(db)

    def verify_functionality(self):
        dbs = self.fetch_all("show databases")
        logging.info("<<<<<<<MEMSQL PLUGIN FUNCTIONING PROPERLY>>>>>>>>>>>>.")


plugins.register('Memsql', Memsql)


@hardware_config(hardware={"host": {}})
def test_basic(base_config):
    memsql = base_config.hosts.host.Memsql
    memsql.verify_functionality()
