import rpyc
from rpyc.utils.server import ThreadedServer
from confluent_kafka import Consumer, Producer, TopicPartition
from confluent_kafka.admin import AdminClient, NewTopic


class KafkaServer(rpyc.Service):
    def __init__(self):
        self._kafka_config = None
        self._consumer = None
        self._producer = None
        self._admin = None

    def set_kafka_config(self, kafka_host, kafka_port, offset):
        self._kafka_config = {'bootstrap.servers': f'{kafka_host}:{kafka_port}',
                                   'group.id': "automation-group",
                                   'session.timeout.ms': 6000,
                                   'auto.offset.reset': offset}

    @property
    def admin(self):
        if self._admin is None:
            self._admin = AdminClient(self._kafka_config)
        return self._admin

    @property
    def consumer(self):
        if self._consumer is None:
            self._consumer = Consumer(self._kafka_config)
        return self._consumer

    @property
    def producer(self):
        if self._producer is None:
            self._producer = Producer(self._kafka_config)
        return self._producer

    @staticmethod
    def create_list(*args):
        new_list = list(args)
        return new_list

    @staticmethod
    def create_topic_object(topic_name, num_partitions=3, replication_factor=1):
        new_topic = NewTopic(topic_name, num_partitions=num_partitions, replication_factor=replication_factor)
        return new_topic

    @staticmethod
    def create_topic_partition_object(topic, partition, offset):
        topic_partition = TopicPartition(topic=topic, partition=partition, offset=offset)
        return topic_partition


if __name__ == "__main__":
    ThreadedServer(
        KafkaServer,
        port=18861,
        protocol_config={'allow_public_attrs': True}
    ).start()
