import logging
import rpyc

from automation_infra.utils import waiter
from infra.model import plugins
from pytest_automation_infra import helpers

from devops_automation_infra.utils import rpyc_kafka_server
from devops_automation_infra.utils import kafka_client
from devops_automation_infra.utils import container
import threading

class Kafka(object):
    RPYC_PORT = 18861

    def __init__(self, host):
        self._host = host
        self.DNS = 'kafka.tls.ai' if not helpers.is_k8s(self._host.SshDirect) \
                else 'kafka-cluster-kafka-brokers.default.svc.cluster.local'
        self.PORT = '9092'
        self._rpyc = None
        self._init_lock = threading.Lock()

    def _start_server(self):
        with self._init_lock:
            if self._rpyc is not None:
                return self._rpyc
            logging.info(f"starting kafka rpyc server on {self._host.ip}")
            self._rpyc = self._host.SSH.run_background_snippet(rpyc_kafka_server.run_kafka_rpyc_server)
        try:
            waiter.wait_for_predicate_nothrow(lambda: self._rpyc.running(), timeout=5)
            logging.info(f"kafka rpyc server is running: {self._rpyc.running()}")
            waiter.await_changing_result(lambda: self._rpyc.running(), interval=0.1)
            assert self._rpyc.running(), "kafka rpyc server is no longer running."
        except (TimeoutError, AssertionError):
            self.log_kafka_rpyc_server_errors()
            raise

    def _create_connection(self):
        tunnel = self._host.TunnelManager.get_or_create('kafka', "127.0.0.1", Kafka.RPYC_PORT)
        return waiter.wait_for_predicate_nothrow(
            lambda: rpyc.connect(*tunnel.host_port, config={'allow_all_attrs': True, 'sync_request_timeout': 120}),
            timeout=10)

    def create_client(self):
        self._start_server()
        logging.info(f"rpyc server still running: {self._rpyc.running()}")
        return kafka_client.Kafka(self._create_connection())

    def ping(self):
        try:
            client = self.create_client()
            logging.info(f"created client successfully. still running: {self._rpyc.running()}")
            return client.ping()
        except:
            self.log_kafka_rpyc_server_errors()
            raise

    def reset_state(self):
        if not helpers.is_k8s(self._host.SshDirect):
            self.delete_storage_compose()
        else:
            raise Exception("Infra doesnt know how to reset_state of kafka on K8s")

    def restart(self):
        container.restart_container_by_service(self._host, "kafka")

    def stop(self):
        container.stop_container_by_service(self._host, "kafka")

    def start(self):
        container.start_container_by_service(self._host, "kafka")

    def delete_storage_compose(self):
        self._host.SshDirect.execute('sudo rm -rf /storage/kafka/*')

    def log_kafka_rpyc_server_errors(self):
        logging.error("had problem with kafka rpyc server")
        logging.info(f"infra thinks that background rpyc server is running: {self._rpyc.running()}")
        logging.info(f"return code: {self._rpyc.returncode}")
        logging.info(f"output: {self._rpyc.output}")
        logging.info(f"stderr: {self._rpyc.error}")

        logging.info(f"docker ps | grep kafka: %s",
                     self._host.SshDirect.execute('docker ps | grep kafka || [[ $? == 1 ]]').split('\n'))

        logging.info("python3 processes (no grep): %s", self._host.SSH.execute('ps -ef | grep python3 | grep -v grep || [[ $? == 1 ]]').split('\n'))
        logging.info("all python3 processes (just to be sure): %s", self._host.SSH.execute('ps -ef | grep python3 ').split('\n'))


plugins.register('Kafka', Kafka)

