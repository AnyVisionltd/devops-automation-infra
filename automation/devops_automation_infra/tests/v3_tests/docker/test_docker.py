import logging

from devops_automation_infra.plugins import docker
from pytest_automation_infra.helpers import hardware_config
import tempfile


@hardware_config(hardware={"host": {}})
def test_docker(base_config):
    temp = tempfile.NamedTemporaryFile(delete=True)
    temp.write(b'Sasha king')
    temp.flush()
    logging.info("write somethinh to proxy container")
    base_config.hosts.host.Docker.copy_file_to_container("automation_proxy", temp.name, "/tmp/test_file")
    logging.info("Read from proxy container")
    content = base_config.hosts.host.SSH.get_contents("/tmp/test_file")
    assert content == b"Sasha king"
    temp.close()
    ids = base_config.hosts.host.Docker.container_ids_by_name("automation_proxy")
    assert len(ids) == 1
