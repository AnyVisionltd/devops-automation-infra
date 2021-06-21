import logging

from pytest_automation_infra import helpers
from devops_automation_infra.plugins.docker import Docker
from devops_automation_infra.plugins.k8s import K8s
from automation_infra.plugins.ssh_direct import SSHCalledProcessError



def restart_container_by_service(host, name):
    if helpers.is_k8s(host.SshDirect):
        host.K8s.restart_pod_by_service_name(name)
    else:
        host.Docker.restart_container_by_service_name(name)


def stop_container_by_service(host, name):
    if helpers.is_k8s(host.SshDirect):
        raise NotImplementedError("Stop container not implemented yet")
    else:
        host.Docker.kill_container_by_service(name)


def start_container_by_service(host, name):
    if helpers.is_k8s(host.SshDirect):
        raise NotImplementedError("Start container not implemented yet")
    else:
        host.Docker.run_container_by_service(name)


def is_docker(host):
    try:
        host.SshDirect.execute("which docker")
    except SSHCalledProcessError:
        return False
    return True


def is_crio(host):
    try:
        host.SshDirect.execute("which crictl")
    except SSHCalledProcessError:
        return False
    return True


def get_container_engine(host):
    if is_crio(host):
        return "crio"
    elif is_docker(host):
        return "docker"
    else:
        raise Exception("Couldn't find container engine on host")
