import pytest

from pytest_automation_infra import determine_scope


@pytest.fixture(scope=determine_scope)
def clean_up_all_deployments_and_svcs(base_config):
    k8s = base_config.hosts.host1.K8s
    k8s.delete_deployment(name="", all=True)
    k8s.delete_svc(svc_name="", all=True)
    yield
    k8s.delete_deployment(name="", all=True)
    k8s.delete_svc(svc_name="", all=True)
