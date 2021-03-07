import kubernetes
from kubernetes.client import ApiException
import logging
import kafka
from devops_automation_infra.k8s_plugins.kubectl import Kubectl
from infra.model import cluster_plugins


class Kafka:
    def __init__(self, cluster):
        self._cluster = cluster
        self._master = self._cluster.K8SMaster()
        self._name = 'kafka-cluster'
        self._is_exposed = False

    def _expose(self):
        if self._is_exposed:
            return

        logging.debug("Exposing kafka cluster")
        custom_object_client = kubernetes.client.CustomObjectsApi(self._cluster.Kubectl.client())

        kafka_spec = custom_object_client.get_namespaced_custom_object(namespace='default',
                                                                       group='kafka.strimzi.io',
                                                                       version='v1beta1',
                                                                       plural='kafkas',
                                                                       name=self._name)['spec']
        advertised_brokers = {'brokers': []}
        for i in range(0, kafka_spec['kafka']['replicas']):
            advertised_brokers['brokers'].append({'broker': i, 'advertisedHost': self._master.ip})

        kafka_spec['kafka']['listeners']['external'] = {'type': 'nodeport', 'tls': False, 'overrides': advertised_brokers}
        self._is_exposed = True

    def _add_default_options(self, kwargs):
        options = {'bootstrap_servers': self._bootstrap_endpoint()}
        options.update(kwargs)
        return options

    def _bootstrap_endpoint(self):
        v1 = kubernetes.client.CoreV1Api(self._cluster.Kubectl.client())
        port = v1.read_namespaced_service(namespace='default', name='kafka-cluster-kafka-external-bootstrap').spec.ports[0].node_port
        return f"{self._master.ip}:{port}"

    def admin(self, **kwargs):
        self._expose()
        options = self._add_default_options(kwargs)
        return kafka.KafkaAdminClient(**options)

    def consumer(self, **kwargs):
        self._expose()
        options = self._add_default_options(kwargs)
        return kafka.KafkaConsumer(**options)

    def producer(self, **kwargs):
        self._expose()
        options = self._add_default_options(kwargs)
        return kafka.KafkaProducer(**options)

    def ping(self):
        return self.consumer().topics()


cluster_plugins.register('Kafka', Kafka)

