import logging
import random
import time


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
    logging.info("unsubscribing")
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
