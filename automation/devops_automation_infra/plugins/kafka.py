import logging
import time
import rpyc

from automation_infra.plugins.base_plugin import TunneledPlugin
from infra.model import plugins
from datetime import datetime
import random

from confluent_kafka import Consumer, Producer, TopicPartition
from confluent_kafka.admin import AdminClient, NewTopic, KafkaException

from pytest_automation_infra import helpers
from pytest_automation_infra.helpers import hardware_config


class Kafka(TunneledPlugin):
    def __init__(self, host):
        super().__init__(host)
        self._host.SSH.put('rpyc-kafka-server.py', '/')
        self._host.SSH.execute('apt install -y python3-pip && pip3 install rpyc confluent_kafka')
        # self._host.SSH.execute('nohup python3 -u /rpyc-kafka-server.py </dev/null >/dev/null 2>&1 & ')
        # time.sleep(5)
        self._conn = rpyc.connect(host.ip, 18861, config={"allow_all_attrs": True})
        self.PORT = '9092'
        self.HOST = 'kafka-cluster-kafka-brokers.default.svc.cluster.local'
        self._kafka_admin = self._conn.root.set_kafka_config(self.HOST, self.PORT, offset='earliest')
        self._c = None
        self._p = None
        self._kafka_admin = None

    @property
    def consumer(self):
        if self._c is None:
            self._c = self._conn.root.Consumer
        return self._c

    @property
    def producer(self):
        if self._p is None:
            self._p = self._conn.root.Producer
        return self._p

    @property
    def admin(self):
        if self._kafka_admin is None:
            self._kafka_admin = self._conn.root.Admin
        return self._kafka_admin

    def get_topics(self, timeout=10):
        return self.admin.list_topics(timeout=timeout).topics

    def topic_names(self):
        topics = self.get_topics()
        return [k for k, v in topics.items()]

    def get_message(self, topic, tries=3):
        topics = self._conn.root.create_list(topic)
        self.consumer.subscribe(topics)
        for i in range(tries):
            msg = self.consumer.poll(timeout=1)
            if msg is not None:
                return msg
        return None

    def create_new_topic(self, name):
        topic = self._conn.root.create_topic_object(name)
        topics = self._conn.root.create_list(topic)
        self.admin.create_topics(topics, request_timeout=45, operation_timeout=45)


plugins.register('Kafka', Kafka)


@hardware_config(hardware={"host": {}})
def test_basic(base_config):
    kafka = base_config.hosts.host.Kafka
    kafka.create_new_topic('anv.automation.topic3')
    kafka.get_message('anv.tracks.collate.new-tracks')
