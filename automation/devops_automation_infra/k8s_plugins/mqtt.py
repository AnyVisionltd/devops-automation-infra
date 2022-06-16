import kubernetes
from kubernetes.client import ApiException
import logging
import kafka
from paho.mqtt import client as mqtt_client

from kafka.errors import NoBrokersAvailable
from devops_automation_infra.k8s_plugins.kubectl import Kubectl
from devops_automation_infra.utils import kubectl
from infra.model import cluster_plugins
from automation_infra.utils import waiter


def ping():
    logging.info("not implemented yet")


class Mqtt:
    def __init__(self, cluster):
        self._cluster = cluster
        self._namespace = 'default'
        self._name = 'mqtt'
        self._port = 1883
        ##maybe change later
        self._host = cluster.hosts.host1.ip
        self._client_id = "automation"
        self._dns_name = "idk"

    def create_client(self):
        def on_connect(client, userdata, flags, rc):
            if rc == 0:
                print("Connected to MQTT Broker!")
            else:
                print("Failed to connect, return code %d\n", rc)

        # Set Connecting Client ID
        client = mqtt_client.Client(self._client_id, clean_session=True,)
        client.username_pw_set(self._client_id)
        client.on_connect = on_connect
        client.connect(self._host, self._port, 300)
        return client

    @property
    def _master(self):
        return self._cluster.K8SMaster()

    @property
    def _tunnel(self):
        return self._master.TunnelManager.get_or_create('consul', self._dns_name, self._port)

    @property
    def _is_running(self):
        return kubectl.is_stateful_set_ready(name='mqtt', client=self._cluster.Kubectl.client())


cluster_plugins.register('Mqtt', Mqtt)
