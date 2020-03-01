from pytest_automation_infra.helpers import hardware_config
from devops_automation_infra.plugins.prometheus import PrometheusService


@hardware_config(hardware={"host": {}})
def test_random_query(base_config):
    assert base_config.hosts.host.PrometheusService.\
        query(query='tracks_full_process_duration_from_collate_end_time_to_kafka_s_sum')['status'] == 'success'
