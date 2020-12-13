from requests import get


def get_default_net_interface(host):
    cmd = "ip route | grep default | cut -d' ' -f 5"
    return host.SshDirect.execute(cmd).strip()


def get_host_ip(host):
    cmd = f"ip addr show | grep '{get_default_net_interface(host)}' | grep  -Po 'inet \\K(\\d+\\.?){{4}}'"
    return host.SshDirect.execute(cmd).strip()


def get_external_host_ip():
    return get('https://api.ipify.org').text
