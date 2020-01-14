from kafka import Kafka


def test_kafka_consume_topic(base_config):
    messages = list()
    queue = ['anv.tracks.pipeng.new-tracks']
    for msg in base_config.host.Kafka.consume_iter(queue, timeout=5, commit=True):
        messages.append(msg)
    return messages
