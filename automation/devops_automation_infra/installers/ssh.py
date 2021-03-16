import logging
import gossip


@gossip.register('session', tags=['ssh'], provides=['ssh'])
def ssh_direct_connect(host, request):
    init_host_ssh_direct(host)
    mkdir_infra(host)


def init_host_ssh_direct(host):
    if host.pkey:
        host.add_to_ssh_agent()
    logging.info(f"[{host}] waiting for ssh connection...")
    host.SshDirect.connect(timeout=60)
    logging.info(f"[{host}] success!")


def mkdir_infra(host):
    host.SshDirect.execute("mkdir -p -m 777 /tmp/automation_infra")