import os
import pickle
from automation_infra.plugins.ssh_direct import SSHCalledProcessError

def backup_consul_keys(host):
    try:
        sshdirect = host.SshDirect
        consul = host.Consul
        sshdirect.execute("mkdir -p $HOME/.local/pytest_env/consul_state")
        
        # try to read back up file
        try:
            res = sshdirect.execute("ls $HOME/.local/pytest_env/consul_state/all_default_keys.pickle")
            sshdirect.download("keys.tmp", "$HOME/.local/pytest_env/consul_state/all_default_keys.pickle")
            with open("keys.tmp", "rb") as f:
                all_default_keys_dict = pickle.load(f)
            os.remove("keys.tmp")
            consul.reset_state(all_default_keys_dict) #restore keys from backup file
            sshdirect.execute("rm -f  $HOME/.local/pytest_env/consul_state/all_default_keys.pickle")

        except SSHCalledProcessError as e:
            if 'No such file or directory' not in e.stderr:
                raise e

        # backup keys to file
        with open("keys.tmp", 'wb') as f:
            pickle.dump(consul.get_all_keys(), f)
        sshdirect.upload("keys.tmp",  "$HOME/.local/pytest_env/consul_state/all_default_keys.pickle")
        os.remove("keys.tmp")

    except Exception as e:
        raise Exception("Error while backup consul keys\nmessage: ")# + e.message)
