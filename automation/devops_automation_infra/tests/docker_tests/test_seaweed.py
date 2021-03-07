import logging
import time
import random

from devops_automation_infra.plugins.kafka import Kafka
from devops_automation_infra.plugins.seaweed import Seaweed

from pytest_automation_infra.helpers import hardware_config


def _test_deploy_to_s3(host):
    logging.info("trying to upload to s3")
    host.Seaweed.deploy_resource_to_s3("core/images/angledfaces.jpg", "tmp/multipart.jpg")
    aws_content = host.ResourceManager.file_content("anyvision-testing", "core/images/angledfaces.jpg")
    local_content = host.Seaweed.get_raw_resource("tmp/multipart.jpg", bucket="automation_infra")
    assert aws_content == local_content
    logging.info("trying with small chunk size")
    host.Seaweed.deploy_resource_to_s3("core/images/angledfaces.jpg", "tmp/multipart1.jpg", chunk_size=1024)
    local_content = host.Seaweed.get_raw_resource("tmp/multipart1.jpg", bucket="automation_infra")
    assert aws_content == local_content


@hardware_config(hardware={"host": {}})
def test_basic(base_config):
    seaweed = base_config.hosts.host.Seaweed
    seaweed.verify_functionality()
    _test_deploy_to_s3(base_config.hosts.host)
