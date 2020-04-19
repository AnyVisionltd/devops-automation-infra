import os
import pickle
import logging
from automation_infra.plugins.ssh_direct import SSHCalledProcessError

def backup_consul_keys(host):
    try:
        sshdirect = host.SshDirect
        consul = host.Consul
        home_dir = '/home/' + host.user  if host.user is not 'root' else '/root'
        work_dir = home_dir + '/.local/pytest_env/consul_state'
        sshdirect.execute(f"mkdir -p {work_dir}")
        
        # try to read back up file
        try:
            logging.info(f"download all default keys file: {work_dir}/all_default_keys.pickle")
            res = sshdirect.execute(f"ls {work_dir}/all_default_keys.pickle")
            sshdirect.download("keys.tmp", f"{work_dir}/all_default_keys.pickle")
            with open("keys.tmp", "rb") as f:
                all_default_keys_dict = pickle.load(f)
            os.remove("keys.tmp")
            consul.reset_state(all_default_keys_dict) #restore keys from backup file
            sshdirect.execute(f"rm -f {work_dir}/all_default_keys.pickle")

        except SSHCalledProcessError as e:
            if 'No such file or directory' not in e.stderr:
                raise e

        # backup keys to file
        with open("keys.tmp", 'wb') as f:
            pickle.dump(consul.get_all_keys(), f)
        logging.info(f"upload all default keys file: {work_dir}/all_default_keys.pickle")
        sshdirect.upload("keys.tmp", f"{work_dir}/all_default_keys.pickle")
        os.remove("keys.tmp")

    except Exception as e:
        raise Exception(f"Error while backup consul keys, {e}")
