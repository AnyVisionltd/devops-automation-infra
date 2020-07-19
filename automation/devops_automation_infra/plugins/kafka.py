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
            logging.debug(f"starting kafka rpyc server on {self._host.ip}")
            self._rpyc = self._host.SSH.run_background_snippet(rpyc_kafka_server.run_kafka_rpyc_server)
        try:
            waiter.wait_for_predicate_nothrow(lambda: self._rpyc.running(), timeout=5)
        except TimeoutError:
            self.log_debug_info()
            raise


    def _create_connection(self):
        tunnel = self._host.TunnelManager.get_or_create('kafka', self._host.ip, Kafka.RPYC_PORT)
        return waiter.wait_for_predicate_nothrow(
            lambda: rpyc.connect(*tunnel.host_port, config={'allow_all_attrs': True, 'sync_request_timeout': 120}),
            timeout=10)

    def create_client(self):
        self._start_server()
        return kafka_client.Kafka(self._create_connection())

    def ping(self):
        try:
            return self.create_client().ping()
        except:
            self.log_debug_info()
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

    def log_debug_info(self):
        logging.exception("caught exception trying to ping kafka plugin")
        logging.info(f"docker ps | grep kafka: {self._host.SshDirect.execute('docker ps | grep kafka')}")
        logging.info(f"(this should show a python3 snippet process running)ps -ef | grep python3 | grep -v grep: "
                     f"{self._host.SSH.execute('ps -ef | grep python3 | grep -v grep')}")

        logging.info(f"""rpyc server logs 0: {self._host.SSH.execute("ps -ef | grep python3 | grep -v grep | "
                                                                           "awk '{print $2}' | xargs -I{} cat /proc/{}/fd/0")}""")
        logging.info(f"""rpyc server logs 1: {self._host.SSH.execute("ps -ef | grep python3 | grep -v grep | "
                                                                           "awk '{print $2}' | xargs -I{} cat /proc/{}/fd/1")}""")
        logging.info(f"""rpyc server logs 2: {self._host.SSH.execute("ps -ef | grep python3 | grep -v grep | "
                                                                           "awk '{print $2}' | xargs -I{} cat /proc/{}/fd/2")}""")

        logging.info(f"kafka_ container logs: ")
        logging.info(self._host.Docker.get_container_logs('kafka_', '5m'))


plugins.register('Kafka', Kafka)

