import logging
import time

from automation_infra.utils import waiter
from automation_infra.utils.timer import timeit
from devops_automation_infra.plugins.kafka import Kafka
from pytest_automation_infra.helpers import hardware_config

BACKUP_TOPIC_NAMES = ['anv.mass-import.mass-import-service.files-before-process',
                          'anv.poi.reid.actions',
                          'camera_statuses',
                          'anv.poi.mass-import-service.new-subject',
                          'anv.camera-groups.camera-service.actions',
                          'anv.upload.upload-service.upload-status',
                          'anv.error-messages.anv-kafka.new-error-message',
                          'anv.poi.reid.responses',
                          'anv.upload.upload-service.new-archive',
                          'anv.upload.upload-service.files',
                          'anv.mass-import.mass-import-consumer-producer.files-after-process',
                          'anv.poi.subject-service.subject-created',
                          'anv.storage.delete-object-service.delete',
                          'anv.tracks.tracks-consumer-producer.new-tracks',
                          'anv.cameras.camera-service.actions',
                          'anv.tracks.track-service.actions',
                          'anv.tracks.tracks-consumer-producer.new-recognition',
                          'anv.ignores.ignore-service.notify',
                          'anv.tracks.pipeng.new-tracks',
                          'anv.tracks.reid.new-tracks',
                          'anv.tracks.collate.new-tracks',
                          'anv.socket.socket-service.push',
                          'anv.poi.subject-service.actions',
                          'anv.metrics.tracks-metrics-consumer.new-metrics']


@hardware_config(hardware={"host": {}})
def test_basic(base_config):
    kafka = base_config.hosts.host.Kafka
    kafka.verify_functionality_full()


@hardware_config(hardware={"host": {}})
def test_create_delete_topics(base_config):
    kafka = base_config.hosts.host.Kafka
    with timeit("create topics"):
        kafka.create_topics(*BACKUP_TOPIC_NAMES)

    with timeit("topic_names"):
        created_topics = kafka.topic_names()
        topics = [topic for topic in created_topics if not topic.startswith('__')]
        assert len(topics) == len(BACKUP_TOPIC_NAMES)

    with timeit("delete topics"):
        kafka.delete_all_topics()

    kafka.create_topics(*BACKUP_TOPIC_NAMES)
