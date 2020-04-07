import logging
import time
import random

from devops_automation_infra.plugins.kafka import Kafka
from devops_automation_infra.plugins.seaweed import Seaweed

from pytest_automation_infra.helpers import hardware_config


@hardware_config(hardware={"host": {}})
def test_basic(base_config):
    seaweed = base_config.hosts.host.Seaweed
    seaweed.create_bucket("test_bucket")
    seaweed.upload_file_to_bucket("media/phase_1.png", "test_bucket", "media/phase_1.png")
    bucket_files = seaweed.get_bucket_files('test_bucket')
    assert bucket_files == ['media/phase_1.png']
    seaweed.delete_bucket("test_bucket")
    logging.info(f"<<<<<<<<<<<<<SEAWEED PLUGIN FUNCTIONING PROPERLY>>>>>>>>>>>>>")