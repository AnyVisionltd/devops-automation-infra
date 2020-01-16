from devops_automation_infra.plugins.kafka import Kafka
from pytest_automation_infra.helpers import hardware_config


@hardware_config(hardware={"host": {}})
def test_kafka_consume_topic(base_config):
    messages = list()
    queue = ['anv.tracks.pipeng.new-tracks']
    for msg in base_config.host.host.Kafka.consume_iter(queue, timeout=5, commit=True):
        messages.append(msg)
    return messages
