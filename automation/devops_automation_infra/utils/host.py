import logging


def get_default_net_interface(host):
    cmd = "ip route | grep default | cut -d' ' -f 5"
    return host.SshDirect.execute(cmd).strip()


def get_host_ip(host):
    network_iface = get_default_net_interface(host)
    logging.debug(f"using network_interface {network_iface}")
    cmd = f"ip addr show | grep '{network_iface}' | grep  -Po 'inet \\K(\\d+\\.?){{4}}'"
    return host.SshDirect.execute(cmd).strip()
