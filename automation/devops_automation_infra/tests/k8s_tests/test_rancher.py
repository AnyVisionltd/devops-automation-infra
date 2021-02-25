import os
from pytest_automation_infra.helpers import hardware_config
from devops_automation_infra.k8s_plugins.rancher import Rancher


@hardware_config(hardware={"host1": {"hardware_type": "ai_camera", }},
                 grouping={"cluster1": {"hosts": ["host1"]}})
def test_install_data_layer(base_config):
    rancher = Rancher(base_config.clusters.cluster1)
    rancher.add_catalog("https://chart.tls.ai/bettertomorrow-v2", "master",
                        "online", os.environ.get("CATALOG_USERNAME"), os.environ.get("CATALOG_PASS"))
    rancher.install_app("bettertomorrow-v2-data", "2.3.1-master")
