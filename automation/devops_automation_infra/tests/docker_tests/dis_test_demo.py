import os
import time

from pytest_automation_infra.helpers import hardware_config

# These plugins need to be imported even though theyre grayed out:
from automation_infra.plugins.ssh import SSH
from devops_automation_infra.plugins.seaweed import Seaweed
from devops_automation_infra.plugins.consul import Consul
from devops_automation_infra.plugins.kafka import Kafka
from devops_automation_infra.plugins.memsql import Memsql

hardware = {"type": "ori_pass"}


@hardware_config(hardware={"host": {}})
def test_ssh(base_config):
    print("Running ssh test!")
    os.system("echo this is a test > /tmp/temp.txt")
    base_config.hosts.host.SSH.put('/tmp/temp.txt', '/tmp')
    res = base_config.hosts.host.SSH.execute('ls /tmp')
    assert 'temp.txt' in res.split()
    base_config.hosts.host.SSH.execute('rm /tmp/temp.txt')
    res = base_config.hosts.host.SSH.execute('ls /tmp')
    assert 'temp.txt' not in res.split()


@hardware_config(hardware={"host": {}})
def test_s3(base_config):
    base_config.hosts.host.Seaweed.create_bucket('test_bucket')
    base_config.hosts.host.Seaweed.delete_bucket('test_bucket')


@hardware_config(hardware={"host": {}})
def test_memsql_seaweed_together(base_config):
    query = '''CREATE TABLE if not exists tracks_db.students (
    stud_id INT,
    stud_group INT,
    joining_date DATETIME
    );'''
    res = base_config.hosts.host.Memsql.upsert(query)
    base_config.hosts.host.Memsql.upsert("drop table if exists tracks_db.students")
    base_config.hosts.host.Seaweed.create_bucket("test_bucket")
    assert True


@hardware_config(hardware={"host": {}})
def test_consul_get_services(base_config):
    services_dict = base_config.hosts.host.Consul.get_services()
    assert len(services_dict) > 0
    assert 'camera-service' in services_dict
    put_key, put_val = ("test_key", "test_val")
    res = base_config.hosts.host.Consul.put_key(put_key, put_val)
    assert res is True
    val = base_config.hosts.host.Consul.get_key("test_key")
    assert val.decode('utf-8') == put_val


@hardware_config(hardware={"host": {}})
def test_kafka_functionality(base_config):
    topics = base_config.hosts.host.Kafka.get_topics()
    assert len(topics) > 0
    success = base_config.hosts.host.Kafka.create_topics('oris_new_topic')
    assert success
    time.sleep(5)
    success = base_config.hosts.host.Kafka.delete_topics('oris_new_topic')
    assert success
