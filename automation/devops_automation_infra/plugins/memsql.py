import logging
from contextlib import closing
import pymysql
from pymysql import InternalError

from infra.model import plugins
from automation_infra.plugins.base_plugin import TunneledPlugin
from pytest_automation_infra import helpers
from pytest_automation_infra.helpers import hardware_config
from pymysql.constants import CLIENT
import copy


class Connection(object):
    def __init__(self, memsql_connection):
        self.connection = memsql_connection

    def fetchall(self, query):
        with closing(self.connection.cursor()) as c:
            c.execute(query)
            return c.fetchall()

    def execute(self, query):
        with closing(self.connection.cursor()) as c:
            c.execute(query)

    def truncate_all(self):
        logging.debug('Truncating all memsql dbs')
        truncate_commands = self.fetchall(
                f"""select concat('truncate table ', TABLE_SCHEMA, '.', TABLE_NAME) as truncate_command
                from information_schema.tables t
                where TABLE_SCHEMA not in ('information_schema', 'memsql')
                and TABLE_NAME not in ('DATABASECHANGELOG', 'DATABASECHANGELOGLOCK'); """)
        commands = ''.join([f"{command['truncate_command']};" for command in truncate_commands])
        self.execute(commands)
        logging.debug('Done Truncating all memsql dbs')

    @staticmethod
    def _reset_pipeline_cmd(pipline):
        return f"alter pipeline {pipline} set offsets earliest;"

    @staticmethod
    def _stop_pipeline_cmd(pipline):
        return f"stop pipeline {pipline};"

    @staticmethod
    def _start_pipeline_cmd(pipline):
        return f"start pipeline {pipline};"

    def reset_pipeline(self, pipeline_name):
        logging.debug(f'Reset pipeline {pipeline_name}')
        cmd = Connection._stop_pipeline_cmd(pipeline_name) + Connection._reset_pipeline_cmd(pipeline_name) + Connection._start_pipeline_cmd(pipeline_name)
        try:
            self.connection.query(cmd)
        except pymysql.err.InternalError as e:
            err_code = e.args[0]
            # This is pipeline already stopped error
            if err_code == 1939:
                cmd = Connection._reset_pipeline(pipeline_name) + Connection._start_pipeline_cmd(pipeline_name)
                self.connection.query(cmd)
        logging.debug(f'Done Reset pipeline {pipeline_name}')

    def close(self):
        self.connection.close()


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

    def _create_connection(self, **kwargs):
        password = "password" if not helpers.is_k8s(self._host.SshDirect) else self._host.SshDirect.execute("kubectl get secret --namespace default memsql-secret -o jsonpath='{.data.password}' | base64 --decode")
        memsql_kwargs = copy.copy(kwargs)
        memsql_kwargs.setdefault('password', password)
        memsql_kwargs.setdefault('user', 'root')
        return pymysql.connect(**memsql_kwargs,
                               cursorclass=pymysql.cursors.DictCursor,
                               client_flag=CLIENT.MULTI_STATEMENTS)

    def _get_connection(self):
        self.start_tunnel(self.DNS_NAME, self.PORT)
        return self._create_connection(host='localhost',
                                       port=self.local_bind_port)

    def tunneled_connection(self, database=None):
        tunnel = self._host.TunnelManager.get_or_create(self.DNS_NAME, self.DNS_NAME, self.PORT)
        connection = self._create_connection(host='localhost',
                                             port=tunnel._local_bind_port,
                                             database=database)
        return Connection(connection)

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
