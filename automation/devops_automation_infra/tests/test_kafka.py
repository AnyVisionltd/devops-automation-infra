import logging
import time
import random

from devops_automation_infra.plugins.kafka import Kafka
from pytest_automation_infra.helpers import hardware_config


@hardware_config(hardware={"host": {}})
def test_basic(base_config):
    kafka = base_config.hosts.host.Kafka
    kafka.verify_functionality_full()
