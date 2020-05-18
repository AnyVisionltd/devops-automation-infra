import kafka
import rpyc
from rpyc.utils.server import ThreadedServer
import logging

class KafkaServer(rpyc.Service):
    @staticmethod
    def get_admin(**kwargs):
        logging.error("getting admin")
        return kafka.KafkaAdminClient(**kwargs)

    @staticmethod
    def get_producer(**kwargs):
        """to produce: producer.send(topic, message_bytes)"""
        logging.error("getting admin")
        return kafka.KafkaProducer(**kwargs)

    @staticmethod
    def get_consumer(*topics, **kwargs):
        """to consume:
        for message in consumer:
            message value and key are raw bytes -- decode if necessary!
            e.g., for unicode: `message.value.decode('utf-8')`
            print ("%s:%d:%d: key=%s value=%s" % (message.topic, message.partition,
                                                  message.offset, message.key,
                                                  message.value))
        """
        return kafka.KafkaConsumer(*topics, **kwargs)

    @staticmethod
    def create_list(*args):
        new_list = list(args)
        return new_list

    @staticmethod
    def create_topic_object(topic_name, num_partitions=3, replication_factor=1):
        new_topic = kafka.admin.NewTopic(topic_name, num_partitions=num_partitions, replication_factor=replication_factor)
        return new_topic

    @staticmethod
    def create_topic_partition_object(topic, partition, offset):
        topic_partition = kafka.TopicPartition(topic=topic, partition=partition, offset=offset)
        return topic_partition


def run_kafka_rpyc_server(port=18861, protocol_config={'allow_public_attrs': True}):
    ThreadedServer(
        KafkaServer,
        port=port,
        protocol_config=protocol_config
    ).start()


if __name__ == "__main__":
    run_kafka_rpyc_server()
