
def backup_consul_keys(host):
    ssh = host.SshDirect
    consul = host.Consul
    # try to read back up file
    # if file exists
    #   + restore keys from backup file
    # backup keys to file
    pass