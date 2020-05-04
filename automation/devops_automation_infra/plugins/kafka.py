import time
import random
import logging
from datetime import datetime

import rpyc
from confluent_kafka.admin import KafkaException

from automation_infra.plugins.base_plugin import TunneledPlugin
from automation_infra.utils import waiter
from automation_infra.utils.timer import timeitdecorator
from infra.model import plugins
from pytest_automation_infra import helpers
from pytest_automation_infra.helpers import hardware_config
from devops_automation_infra.utils import kafka as kafka_util

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
        self._host.SSH.execute('nohup python3 -u /rpyc-kafka-server.py > rpyc.log &')
        time.sleep(5)

    def get_topics(self, timeout=TIMEOUT):
        return self.admin.list_topics(timeout=timeout).topics

    @timeitdecorator
    def topic_names(self):
        return self._conn.root.topic_names()

    @timeitdecorator
    def num_topics(self):
        return self._conn.root.num_topics()

    @timeitdecorator
    def create_topics(self, *topic_names):
        remote_topics = self._conn.root.create_list(*topic_names)
        result = self._conn.root.create_topics(*remote_topics)
        if not result == True:
            raise Exception(str(result))
        waiter.await_changing_result(self.num_topics)

    @timeitdecorator
    def delete_topics(self, *topic_names):
        remote_topics = self._conn.root.create_list(*topic_names)
        result = self._conn.root.delete_topics(remote_topics)
        if not result == True:
            raise Exception(str(result))
        # give time for topics to be actually deleted
        waiter.await_changing_result(self.num_topics)

    @timeitdecorator
    def delete_all_topics(self):
        topic_names = self.topic_names()
        if not topic_names:
            return
        self.delete_topics(*topic_names)
        # __consumer_groups topic is created automatically
        assert self.num_topics() <= 1

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

    def verify_functionality(self):
        automation_tests_topic = 'anv.automation.topic1'
        logging.info("getting topics")
        kafka_util.init_topic(automation_tests_topic, self)
        kafka_util.init_consumer(automation_tests_topic, self)

        num_messages = 10

        kafka_util.produce_messages(num_messages, automation_tests_topic, self)
        logging.info("testing consume_all:")
        consumed_messages = self.consume_all_messages(automation_tests_topic)
        logging.info(f"got {len(consumed_messages)} messages!")
        assert len(consumed_messages) == num_messages, "number of consumed messages != number of produced messages"
        logging.info(f"consume iter functioning properly {[msg.value() for msg in consumed_messages]}")

        kafka_util.deinit_topic(automation_tests_topic, self)

        logging.info(f"<<<<<<<<<<KAFKA PLUGIN FUNCTIONING PROPERLY>>>>>>>>>>")

    def verify_functionality_full(self):
        automation_tests_topic = 'anv.automation.topic1'
        logging.info("getting topics")
        kafka_util.init_topic(automation_tests_topic, self)
        kafka_util.init_consumer(automation_tests_topic, self)

        num_messages = 10

        kafka_util.produce_messages(num_messages, automation_tests_topic, self)
        logging.info("testing consume_all:")
        consumed_messages = self.consume_all_messages(automation_tests_topic)
        logging.info(f"got {len(consumed_messages)} messages!")
        assert len(consumed_messages) == num_messages, "number of consumed messages != number of produced messages"
        logging.info(f"consume iter functioning properly {[msg.value() for msg in consumed_messages]}")

        kafka_util.produce_messages(num_messages, automation_tests_topic, self)
        logging.info("testing consume_x_messages:")
        consumed_messages = self.consume_x_messages(automation_tests_topic, num_messages / 2)
        assert len(consumed_messages) == num_messages / 2, "number of consumed messages != number of produced messages"
        logging.info(f"consume_x_messages functioning properly. messages: {[msg.value() for msg in consumed_messages]}")

        logging.info("testing kafka.empty:")
        self.empty(automation_tests_topic)
        logging.info("empty functioning properly.")

        kafka_util.deinit_topic(automation_tests_topic, self)

        logging.info(f"<<<<<<<<<<KAFKA PLUGIN FUNCTIONING PROPERLY>>>>>>>>>>")

    def ping(self):
        self.get_topics()

    def reset_state(self):
        self.delete_all_topics()


plugins.register('Kafka', Kafka)


@hardware_config(hardware={"host": {}})
def test_basic(base_config):
    kafka = base_config.hosts.host.Kafka
    kafka.verify_functionality_full()
