import rpyc
from rpyc.utils.server import ThreadedServer
from confluent_kafka import Consumer, Producer, TopicPartition
from confluent_kafka.admin import AdminClient, NewTopic, KafkaException


class KafkaServer(rpyc.Service):
    def __init__(self):
        self._kafka_config = None
        self._consumer = None
        self._producer = None

    def set_kafka_config(self, kafka_host, kafka_port, offset):
        self._kafka_config = {'bootstrap.servers': f'{kafka_host}:{kafka_port}',
                                   'group.id': "automation-group",
                                   'session.timeout.ms': 6000,
                                   'auto.offset.reset': offset}

    @property
    def Admin(self):
        if self._admin is None:
            self._admin = AdminClient(self._kafka_config)
        return self._admin

    @property
    def Consumer(self):
        if self._consumer is None:
            self._consumer = Consumer(self._kafka_config)
        return self._consumer

    @property
    def Producer(self):
        if self._producer is None:
            self._producer = Producer(self._kafka_config)
        return self._producer

    @staticmethod
    def create_list(*args):
        list_of_topics = list(args)
        return list_of_topics

    def create_topic_object(self, topic_name, num_partitions=3, replication_factor=1):
        topic = NewTopic(topic_name, num_partitions=num_partitions, replication_factor=replication_factor)
        return topic


if __name__ == "__main__":
    ThreadedServer(
        KafkaServer,
        port=18861,
        protocol_config={'allow_public_attrs': True}
    ).start()
