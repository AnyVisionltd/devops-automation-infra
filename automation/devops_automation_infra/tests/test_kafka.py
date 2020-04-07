import logging
import time
import random

from devops_automation_infra.plugins.kafka import Kafka
from pytest_automation_infra.helpers import hardware_config


def init_topic(automation_tests_topic, kafka):
    if automation_tests_topic in kafka.topic_names():
        kafka.delete_topic(automation_tests_topic)

    logging.info("creating topic")
    kafka.create_topic(automation_tests_topic)
    time.sleep(5)
    logging.info("done creating topic")
    assert automation_tests_topic in kafka.topic_names()


def init_consumer(automation_tests_topic, kafka):
    logging.info("subscribing..")
    kafka.subscribe(automation_tests_topic)
    logging.info    ("unsubscribing")
    kafka.unsubscribe()
    logging.info("done.")


def produce_messages(num_messages, topic, kafka):
    logging.info("producing messages:")
    for i in range(num_messages):
        kafka.put_message(topic, f'key{random.randint(0, 10)}', f"test {random.randint(10, 100)}")
    logging.info("done producing messages")


def deinit_topic(automation_tests_topic, kafka):
    logging.info("deleting topic")
    kafka.delete_topic(automation_tests_topic)
    assert 'anv.automation.topic1' not in kafka.topic_names()


@hardware_config(hardware={"host": {}})
def test_basic(base_config):
    kafka = base_config.hosts.host.Kafka
    automation_tests_topic = 'anv.automation.topic1'
    logging.info("getting topics")
    init_topic(automation_tests_topic, kafka)
    init_consumer(automation_tests_topic, kafka)

    num_messages = 10

    produce_messages(num_messages, automation_tests_topic, kafka)
    logging.info("testing consume_all:")
    consumed_messages = kafka.consume_all_messages(automation_tests_topic)
    logging.info(f"got {len(consumed_messages)} messages!")
    assert len(consumed_messages) == num_messages, "number of consumed messages != number of produced messages"
    logging.info(f"consume iter functioning properly {[msg.value() for msg in consumed_messages]}")

    produce_messages(num_messages, automation_tests_topic, kafka)
    logging.info("testing consume_x_messages:")
    consumed_messages = kafka.consume_x_messages(automation_tests_topic, num_messages/2)
    assert len(consumed_messages) == num_messages/2, "number of consumed messages != number of produced messages"
    logging.info(f"consume_x_messages functioning properly. messages: {[msg.value() for msg in consumed_messages]}")

    logging.info("testing kafka.empty:")
    kafka.empty(automation_tests_topic)
    logging.info("empty functioning properly.")

    deinit_topic(automation_tests_topic, kafka)

    logging.info(f"<<<<<<<<<<KAFKA PLUGIN FUNCTIONING PROPERLY>>>>>>>>>>")
