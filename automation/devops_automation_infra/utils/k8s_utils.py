from automation_infra.utils.waiter import wait_for_predicate


def create_deployment_with_replicas(host, name, docker_image, amount_of_replicas):
    wait_for_predicate(lambda: host.K8s.create_deployment(name, docker_image), timeout=120)
    host.K8s.scale_deployment(name, int(amount_of_replicas))
    host.K8s.expose_deployment(name)
