import logging

from pytest_automation_infra.helpers import hardware_config


@hardware_config(hardware={"host": {}})
def test_one(base_config):
    # import pdb; pdb.set_trace()
    logging.info("Running devops test_one...")
    logging.info(f"ls /: {base_config.hosts.host.SshDirect.execute('ls / ')}")
    logging.info(f"ls /: {base_config.hosts.host.SSH.execute('ls / ')}")
    logging.info("Finished devops test_one!")
    assert True


@hardware_config(hardware={"host": {}})
def test_two(base_config):
    logging.info(f"ls /: {base_config.hosts.host.SshDirect.execute('ls / ')}")
    logging.info(f"ls /: {base_config.hosts.host.SSH.execute('ls / ')}")

    assert True\

@hardware_config(hardware={"host": {}})
def test_3(base_config):
    logging.info(f"ls /: {base_config.hosts.host.SshDirect.execute('ls / ')}")
    logging.info(f"ls /: {base_config.hosts.host.SSH.execute('ls / ')}")

    assert True
@hardware_config(hardware={"host": {}})
def test_4(base_config):
    logging.info(f"ls /: {base_config.hosts.host.SshDirect.execute('ls / ')}")
    logging.info(f"ls /: {base_config.hosts.host.SSH.execute('ls / ')}")

    assert True
@hardware_config(hardware={"host": {}})
def test_5(base_config):
    logging.info(f"ls /: {base_config.hosts.host.SshDirect.execute('ls / ')}")
    logging.info(f"ls /: {base_config.hosts.host.SSH.execute('ls / ')}")

    assert True


@hardware_config(hardware={"host": {"gpu": 1}})
def test_six(base_config):
    logging.info(f"ls /: {base_config.hosts.host.SshDirect.execute('ls / ')}")
    logging.info(f"ls /: {base_config.hosts.host.SSH.execute('ls / ')}")
    assert True