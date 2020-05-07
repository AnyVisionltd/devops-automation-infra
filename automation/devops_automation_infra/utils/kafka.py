import logging
import random
import time


def init_topic(automation_tests_topic, kafka):
    if automation_tests_topic in kafka.topic_names():
        kafka.delete_topics(automation_tests_topic)

    logging.debug("creating topic")
    kafka.create_topics(automation_tests_topic)
    time.sleep(5)
    logging.debug("done creating topic")
    assert automation_tests_topic in kafka.topic_names()


def init_consumer(automation_tests_topic, kafka):
    logging.debug("subscribing..")
    kafka.subscribe(automation_tests_topic)
    logging.debug("unsubscribing")
    kafka.unsubscribe()
    logging.debug("done.")


def produce_messages(num_messages, topic, kafka):
    logging.debug("producing messages:")
    for i in range(num_messages):
        kafka.put_message(topic, f'key{random.randint(0, 10)}', f"test {random.randint(10, 100)}")
    logging.debug("done producing messages")


def deinit_topic(automation_tests_topic, kafka):
    logging.debug("deleting topic")
    kafka.delete_topics(automation_tests_topic)
    assert 'anv.automation.topic1' not in kafka.topic_names()
