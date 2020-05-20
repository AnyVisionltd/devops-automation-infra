import time
import logging
import rpyc

from automation_infra.utils import waiter
from pytest_automation_infra import helpers

from devops_automation_infra.utils import rpyc_kafka_server


class Kafka(object):

    def __init__(self, rpyc_connection):
        self.rpyc = rpyc_connection

    @staticmethod
    def parse_message(msg):
        key, value = msg.key.decode(), msg.value.decode()
        return key, value

    @staticmethod
    def delivery_report(err, msg):
        if err:
            raise Exception
        else:
            logging.debug('put message successfully')

    def _add_default_options(self, kwargs):
        options = {"bootstrap_servers": (f"kafka.tls.ai:9092")}
        options.update(kwargs)
        return options

    def get_admin(self, **kwargs):
        options = self._add_default_options(kwargs)
        return self.rpyc.root.get_admin(**options)

    def get_consumer(self, *topics, **kwargs):
        options = self._add_default_options(kwargs)
        return self.rpyc.root.get_consumer(*topics, **options)

    def get_producer(self, **kwargs):
        options = self._add_default_options(kwargs)
        return self.rpyc.root.get_producer(**options)

    def get_topics(self):
        return self.get_consumer().topics()

    def ping(self):
        topics = self.get_topics()
        return True

    def reset_state(self):
        if not helpers.is_k8s(self._host.SshDirect):
            self.delete_storage_compose()
        else:
            raise Exception("Infra doesnt know how to reset_state of kafka on K8s")

    def verify_functionality(self):
        logging.debug("verifying kafka functionality")
        automation_tests_topic = 'anv.automation.topic1'

        topics = self.get_topics()
        logging.debug(f"topics: {list(topics)}")

        admin = self.get_admin()
        logging.debug("delete topics")
        try:
            admin.delete_topics([automation_tests_topic])
        except Exception as e:
            if e.message == 'UNKNOWN_TOPIC_OR_PARTITION':
                pass

        logging.debug("create topic obj")
        rtopic_obj = self.rpyc.root.create_topic_object(automation_tests_topic)
        logging.debug("create topics")
        topics = self.get_topics()
        assert automation_tests_topic not in topics, f"topic should not exist but it does"
        waiter.wait_for_predicate_nothrow(lambda: admin.create_topics([rtopic_obj]))
        topics = self.get_topics()
        assert automation_tests_topic in topics, f"topic should exist but doesnt"

        logging.debug("get consumer")
        consumer = self.get_consumer(automation_tests_topic, auto_offset_reset='earliest',
                                     enable_auto_commit=False, consumer_timeout_ms=1000)

        logging.debug("get producer")
        producer = self.get_producer()
        num_produce_messages = 10
        logging.debug("produce 10")
        for i in range(num_produce_messages):
            producer.send(automation_tests_topic, b"this is a test %r" % i)
        logging.debug("done producing")
        time.sleep(1)

        consume_counter = 0
        logging.debug("consume 10")
        for message in consumer:
            logging.debug("consumed message: %s:%d:%d: key=%s value=%s" %
                          (message.topic, message.partition,
                           message.offset, message.key, message.value))
            consume_counter += 1
        logging.debug("delete topics")

        assert consume_counter == num_produce_messages, f"produced: {num_produce_messages}, consumed: {consume_counter}"

        admin.delete_topics([automation_tests_topic])
        logging.debug("end")
