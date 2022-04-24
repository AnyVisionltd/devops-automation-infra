import json
import logging

from devops_automation_infra.utils import consul
from pipeng.utils import tracks
from pipeng.services import pipe
from devops_automation_infra.k8s_plugins.consul import Consul
from devops_automation_infra.k8s_plugins.kafka import Kafka

CONSUL_NAME = 'pipeng_local-agent-default'


def create_kafka_tracks_reader(cluster, reader_offset='latest', topic="anv.tracks.pipeng.new-tracks"):
    kafka_client = cluster.Kafka
    tracks_reader = tracks.Reader(kafka_client, topic=topic, reader_offset=reader_offset)
    return tracks_reader


def get_list_pipes_from_consul(cluster):
    consul_client = cluster.Consul.create_client()
    instances = consul.get_service_nodes(consul_client, "pipeng")
    logging.debug(f'Found {instances} in consul')
    return instances


def get_consul_path(layer, field, node_id=None):
    return f"{layer}/{node_id}/{field}" if node_id is None else f"{layer}/{CONSUL_NAME}/{field}"


def get_consul_value(cluster, key):
    consul_client = cluster.Consul.create_client()

    value_in_bytes = consul.get_key_layered(consul_client, key)
    value_as_string = value_in_bytes.decode('utf-8')
    try:
        return json.loads(value_as_string)
    except json.decoder.JSONDecodeError:
        return value_as_string


def scale_node_daemon_pod_to_x(cluster, replicas):
    return cluster.hosts.host1.K8s.scale(f"node-daemon", replicas=replicas)
