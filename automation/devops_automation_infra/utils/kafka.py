from kafka.admin import ConfigResource
from automation_infra.utils import waiter
import kubernetes
from devops_automation_infra.utils import kubectl

def clear_all_topics(admin, consumer):
    for topic_name in admin.list_topics():
        if topic_name != '__consumer_offsets':
            clear_topic(admin, consumer, topic_name)


# In order to make this function work, need to make sure that this configuration is applied:
# kubectl patch kafkas.kafka.strimzi.io kafka-cluster --type merge -p '{"spec":{"kafka":{"config":{"log.retention.check.interval.ms": 1000}}}}'
# Also, it won't work if there's any producer activated
def clear_topic(admin, consumer, name):
    retention = get_topic_config_value(admin, name, 'retention.ms')
    update_topic_config(admin, name, {"retention.ms": 1000})
    consumer.subscribe(name)
    # Lazy initiate of topic assignment
    consumer.topics()
    waiter.wait_for_predicate(lambda: consumer.beginning_offsets(consumer.assignment()) ==
                                      consumer.end_offsets(consumer.assignment()))

    update_topic_config(admin, name, {"retention.ms": retention})
    consumer.close()


def get_topic_config_value(admin, topic_name, config_key):
    described_config = admin.describe_configs([ConfigResource(resource_type='topic', name=topic_name)])[0].to_object()
    if described_config['resources'][0]['error_code'] != 0:
        raise Exception(
            f"Failed to get topic {topic_name} config: {described_config['resources'][0]['error_message']}")

    config_value = next((config['config_value'] for config in described_config['resources'][0]['config_entries'] if
                         config['config_names'] == config_key))

    return config_value


def update_topic_config(admin, topic_name, body):
    alter_config_response = admin.alter_configs([ConfigResource(resource_type='topic', name=topic_name,
                                                                configs=body)]).to_object()
    if alter_config_response['resources'][0]['error_code'] != 0:
        raise Exception(
            f"Failed to update topic {topic_name}: {alter_config_response['resources'][0]['error_message']}")

def update_retention_check_interval(k8s_client, kafka_name, namespace="default", interval=1000):
    custom_object_client = kubernetes.client.CustomObjectsApi(k8s_client)
    body = {"spec": {"kafka": {"config": {"log.retention.check.interval.ms": interval}}}}
    custom_object_client.patch_namespaced_custom_object(namespace=namespace,
                                                        group='kafka.strimzi.io',
                                                        version='v1beta1',
                                                        plural='kafkas',
                                                        name=kafka_name,
                                                        body=body)

    waiter.wait_for_predicate(lambda: kubectl.is_stateful_set_ready(k8s_client, f"{kafka_name}-kafka", namespace=namespace), timeout=60)


def read_x_messages_from_kafka_consumer(consumer, messages_number, reader_offset='latest', timeout_ms=5000):
    if not consumer.subscription():
        raise Exception("No topic assigned to consumer")

    consumer.config['consumer_timeout_ms'] = timeout_ms

    if not consumer.config['auto_offset_reset']:
        consumer.config['auto_offset_reset'] = reader_offset

    messages = []

    while len(messages) < messages_number:
        try:
            messages.append(next(consumer).value)
        except StopIteration:
            raise TimeoutError(f"Could not read {messages_number} messages from kafka, got {len(messages)}")

    return messages