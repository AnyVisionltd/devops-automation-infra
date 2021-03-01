import logging
import os

from devops_automation_infra.k8s_plugins.rancher import Rancher
from pytest_automation_infra.helpers import hardware_config


@hardware_config(hardware={"host1": {"hardware_type": "vm", "base_image": "gravity_infra_230"}},
                 grouping={"cluster1": {"hosts": ["host2"]}})
def test_rancher_install(base_config):
    rancher = base_config.clusters.cluster1.Rancher
    app_layer_name, version, catalog = "some_product", "1.0.1", "online"
    rancher.add_catalog("url for chart repo", "master",
                        catalog, os.environ.get("CATALOG_USERNAME"), os.environ.get("CATALOG_PASS"))
    rancher.refresh_catalog(catalog)
    rancher.install_app(app_name=app_layer_name, version=version, timeout=600)
    assert rancher.app_exists(app_layer_name), f"Failed to install app {app_layer_name}"
    rancher.delete_app(app_layer_name)