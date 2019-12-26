import os
import random
import time
import pytest
import random
from runner.helpers import hardware_config

# These (and all other used plugins) need to be imported even though they are grayed out in pycharm!
from devops_plugins import memsql, memsql, seaweed

# automation-infra repo needs to be added as content root to pycharm project
# TODO: create installer for plugin and add to requirements
pytest_plugins = "pytest_automation_infra"

# These are all example tests:
@hardware_config(hardware={"type": "pasha_pass"})
def test_ssh(base_config):
    print("Running ssh test!")
    os.system("echo this is a test > /tmp/temp.txt")
    base_config.host.SSH.put('/tmp/temp.txt', '/tmp')
    res = base_config.host.SSH.execute('ls /tmp')
    assert 'temp.txt' in res.split()
    base_config.host.SSH.execute('rm /tmp/temp.txt')
    res = base_config.host.SSH.execute('ls /tmp')
    assert 'temp.txt' not in res.split()


@hardware_config(hardware={"type": "pasha_pass"})
def test_s3(base_config):
    base_config.host.Seaweed.create_bucket('test_bucket')
    content = base_config.host.Seaweed.get_buckets()
    assert b'test_bucket' in content
    base_config.host.Seaweed.delete_bucket('test_bucket')
    content = base_config.host.Seaweed.get_buckets()
    assert b'test_bucket' not in content


@hardware_config(hardware={"type": "pasha_pass"})
def test_memsql_add_suspect(base_config):
    poi_id = random.randint(0, 999999)
    query = f'''INSERT INTO `reid_db`.`poi`
            (`poi_id`,`detection_type`,`is_ignored`,`feature_id`,`features`,`valid_until`)
            VALUES
            ({poi_id},1,0,123,123,4141);'''
    res = base_config.host.Memsql.upsert(query)
    assert res == 1


memsql_suspects_to_add = [[random.randint(1, 999999),1,0,123,123,4141] for i in range(5)]
test_data = [(tuple(suspect), 1) for suspect in memsql_suspects_to_add]


@hardware_config(hardware={"type": "ori_pass"})
@pytest.mark.parametrize("suspect, expected", test_data)
def test_memsql_add_suspects(base_config, suspect, expected):
    query = f'''INSERT INTO `reid_db`.`poi`
            (`poi_id`,`detection_type`,`is_ignored`,`feature_id`,`features`,`valid_until`)
            VALUES
            {suspect};'''
    res = base_config.host.Memsql.upsert(query)
    assert res == expected


@hardware_config(hardware={"type": "ori_pass"})
def test_consul_get_services(base_config):
    _, services_dict = base_config.host.Consul.get_services()
    assert len(services_dict) > 0
    assert 'camera-service' in services_dict
    put_key, put_val = ("test_key", "test_val")
    res = base_config.host.Consul.put_key(put_key, put_val)
    assert res is True
    val = base_config.host.Consul.get_key("test_key")
    assert val.decode('utf-8') == put_val


@hardware_config(hardware={"type": "pasha_pass"})
def test_kafka_functionality(base_config):
    topics = base_config.host.Kafka.get_topics()
    assert len(topics.topics) > 0
    success = base_config.host.Kafka.create_topic('oris_new_topic')
    assert success
    time.sleep(5)
    success = base_config.host.Kafka.delete_topic('oris_new_topic')
    assert success


if __name__ == '__main__':
    # These are examples of possible ways to run:
    pytest.main(['test_demo.py::test_memsql_add_suspects', ])
    #pytest.main(['test_demo.py', ])
