import logging

from pytest_automation_infra.helpers import hardware_config
from automation_infra.utils import waiter
from automation_infra.utils import concurrently

from devops_automation_infra.plugins.kafka import Kafka


@hardware_config(hardware={"host": {}})
def test_kafka(base_config):
    logging.info("testing original kafka")
    kafka = base_config.hosts.host.Kafka
    logging.info("Ensure kafka is up")
    kafka.start()
    waiter.wait_for_predicate_nothrow(lambda: kafka.ping(), timeout=60)
    client = kafka.create_client()
    logging.info("Verify functionality")
    client.verify_functionality()
    logging.info("Stop and clean kafka")
    kafka.stop()
    kafka.reset_state()
    kafka.start()
    logging.info("Waiting kafka alive")
    waiter.wait_for_predicate_nothrow(lambda: kafka.ping(), timeout=60)
    logging.info("Verify functionality again")
    client = kafka.create_client()
    client.verify_functionality()
    logging.info("restart kafka")
    kafka.restart()
    logging.info("Waiting kafka alive")
    waiter.wait_for_predicate_nothrow(lambda: kafka.ping(), timeout=60)
    logging.info("Verify functionality again")
    client = kafka.create_client()
    client.verify_functionality()
    logging.info("original kafka functioning properly")


@hardware_config(hardware={"host": {}})
def test_kafka_multithreaded_usage(base_config):
    def _kafka_minitest():
        kafka = base_config.hosts.host.Kafka
        client = kafka.create_client()
        client.get_topics()
    concurrently.run({f"{i}" : _kafka_minitest for i in range(3)})