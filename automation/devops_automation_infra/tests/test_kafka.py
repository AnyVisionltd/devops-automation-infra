import logging

from devops_automation_infra.plugins.kafka import Kafka
from pytest_automation_infra.helpers import hardware_config


@hardware_config(hardware={"host": {}})
def test_tunneled_kafka(base_config):
    kafka = base_config.hosts.host.Kafka
    topics = kafka.get_topics()
    logging.info(f"topics: {topics}")
    kafka.create_topic("aaaOri")
    topics_to_empty = ['anv.tracks.collate.new-tracks', 'anv.tracks.tracks-consumer-producer.new-tracks']
    msg = kafka.get_message(topics_to_empty)
    logging.error(f'msg: {msg}')
    kafka.empty(topics_to_empty, 10)
    kafka.delete_topic("aaaOri")
