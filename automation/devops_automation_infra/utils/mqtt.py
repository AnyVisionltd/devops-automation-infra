import logging

from paho.mqtt import client as mqtt_client


def subscribe(client: mqtt_client, topic):
    def on_message(client, userdata, msg):
        logging.info(f"Received `{msg.payload.decode()}` from `{msg.topic}` topic")

    client.subscribe(topic)
    client.on_message = on_message


def publish(client, topic, msg):
    result = client.publish(topic, msg)
    status = result[0]
    if status == 0:
        logging.info(f"Send `{msg}` to topic `{topic}`")
    else:
        logging.info(f"Failed to send message to topic {topic}")
