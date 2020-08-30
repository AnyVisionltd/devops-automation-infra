import redis
import logging
from automation_infra.plugins import tunnel_manager
from infra.model import plugins
from pytest_automation_infra import helpers
from devops_automation_infra.utils import container
from automation_infra.utils import waiter


class Redis(object):
    def __init__(self, host):
        self._host = host
        self.DNS_NAME = 'redis.tls.ai' if not helpers.is_k8s(self._host.SshDirect) else 'redis-server.default.svc.cluster.local'
        self.PORT = 6379

    @property
    def tunnel(self):
        return self._host.TunnelManager.get_or_create('redis', self.DNS_NAME, self.PORT)

    def create_client(self):
        host, port = self.tunnel.host_port
        return redis.Redis(host=host, port=port, db=0)

    @property
    def _redis(self):
        return self.create_client()
    
    def set_key(self, key, value):
        return self._redis.set(key, value)

    def get_key(self, key):
        return self._redis.get(key)

    def key_exists(self, key):
        return self._redis.exists(key)

    def delete_key(self, key):
        return self._redis.delete(key)

    def clear_and_start(self):
        self._redis.flushall()
        container.start_container_by_service(self._host, "_redis")
        waiter.wait_nothrow(self.ping, timeout=30)

    def ping(self):
        return self._redis.ping()

    def wait_for_redis_to_be_up(self):
        waiter.wait_for_predicate(lambda: self.ping(), timeout=30)

    def verify_functionality(self):
        self.ping()
        assert self.set_key("test_key", "test_value")
        assert self.key_exists("test_key")
        assert b"test_value" in self.get_key("test_key")
        assert self.delete_key("test_key")
        assert not self.key_exists("test_key")


plugins.register('Redis', Redis)
