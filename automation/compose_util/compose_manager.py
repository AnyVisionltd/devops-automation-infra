import logging


class ComposeManager:
    @staticmethod
    def pull_and_up(host, remote_compose_yaml_path):
        host.Docker.login()
        host.DockerCompose.compose_down(remote_compose_yaml_path)
        try:
            host.DockerCompose.compose_pull(remote_compose_yaml_path)
            host.DockerCompose.compose_up(remote_compose_yaml_path)
        except Exception as e:
            logging.exception(f"Failed to run compose")
            raise e
