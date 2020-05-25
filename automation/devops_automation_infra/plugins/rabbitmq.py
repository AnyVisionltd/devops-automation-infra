import logging
import pika
from infra.model import plugins
from automation_infra.plugins.base_plugin import TunneledPlugin
from pytest_automation_infra.helpers import hardware_config


class RabbitMQ(object):
    def __init__(self, host):
        self._host = host
        self.DNS_NAME = 'rabbitmq.tls.ai'
        self.PORT = 5672

    @property
    def connection(self):
        return self._get_connection()

    @property
    def tunnel(self):
        return self._host.TunnelManager.get_or_create('consul', self.DNS_NAME, self.PORT)

    def _get_connection(self):
        try:
            _tunnel = self.tunnel
            _tunneled_host = _tunnel.host_port[0]
            _tunneled_port = _tunnel.host_port[1]
            rmq_credentials = pika.PlainCredentials('user', 'password')
            connection = pika.BlockingConnection(pika.ConnectionParameters(host=_tunneled_host,
                                                                           port=_tunneled_port,
                                                                           credentials=rmq_credentials))
            return connection
        except Exception as e:
            logging.error(f"there was an error while connecting to rabbitmq. {e}")

    def verify_functionality(self):
        queue_name = 'aut_test_rmq'
        rmq_conn = self.connection
        rmq_channel = rmq_conn.channel()
        rmq_channel.queue_declare(queue=queue_name)
        rmq_channel.basic_publish(exchange='',
                                  routing_key=queue_name,
                                  body='Hello World')
        res = rmq_channel.basic_get(queue=queue_name, auto_ack=False)
        assert res[2] == b'Hello World'
        rmq_channel.queue_delete(queue=queue_name)
        logging.info("<<<<<<<RABBITMQ PLUGIN FUNCTIONING PROPERLY>>>>>>>>>>>>>")


plugins.register('RabbitMQ', RabbitMQ)


@hardware_config(hardware={"host": {}})
def test_basic(base_config):
    rmq = base_config.hosts.host.RabbitMQ
    rmq.verify_functionality()
