import logging
import time
import random

from devops_automation_infra.plugins.kafka import Kafka
from devops_automation_infra.plugins.seaweed import Seaweed

from pytest_automation_infra.helpers import hardware_config


@hardware_config(hardware={"host": {}})
def test_basic(base_config):
    seaweed = base_config.hosts.host.Seaweed
    seaweed.verify_functionality()
