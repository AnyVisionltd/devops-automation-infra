import json
import logging

import common_pb2
from devops_automation_infra.utils import consul
from pipeng.utils import tracks
from pipeng.services import pipe as pipe_service
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


def create_stream_settings_for_jetson():
    stream_config = pipe_service.create_stream_config(flow_type=common_pb2.FACE, **{
        "association_threshold": 0.5,
        "auto_skip_enabled": True,
        "rotation_angle": -1,
        "tracker_face_min_track_length": 1,
        "tracker_face_max_track_length": 200,
        "tracker_face_lost_threshold": 45,
        "detection_min_face_size": 48,
        "detection_max_face_size": -1,
        "detection_min_body_size": 20,
        "detection_max_body_size": -1,
        "tracker_body_min_track_length": 4,
        "tracker_body_max_track_length": 200,
        "tracker_body_lost_threshold": 45,
        "camera_group_id": "00000000-0200-4c1b-4e12-1ba74bff4a4b",
        "enable_frame_storage": True
    })
    return stream_config
