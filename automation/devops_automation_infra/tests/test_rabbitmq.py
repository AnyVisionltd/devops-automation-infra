import logging
from automation_infra.utils.waiter import wait_for_predicate_nothrow
from pytest_automation_infra.helpers import hardware_config
from devops_automation_infra.plugins.rabbitmq import Rabbitmq
import pika
import time


@hardware_config(hardware={"host": {}})
def test_rabbit_ha(base_config):
    num_of_messages = 10
    queueu_name = "test_queue"
    produce_messages_list = []
    for i in range(0,num_of_messages):
        produce_message_dict = {}
        produce_message_dict['exchange'] = ''
        produce_message_dict['routing_key'] = queueu_name
        produce_message_dict['body'] = 'Hello World!'
        produce_message_dict['mandatory'] = True
        produce_message_dict['properties'] = pika.BasicProperties(delivery_mode=2)
        produce_messages_list.append(produce_message_dict)

    consume_message_dict = {"queue": queueu_name, "auto_ack": False}

    rmq = base_config.hosts.host.Rabbitmq

    rmq.reset_state()

    connection = rmq.create_amqp_connection()
    channel = connection.channel
    channel.queue_declare(queue=queueu_name, durable=True)
    
    # test 10 queue and consume them
    connection.produce_messages(produce_messages_list)
    wait_for_predicate_nothrow(lambda: channel.queue_declare(queue=queueu_name, durable=True).method.message_count == num_of_messages, timeout=120)
    for i in range(0,num_of_messages):
        method_frame, header_frame, body = connection.consume_message(**consume_message_dict)
        if method_frame is None:
            logging.debug(f"The queue {consume_message_dict['queue']} Channel is Empty")
            break
        logging.debug(f"Message content from queue {consume_message_dict['queue']}: {body}")
        connection.ack_message(method_frame.delivery_tag)
    wait_for_predicate_nothrow(lambda: channel.queue_declare(queue=queueu_name, durable=True).method.message_count == 0, timeout=120)

    # produce 10 messages in the queue
    connection.produce_messages(produce_messages_list)
    wait_for_predicate_nothrow(lambda: channel.queue_declare(queue=queueu_name, durable=True).method.message_count == num_of_messages, timeout=120)

    # down 1 instance (not the host under test)
    queueu_owner_node = rmq.get_vhost_node()
    connection.close()
    logging.info(f'Here you need to bring down the queue node owner {queueu_owner_node}')
    time.sleep(180)

    # re connect to rabbitmq after node owner is down
    connection = rmq.create_amqp_connection()
    channel = connection.channel
    wait_for_predicate_nothrow(lambda: connection.ping(), timeout=120)
    channel.queue_declare(queue=queueu_name, durable=True)

    # check 10 messages exist
    assert channel.queue_declare(queue=queueu_name, durable=True).method.message_count == num_of_messages

    #consume_messages(channel, num_of_messages)
    for i in range(0,num_of_messages):
        method_frame, header_frame, body = connection.consume_message(**consume_message_dict)
        if method_frame is None:
            logging.debug(f"The queue {consume_message_dict['queue']} Channel is Empty")
            break
        logging.debug(f"Message content from queue {consume_message_dict['queue']}: {body}")
        connection.ack_message(method_frame.delivery_tag)
    wait_for_predicate_nothrow(lambda: channel.queue_declare(queue=queueu_name, durable=True).method.message_count == 0, timeout=120)
    
    # produce additional 10 messages in queue and consume all while one server is down
    connection.produce_messages(produce_messages_list)
    wait_for_predicate_nothrow(lambda: channel.queue_declare(queue=queueu_name, durable=True).method.message_count == num_of_messages, timeout=120)
    for i in range(0,num_of_messages):
        method_frame, header_frame, body = connection.consume_message(**consume_message_dict)
        if method_frame is None:
            logging.debug(f"The queue {consume_message_dict['queue']} Channel is Empty")
            break
        logging.debug(f"Message content from queue {consume_message_dict['queue']}: {body}")
        connection.ack_message(method_frame.delivery_tag)    
    wait_for_predicate_nothrow(lambda: channel.queue_declare(queue=queueu_name, durable=True).method.message_count == 0, timeout=120)
    
    logging.info(f'here you can bring up again the node {queueu_owner_node}')

    # cleanup
    channel.queue_delete(queue=queueu_name)
    connection.close()
    