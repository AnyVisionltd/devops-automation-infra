import logging
import time
from datetime import datetime

import rpyc
from confluent_kafka.admin import KafkaException

from automation_infra.plugins.base_plugin import TunneledPlugin
from infra.model import plugins
from pytest_automation_infra import helpers
from pytest_automation_infra.helpers import hardware_config


class Kafka(TunneledPlugin):
    def __init__(self, host):
        super().__init__(host)
        self._host.SSH.put('/home/user/infra/devops-automation-infra/automation/devops_automation_infra/plugins/rpyc-kafka-server.py', '/')
        self._host.SSH.execute('apt install -y python3-pip && pip3 install rpyc confluent_kafka')
        self._host.SSH.execute('nohup python3 -u /rpyc-kafka-server.py </dev/null >/dev/null 2>&1 & ')
        time.sleep(5)
        self._conn = rpyc.connect(host.ip, 18861, config={"allow_all_attrs": True})
        self.PORT = '9092'
        self.DNS_NAME = 'kafka.tls.ai' if not helpers.is_k8s(self._host.SshDirect) \
            else 'kafka-cluster-kafka-brokers.default.svc.cluster.local'
        self._kafka_admin = self._conn.root.set_kafka_config(self.DNS_NAME, self.PORT, offset='latest')
        self._c = None
        self._p = None
        self._kafka_admin = None

    @property
    def consumer(self):
        if self._c is None:
            self._c = self._conn.root.consumer
        return self._c

    @property
    def producer(self):
        if self._p is None:
            self._p = self._conn.root.producer
        return self._p

    @property
    def admin(self):
        if self._kafka_admin is None:
            self._kafka_admin = self._conn.root.admin
        return self._kafka_admin

    @staticmethod
    def parse_message(msg):
        key, value = msg.key().decode(), msg.value().decode()
        return key, value

    @staticmethod
    def delivery_report(err, msg):
        if err:
            raise Exception
        else:
            logging.info(f"message {msg} put successfully")

    def get_topics(self, timeout=10):
        return self.admin.list_topics(timeout=timeout).topics

    def topic_names(self):
        topics = self.get_topics()
        return [k for k, v in topics.items()]

    def get_message(self, topics, tries=3):
        topics = self._conn.root.create_list(*topics)
        self.consumer.subscribe(topics)
        for i in range(tries):
            msg = self.consumer.poll(timeout=1)
            if msg is not None:
                self.consumer.unsubscribe()
                return msg
        self.consumer.unsubscribe()
        return None

    def create_topic(self, name):
        """ create topic if not exists """
        new_topic = self._conn.root.create_topic_object(name)
        topics = self._conn.root.create_list(new_topic)
        fs = self.admin.create_topics(topics, request_timeout=30, operation_timeout=30)
        for topic, f in fs.items():
            try:
                f.result()
                logging.info("Topic {} created".format(topic))
                return True
            except Exception as e:
                logging.exception("Failed to create topic {}: {}".format(topic, e))
                raise

    def delete_topic(self, topic):
        topics = self._conn.root.create_list(topic)
        fs = self.admin.delete_topics(topics, request_timeout=30, operation_timeout=30)
        for topic, f in fs.items():
            try:
                f.result()
                logging.info("Topic {} deleted".format(topic))
                return True
            except Exception as e:
                logging.exception("Failed to delete topic {}: {}".format(topic, e))

    def consume_messages_x_times(self, topics, times):
        topics = self._conn.root.create_list(*topics)
        self.consumer.subscribe(topics)
        list_of_msg = []
        for i in range(times):
            msg = self.consumer.poll(timeout=1)
            if msg is not None:
                list_of_msg.append(msg)
        self.consumer.unsubscribe()
        return list_of_msg

    def consume_iter(self, topics, timeout=None, commit=False):
        """ Generator - use Kafka consumer for receiving messages from the given *topics* list.
            Yield a tuple of each message key and value.
            If got a *timeout* argument - break the loop if passed the value in seconds, but did not
            received messages since the last one was processed.
            If the optional argument *commit* is true, commit each message consumed."""

        logging.info(f'Starting to consume message (timeout: {timeout}).')
        topics = self._conn.root.create_list(*topics)
        self.consumer.subscribe(topics)
        last_ts = datetime.now()
        try:
            while (timeout is None) or ((datetime.now() - last_ts).seconds < timeout):
                msg = self.consumer.poll(timeout=1)
                if msg is None:
                    continue
                last_ts = datetime.now()
                if msg.error():
                    raise KafkaException(msg.error())
                else:
                    yield msg
                if commit is True and msg is not None:
                    offset = msg.offset()
                    if offset < 0:
                        offset = 0
                    tpo = self._conn.root.create_topic_partition_object(topic=msg.topic(), partition=msg.partition(),
                                                                        offset=offset)
                    tpos = self._conn.root.create_list(tpo)
                    self.consumer.commit(offsets=tpos, asynchronous=True)

        except Exception as e:
            logging.exception(f"Error in consume_iter {e.__str__()}")
        finally:
            self.consumer.unsubscribe()
            logging.info(f"Stopping to consume topics {topics}")

    def empty(self, topics, timeout=10):
        for msg in self.consume_iter(topics, timeout=timeout, commit=True):
            logging.debug(f"emptying message {msg}")
        time.sleep(5)
        assert self.get_message(topics) is None

    def put_message(self, topic, key, msg):
        self.producer.produce(topic=topic, key=key, value=msg, callback=self.delivery_report)
        self.producer.poll(0)


plugins.register('Kafka', Kafka)


@hardware_config(hardware={"host": {}})
def test_basic(base_config):
    kafka = base_config.hosts.host.Kafka
    kafka.delete_topic('anv.automation.topic2')
    kafka.create_topic('anv.automation.topic2')
    logging.error(f"{kafka.get_message(['anv.tracks.collate.new-tracks', 'anv.tracks.pipeng.new-tracks'])}")
    kafka.consume_messages_x_times(['anv.tracks.collate.new-tracks', 'anv.tracks.pipeng.new-tracks'], 400)
