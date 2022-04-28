import json
import os
import pickle
import logging
from automation_infra.plugins.ssh_direct import SSHCalledProcessError
import consul


def get_services(client):
    return client.catalog.services()[1]


def get_service_nodes(client, service_name):
    return client.catalog.service(service_name)[1]


def is_healthy(client, service_name, instance_name):
    nodes = client.health.service(service_name)[1]
    for node in nodes:
        if node["Service"]["ID"] == instance_name:
            return "critical" not in [check["Status"] for check in node["Checks"]]
    return False


def backup_consul_keys(host):
    try:
        sshdirect = host.SshDirect
        consul = host.Consul
        home_dir = '/home/' + host.user  if host.user is not 'root' else '/root'
        work_dir = home_dir + '/.local/pytest_env/consul_state'
        sshdirect.execute(f"mkdir -p {work_dir}")
        
        # try to read back up file
        try:
            logging.debug(f"download all default keys file: {work_dir}/all_default_keys.pickle")
            res = sshdirect.execute(f"ls {work_dir}/all_default_keys.pickle")
            sshdirect.download("keys.tmp", f"{work_dir}/all_default_keys.pickle")
            with open("keys.tmp", "rb") as f:
                all_default_keys_dict = pickle.load(f)
            os.remove("keys.tmp")
            current_keys = consul.get_all_keys()
            if current_keys != all_default_keys_dict:
                consul.reset_state(all_default_keys_dict) #restore keys from backup file
            sshdirect.execute(f"rm -f {work_dir}/all_default_keys.pickle")

        except SSHCalledProcessError as e:
            if 'No such file or directory' not in e.stderr:
                raise e

        # backup keys to file
        with open("keys.tmp", 'wb') as f:
            pickle.dump(consul.get_all_keys(), f)
        logging.debug(f"upload all default keys file: {work_dir}/all_default_keys.pickle")
        sshdirect.upload("keys.tmp", f"{work_dir}/all_default_keys.pickle")
        os.remove("keys.tmp")

    except Exception as e:
        raise Exception(f"Error while backup consul keys, {e}")


def get_key(client, key):
    res = client.kv.get(key)[1]['Value']
    return res


def get_key_layered(client, service_name, key):
    layers_read_order = [client.OVERRIDE_KEY, client.APPLICATION_KEY, client.DEFAULT_KEY]
    for layer in layers_read_order:
        layered_key = f"{layer}/{service_name}/{key}"
        value = client.kv.get(layered_key)[1]
        if value is not None:
            return value['Value']
    return None


def get_key_if_exists(client, key):
    value = None
    res = client.kv.get(key)[1]
    if res is not None:
        value = res['Value']
    return value


def put_key(client, key, value):
    if isinstance(value, dict):
        value = json.dumps(value)
    else:
        value = str(value)
    res = client.kv.put(key, value)
    return res