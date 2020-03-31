import rpyc
from rpyc.utils.server import ThreadedServer
from confluent_kafka import Consumer, Producer, TopicPartition
from confluent_kafka.admin import AdminClient, NewTopic, KafkaException


class KafkaServer(rpyc.Service):
    def __init__(self):
        self._kafka_config = None

    def init_kafka(self, kafka_host, kafka_port, offset):
        if self._kafka_config is None:
            self._kafka_config = {'bootstrap.servers': f'{kafka_host}:{kafka_port}',
                                   'group.id': "automation-group",
                                   'session.timeout.ms': 6000,
                                   'auto.offset.reset': offset}
        kafka_admin = AdminClient(self._kafka_config)
        return kafka_admin

    def init_consumer(self):
        return Consumer(self._kafka_config)

    def init_producer(self):
        return Producer(self._kafka_config)

    def kafka_new_topics(self, topic_name, num_partitions=3, replication_factor=1):  # this is an exposed method
        topic = NewTopic(topic_name, num_partitions=num_partitions, replication_factor=replication_factor)
        return [topic, ]

    @staticmethod
    def create_list(*args):
        print(f'args {args} {type(args)}')
        list_of_topics = list(args)
        print(f'list of topics {list_of_topics} {type(list_of_topics)}')
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
