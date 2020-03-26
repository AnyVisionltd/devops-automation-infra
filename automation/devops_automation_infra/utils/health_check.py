import subprocess


def host_is_active(host_ip):
    command = ['ping', '-c', '1', host_ip]
    return True if subprocess.call(command) == 0 else False