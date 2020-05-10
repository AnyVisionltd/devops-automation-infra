import logging

from pytest_automation_infra import helpers
from devops_automation_infra.plugins.docker import Docker
from devops_automation_infra.plugins.k8s import K8s

def restart_container_by_service(host, name):
    
    if helpers.is_k8s(host.SshDirect):
        host.K8s.restart_pod_by_service_name(name)
    else:
        host.Docker.restart_container_by_service_name(name)