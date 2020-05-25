import logging
import pika
from infra.model import plugins
from automation_infra.plugins.base_plugin import TunneledPlugin
from pytest_automation_infra.helpers import hardware_config


class RabbitMQ(TunneledPlugin):
    def __init__(self, host):
        super().__init__(host)
        self.DNS_NAME = 'rabbitmq.tls.ai'
        self.PORT = 5672
        self._connection = None

    @property
    def connection(self):
        if self._connection is None:
            self._connection = self._get_connection()
        return self._connection

    def _get_connection(self):
        try:
            self.start_tunnel(self.DNS_NAME, self.PORT)
            rmq_credentials = pika.PlainCredentials('user', 'password')
            connection = pika.BlockingConnection(pika.ConnectionParameters(host='localhost',
                                                                           port=self.local_bind_port,
                                                                           credentials=rmq_credentials))
            return connection
        except Exception as e:
            logging.error(f"there was an error while connecting to rabbitmq. {e}")

    def verify_functionality(self):
        queue_name = 'aut_test_rmq'
        rmq_channel = self.connection.channel()
        rmq_channel.queue_declare(queue=queue_name)
        rmq_channel.basic_publish(exchange='',
                                  routing_key=queue_name,
                                  body='Hello World')
        res = rmq_channel.basic_get(queue=queue_name, auto_ack=False)
        print(res)
        rmq_channel.queue_delete(queue=queue_name)
        logging.info("<<<<<<<RABBITMQ PLUGIN FUNCTIONING PROPERLY>>>>>>>>>>>>>")


plugins.register('RabbitMQ', RabbitMQ)


@hardware_config(hardware={"host": {}})
def test_basic(base_config):
    rmq = base_config.hosts.host.RabbitMQ
    rmq.verify_functionality()
