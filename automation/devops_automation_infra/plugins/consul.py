import json
import base64
import consul
from automation_infra.plugins import tunnel_manager
from infra.model import plugins
from pytest_automation_infra import helpers
from automation_infra.utils import waiter
from devops_automation_infra.utils import container


class Consul(object):
    def __init__(self, host):
        self._host = host
        self.DNS_NAME = 'consul.tls.ai' if not helpers.is_k8s(self._host.SshDirect) else 'consul-server.default.svc.cluster.local'
        self.PORT = 8500
        self.DEFAULT_KEY = "DEFAULT"
        self.OVERRIDE_KEY = "OVERRIDE"
        self.APPLICATION_KEY = "APPLICATION"

    @property
    def tunnel(self):
        return self._host.TunnelManager.get_or_create('consul', self.DNS_NAME, self.PORT)

    def create_client(self):
        return consul.Consul(*self.tunnel.host_port)

    @property
    def _consul(self):
        return self.create_client()

    def get_services(self):
        return self._consul.catalog.services()[1]

    def get_service_nodes(self, service_name):
        return self._consul.catalog.service(service_name)[1]

    def is_healthy(self, service_name, instance_name):
        nodes = self._consul.health.service(service_name)[1]
        for node in nodes:
            if node["Service"]["ID"] == instance_name:
                return "critical" not in [check["Status"] for check in node["Checks"]]
        return False

    def put_key(self, key, val):
        if isinstance(val, dict):
            val = json.dumps(val)
        else:
            val = str(val)
        res = self._consul.kv.put(key, val)
        return res

    def update_key_value(self, key, val):
        self._consul.kv.delete(key, recurse=False)
        res = self._consul.kv.put(key, val)
        return res

    def get_key(self, key):
        res = self._consul.kv.get(key)[1]['Value']
        return res

    def get_value(self, key):
        plain_value = self._consul.kv.get(key)[1]['Value'].decode()
        try:
            return json.loads(plain_value)
        except Exception:
            return plain_value

    def get_key_if_exists(self, key):
        value = None
        res = self._consul.kv.get(key)[1]
        if res is not None:
            value = res['Value']
        return value

    def delete_key(self, key, recurse=None):
        res = self._consul.kv.delete(key, recurse=recurse)
        return res

    def register_service(self, name, service_id, address, port, check):
        res = self._consul.agent.service.register(
            name=name, service_id=service_id, address=address, port=port, check=check)
        return res

    # python-consul library does not support consul registration with meta data
    # This function use direct http request to consul in order to register service with meta data
    def register_service_with_meta(self, name, service_id, address, port, meta, check=None):
        payload = {"name": name, "id": service_id, "address": address, "port": port, "meta": meta}
        if check:
            payload["check"] = check

        params = []
        if self._consul.agent.service.agent.token:
            params.append(('token', self._consul.agent.service.agent.token))

        return self._consul.agent.service.agent.http.put(
            consul.base.CB.bool(),
            '/v1/agent/service/register',
            params=params,
            data=json.dumps(payload))

    def ping_ttl_check(self, check_id):
        self._consul.agent.check.ttl_pass(check_id=check_id)

    def divide_chunks(self, payload, size):
        for i in range(0, len(payload), size): 
            yield payload[i:i + size]

    def transaction(self, payload):
        client = self._consul
        for chunk in self.divide_chunks(payload, 64):
            client.txn.put(chunk)

    def ping(self):
        leader = self._consul.status.leader()
        if not leader:
            raise Exception("Failed leader is unspecified")
        return leader

    def get_all_keys(self, folder=""):
        _, data = self._consul.kv.get(folder, recurse=True)
        if data is None:
            return None
        return dict((x['Key'], x['Value']) for x in data)

    def create_kv_payload(self, keys={}):
        transaction_arr = []

        for key, value in keys.items():
            transaction_dict = {}
            transaction_dict['KV'] = {}
            transaction_dict['KV']['Verb'] = "set"
            transaction_dict['KV']['Key'] = key
            if type(value) is bytes:
                transaction_dict['KV']['Value'] = base64.b64encode(value).decode()
            elif type(value) is type(None):
                transaction_dict['KV']['Value'] = ""
            else:
                transaction_dict['KV']['Value'] = base64.b64encode(value.encode()).decode()
            transaction_arr.append(transaction_dict)

        return transaction_arr

    def clear_and_start(self):
        self.delete_storage_compose()
        container.start_container_by_service(self._host, "_consul")
        waiter.wait_nothrow(self.ping, timeout=30)

    def delete_storage_compose(self):
        self._host.SshDirect.execute('sudo rm /storage/consul-data/* -rf')

    def verify_functionality(self):
        self.put_key('test_key', 'test_value')
        self.get_key('test_key')
        self.delete_key('test_key')
        first_service = next(iter(self.get_services()))
        self._consul.health.service(first_service)[1]
        self.put_key('test_key_int', 2)
        self.put_key('test_key_float', 2.5)
        dict_value = {"a" : 1, "b": 2.4, "c": "bla"}
        self.put_key('test_key_json', json.dumps(dict_value))
        int_value = self.get_value("test_key_int")
        assert int_value == 2 , "int value not in consul"
        float_value = self.get_value("test_key_float")
        assert float_value == 2.5 , "float value not in consul"
        json_value = self.get_value("test_key_json")
        assert json_value == dict_value , "dict value not in consul"


    def get_key_layered(self, service_name, key):
        layers_read_order = [self.OVERRIDE_KEY, self.APPLICATION_KEY, self.DEFAULT_KEY]
        for layer in layers_read_order:
            layered_key = f"{layer}/{service_name}/{key}"
            value = self.get_key_if_exists(layered_key)
            if value is not None:
                return value
        return None


plugins.register('Consul', Consul)

