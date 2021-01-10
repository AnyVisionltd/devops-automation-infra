import logging

import pika
import requests

from infra.model import plugins
from pytest_automation_infra import helpers
from pytest_automation_infra.helpers import hardware_config


class Connection:
    def __init__(self, dns_name, port, virtual_host, credentials):
        self.connection = pika.BlockingConnection(
            pika.ConnectionParameters(host=dns_name, port=port, virtual_host=virtual_host, credentials=credentials,
                                      heartbeat=30))
        self.channel = self.connection.channel()

    def close(self):
        self.connection.close()

    def ping(self):
        return self.channel.is_open

    def verify_functionality(self):
        test_message = 'test message'
        self.channel.queue_declare(queue='test_queue', durable=True)
        self.produce_msg(exchange='', routing_key='test_queue', body=test_message)
        method_frame, header_frame, message = self.consume_message(queue='test_queue', auto_ack=True)
        assert test_message == message.decode('utf-8')
        self.channel.queue_delete(queue='test_queue')

    def produce_messages(self, messages_list):
        for message_dict in messages_list:
            self.produce_msg(**message_dict)

    def produce_msg(self, **kwargs):
        self.channel.basic_publish(**kwargs)

    def consume_message(self, **kwargs):
        return self.channel.basic_get(**kwargs)

    def consume_messages(self, **kwargs):
        return self.channel.basic_consume(**kwargs)

    def ack_message(self, delivery_tag):
        self.channel.basic_ack(delivery_tag=delivery_tag)


class Rabbitmq:
    def __init__(self, host):
        self._host = host
        self.DNS_NAME = 'rabbitmq.tls.ai' if not helpers.is_k8s(
            self._host.SshDirect) else 'rabbitmq-ha.default.svc.cluster.local'
        self.PORT = 5672  # amqp
        self.ADMIN_PORT = 15672  # admin
        self.password = "password" if not helpers.is_k8s(self._host.SshDirect) else self._host.SshDirect.execute(
            "kubectl get secret --namespace default rabbitmq-secret -o jsonpath='{.data.password}' | base64 --decode")
        self.user = 'user' if not helpers.is_k8s(self._host.SshDirect) else 'root'
        self.virtual_host = '/'
        self._amqp_tunnel = None
        self._admin_tunnel = None
        self._amqp_connection = None

    @property
    def amqp_tunnel(self):
        if self._amqp_tunnel is None:
            self._amqp_tunnel = self._host.TunnelManager.get_or_create("rmq", self.DNS_NAME, self.PORT)
        return self._amqp_tunnel

    @property
    def admin_tunnel(self):
        if self._admin_tunnel is None:
            self._admin_tunnel = self._host.TunnelManager.get_or_create("rmq-admin", self.DNS_NAME, self.ADMIN_PORT)
        return self._admin_tunnel

    def create_amqp_connection(self):
        credentials = pika.PlainCredentials(self.user, self.password)
        return Connection(*self.amqp_tunnel.host_port, self.virtual_host, credentials)

    def get_amqp_connection(self):
        if not self._amqp_connection:
            self._amqp_connection = self.create_amqp_connection()
        assert self._amqp_connection.ping()
        return self._amqp_connection

    def get_queue(self, queue_name):
        rmq_connection = self.get_amqp_connection()
        return rmq_connection.channel.queue_declare(queue=queue_name, passive=True)

    def get_queue_message_count(self, queue_name):
        queue = self.get_queue(queue_name)
        return queue.method.message_count

    def get_queue_list(self):
        url = f"http://{self.admin_tunnel.local_endpoint}/api/queues/{self.virtual_host if self.virtual_host != '/' else '%2F'}"
        response = requests.get(url, auth=(self.user, self.password))
        response.raise_for_status()
        queues = [q['name'] for q in response.json()]
        return queues

    def delete_queue(self, queue):
        url = f"http://{self.admin_tunnel.local_endpoint}/api/queues/{self.virtual_host if self.virtual_host != '/' else '%2F'}/{queue}"
        response = requests.delete(url, auth=(self.user, self.password))
        response.raise_for_status()
        logging.debug(f'Done remove queue {queue}')

    def reset_state(self):
        for queue in self.get_queue_list():
            self.delete_queue(queue)
        logging.debug('Done remove all queues')

    def get_vhost_node(self):
        url = f"http://{self.admin_tunnel.local_endpoint}/api/queues/{self.virtual_host if self.virtual_host != '/' else '%2F'}"
        response = requests.get(url, auth=(self.user, self.password))
        response.raise_for_status()
        return response.json()[0]['node']


plugins.register('Rabbitmq', Rabbitmq)


@hardware_config(hardware={"host": {}})
def test_basic(base_config):
    host = next(iter(base_config.hosts.values()))
    rmq = host.Rabbitmq
    rmq_connection = rmq.create_amqp_connection()
    rmq_connection.ping()
    rmq_connection.verify_functionality()
    rmq_connection.close()
