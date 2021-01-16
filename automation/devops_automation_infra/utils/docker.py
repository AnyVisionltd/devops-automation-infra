import subprocess

_local_docker_path = None


def _docker_run(cmd):
    global _local_docker_path
    if not _local_docker_path:
        _local_docker_path = subprocess.check_output(['which', 'docker']).strip().decode()
    cmd = f"sudo {_local_docker_path} {cmd}"
    return subprocess.check_output(cmd, shell=True).decode().strip()


def image_exists(image_fqdn):
    cmd = f"images -q {image_fqdn}"
    image = _docker_run(cmd)
    return image != ""


def tag(image_fqdn, tag_fqdn):
    try:
        _docker_run(f"tag {image_fqdn} {tag_fqdn}")
    except:
        if not image_exists(image_fqdn):
            raise Exception(f"Docker image {image_fqdn} does not exists locally")
        raise


def push(image_fqdn):
    _docker_run(f"push {image_fqdn}")


def rmi(image_fqdn):
    _docker_run(f"rmi {image_fqdn}")

