from kafka.admin import ConfigResource
from automation_infra.utils import waiter


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

