from infra.plugins.base_plugin import TunneledPlugin
from infra.model import plugins
from datetime import datetime

from confluent_kafka import Consumer, Producer, TopicPartition
from confluent_kafka.admin import AdminClient, NewTopic, KafkaException

from runner import helpers


class Kafka(TunneledPlugin):
    def __init__(self, host):
        super().__init__(host)
        self.DNS_NAME = 'kafka.tls.ai' if not helpers.is_k8s(self._host.SSH) else 'kafka.default.svc.cluster.local'
        self.PORT = 9092
        self.start_tunnel(self.DNS_NAME, self.PORT)
        self.kafka_config = {'bootstrap.servers': f"localhost:{self.local_bind_port}", 'group.id': "automation-group",
                             'session.timeout.ms': 6000, 'auto.offset.reset': 'earliest'}

        self._kafka_admin = None
        self._c = None
        self._p = None

    @property
    def consumer(self):
        if self._c is None:
            self._c = Consumer(self.kafka_config)
        return self._c

    @property
    def producer(self):
        if self._p is None:
            self._p = Producer(self.kafka_config)
        return self._p

    @property
    def admin(self):
        if self._kafka_admin is None:
            self._kafka_admin = AdminClient(self.kafka_config)
        return self._kafka_admin

    def get_topics(self):
        topics = self.admin.list_topics(timeout=5)
        return topics.topics

    def create_topic(self, name):
        """create topic if not exists"""
        new_topic = NewTopic(name, num_partitions=3, replication_factor=1)
        fs = self.admin.create_topics([new_topic])
        for topic, f in fs.items():
            try:
                f.result()  # The result itself is None
                print("Topic {} created".format(topic))
                return True
            except KafkaException:
                # TODO: validate this exception is thrown only when topic exists and not in other cases
                # Othewise can add check before trying to create it...
                print("topic already exists")
                return True
            except Exception as e:
                print("Failed to create topic {}: {}".format(topic, e))
                raise

    def get_message(self, topic, tries=3):
        self.consumer.subscribe(topic)
        for i in range(tries):
            msg = self.consumer.poll()
            if msg is not None:
                return msg
            else:
                return None


    def consume_messages_for_x_seconds(self, topic, seconds):
        self.consumer.subscribe(topic)
        list_of_msg = []
        for i in range(seconds):
            msg = self.consumer.poll(timeout=1)
            if msg is not None:
                list_of_msg.append(msg)
        return list_of_msg

    def consume_iter(self, topics, timeout=None, commit=False):
        """ Generator - use Kafka consumer for receiving messages from the given *topics* list.
            Yield a tuple of each message key and value.
            If got a *timeout* argument - break the loop if passed the value in seconds, but did not
            received messages since the last one was processed.
            If the optional argument *commit* is true, commit each message consumed."""
        # if len(topic) == 0:
        #     raise TypeError('at least one topic must be received to consume_iter instance')

        print(f'Started receiving messages (timeout: {timeout}).')

        try:
            self.consumer.subscribe(topics)
            self._is_consuming = True
            last_ts = datetime.now()
            while timeout is None or (datetime.now() - last_ts).seconds < timeout:
                for i in range(2):
                    msg = self.consumer.poll(timeout=1)
                    self._last_message = msg
                    if msg is not None:
                        last_ts = datetime.now()
                        yield msg
                if commit is True and msg is not None:
                    offset = msg.offset()
                    if offset < 0:
                        offset = 0
                    tpo = TopicPartition(topic=msg.topic(), partition=msg.partition(), offset=offset)
                    self.consumer.commit(offsets=[tpo], asynchronous=True)
        except Exception as e:
            print(f"Error in consume_iter {e}")
        finally:
            self._is_consuming = False
            self._last_message = None

    def parse_message(self, msg):
        key, value = msg.key().decode(), msg.value().decode()
        return key, value

    @staticmethod
    def delivery_report(err, msg):
        if err:
            raise Exception
        else:
            print(f"message {msg} put successfully")

    def put_message(self, key, msg):
        self.producer.produce(topic=automation_tests_topic, key=key, value=msg, callback=self.delivery_report)
        self.producer.poll(0)

    def delete_topic(self, topic):
        fs = self.admin.delete_topics([topic], operation_timeout=30)

        # Wait for operation to finish.
        for topic, f in fs.items():
            try:
                f.result()  # The result itself is None
                print("Topic {} deleted".format(topic))
                return True
            except Exception as e:
                print("Failed to delete topic {}: {}".format(topic, e))


plugins.register('Kafka', Kafka)


def test_basic(base_config):
    topics = base_config.host.Kafka.get_topics()
    print(topics)
