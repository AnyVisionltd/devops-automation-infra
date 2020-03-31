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

automation_tests_topic = 'anv.automation.topic1'


class Kafka(TunneledPlugin):
    def __init__(self, host):
        super().__init__(host)
        self._host.SSH.put('rpyc-kafka-server.py', '/')
        self._host.SSH.execute('apt install -y python3-pip && pip3 install rpyc confluent_kafka')
        self._host.SSH.execute('nohup python3 -u /rpyc-kafka-server.py </dev/null >/dev/null 2>&1 & ')
        time.sleep(5)
        self._conn = rpyc.connect(host.ip, 18861, config={"allow_all_attrs": True})
        self.PORT = '9092'
        self.HOST = 'kafka-cluster-kafka-brokers.default.svc.cluster.local'
        self._kafka_admin = self._conn.root.init_kafka(self.HOST, self.PORT, offset='earliest')
        self._c = None
        self._p = None

    @property
    def consumer(self):
        if self._c is None:
            self._c = self._conn.root.init_consumer()
        return self._c

    @property
    def producer(self):
        if self._p is None:
            self._p = self._conn.root.init_producer()
        return self._p

    @property
    def admin(self):
        return self._kafka_admin

    def get_topics(self, timeout=10):
        return self.admin.list_topics(timeout=timeout).topics

    def topic_names(self):
        topics = self.get_topics()
        return [k for k, v in topics.items()]

    def get_message(self, topics, tries=3):
        self.consumer.subscribe(topics)
        for i in range(tries):
            msg = self.consumer.poll(timeout=1)
            if msg is not None:
                return msg
        return None

    def new_topic(self):
        topic = self._conn.root.create_topic_object('chen')
        topics = self._conn.root.create_list(topic)
        fs = self.admin.create_topics(topics)
        for topic, f in fs.items():
            try:
                f.result()
                logging.info("Topic {} created".format(topic))
                return True
            except Exception as e:
                logging.exception("Failed to create topic {}: {}".format(topic, e))
                raise

    def old_new_topics(self):
        topics = self._conn.root.kafka_new_topics('anv.automation.topic1')
        fs = self.admin.create_topics(topics)
        for topic, f in fs.items():
            try:
                f.result()  # The result itself is None
                logging.info("Topic {} created".format(topic))
                return True
            except Exception as e:
                logging.exception("Failed to create topic {}: {}".format(topic, e))
                raise


plugins.register('Kafka', Kafka)


@hardware_config(hardware={"host": {}})
def test_basic(base_config):
    kafka = base_config.hosts.host.Kafka
    kafka.old_new_topics()
    kafka.new_topic()

    # topics = kafka.get_topics()
    # msg = kafka.get_message(['anv.tracks.collate.new-tracks'])