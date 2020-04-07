import time
import random
import logging
from datetime import datetime

import rpyc
from confluent_kafka.admin import KafkaException

from automation_infra.plugins.base_plugin import TunneledPlugin
from infra.model import plugins
from pytest_automation_infra import helpers
from pytest_automation_infra.helpers import hardware_config

TIMEOUT = 10


class Kafka(TunneledPlugin):
    def __init__(self, host):
        """IMPORTANT NOTE:
        Working with kafka can sometimes be delicate. The proper flow to consume:
        + create topic (if necessary)
        + init consumer (subscribe to topic AND POLL otherwise subscription does nothing)
        *** Only messages produced after subscribing and polling will be available to be consumed ***
        *** There is a subscribe helper function for your use ***
        + produce messages (if necessary)
        + consume messages - there are 3 helper functions: consumer_iter, consume_x_messages, consume_all_messages
        There is an example complete flow in test_kafka.py. Feel free to copy from there :)
        Be warned - if you dont use this order in your tests, there can be problems consuming.
        """
        super().__init__(host)
        self._execute_rpyc_server()
        self._conn = rpyc.connect(host.ip, 18861, config={'allow_all_attrs': True, 'sync_request_timeout': 120})
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
            logging.debug('put message successfully')

    def subscribe(self, topics):
        topics = topics if type(topics) == list else [topics]
        topics_l = self._conn.root.create_list(*topics)
        self.consumer.subscribe(topics_l)
        self.consumer.poll(timeout=5)
        time.sleep(5)

    def unsubscribe(self):
        self.consumer.unsubscribe()

    def _execute_rpyc_server(self):
        self._host.SSH.put('../devops-automation-infra/automation/devops_automation_infra/utils/rpyc-kafka-server.py',
                           '/')
        self._host.SSH.execute('nohup python3 -u /rpyc-kafka-server.py </dev/null >/dev/null 2>&1 &')
        time.sleep(5)

    def get_topics(self, timeout=TIMEOUT):
        return self.admin.list_topics(timeout=timeout).topics

    def topic_names(self):
        topics = self.get_topics()
        return [k for k, v in topics.items()]

    def create_topic(self, name):
        """ create topic if not exists """
        new_topic = self._conn.root.create_topic_object(name)
        topics = self._conn.root.create_list(new_topic)
        fs = self.admin.create_topics(topics, request_timeout=TIMEOUT, operation_timeout=TIMEOUT)
        for topic, f in fs.items():
            try:
                f.result()
                logging.info(f'Topic {name} created')
                return True
            except Exception as e:
                logging.exception(f'Failed to create topic {name}: {str(e)}')
                raise

    def delete_topic(self, topic):
        topics = self._conn.root.create_list(topic)
        fs = self.admin.delete_topics(topics, request_timeout=TIMEOUT, operation_timeout=TIMEOUT)
        for topic, f in fs.items():
            try:
                f.result()
                logging.info(f'Topic {topic} deleted')
                return True
            except Exception as e:
                logging.exception(f'Failed to delete topic {topic}: {str(e)}')

    def consume_x_messages(self, topics, num, timeout=TIMEOUT):
        list_of_msg = []
        for msg in self.consume_iter(topics, timeout=timeout):
            list_of_msg.append(msg)
            if len(list_of_msg) >= num:
                break

        return list_of_msg

    def consume_all_messages(self, topic, timeout=TIMEOUT):
        messages = list()
        logging.debug("starting to consume..")
        for msg in self.consume_iter(topic, timeout=timeout):
            logging.debug("received message!")
            messages.append(msg)
            logging.debug("appended message!")
        logging.info(f"got {len(messages)} messages!")
        return messages

    def consume_iter(self, topics, timeout=TIMEOUT, commit=False):
        """ Generator - use Kafka consumer for receiving messages from the given *topics* list.
            Yield a tuple of each message key and value.
            If got a *timeout* argument - break the loop if passed the value in seconds, but did not
            received messages since the last one was processed.
            If the optional argument *commit* is true, commit each message consumed."""
        topics = topics if type(topics) == list else [topics]
        logging.debug(f'Starting to consume topics {topics} (timeout: {timeout}).')
        topics = self._conn.root.create_list(*topics)
        logging.debug("subscribing")
        self.consumer.subscribe(topics)
        last_ts = datetime.now()
        try:
            while (timeout is None) or ((datetime.now() - last_ts).seconds < timeout):
                logging.debug("polling")
                msg = self.consumer.poll(timeout=timeout)
                logging.debug("polled!")
                if msg is None:
                    logging.debug("message is none :(")
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
            logging.exception(f'Error in consume_iter {str(e)}')
        finally:
            self.consumer.unsubscribe()
            logging.debug('Stopping to consume topics')

    def empty(self, topics, timeout=TIMEOUT):
        for msg in self.consume_iter(topics, timeout=timeout):
            logging.debug(f"discarding message: {msg.value()}")
        logging.debug(f"prilim: topic {topics} is now empty! Verifying...")

        time.sleep(3)

        for msg in self.consume_iter(topics, timeout=timeout):
            logging.debug(f"Received unexpected message: {msg.value()}")
            raise Exception("received message from topic which should be empty!")
        logging.info(f"topic {topics} is empty!")

    def put_message(self, topic, key, msg):
        self.producer.produce(topic=topic, key=key, value=msg, callback=self.delivery_report)
        self.producer.poll(0)


plugins.register('Kafka', Kafka)


@hardware_config(hardware={"host": {}})
def test_basic(base_config):
    automation_tests_topic = 'anv.automation.topic1'

    kafka = base_config.hosts.host.Kafka
    if automation_tests_topic in kafka.topic_names():
        kafka.delete_topic(automation_tests_topic)

    logging.info("creating topic")
    kafka.create_topic(automation_tests_topic)
    time.sleep(5)
    logging.info("done creating topic")
    assert automation_tests_topic in kafka.topic_names()
