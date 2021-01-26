import yaml


class ComposeEditor(object):

    def __init__(self, compose):
        self.compose = compose

    @classmethod
    def from_file(cls, file_path):
        with open(file_path, "r") as file:
            yaml_content = yaml.safe_load(file)
            return cls(yaml_content)

    def update_service(self, service_name, key, value):
        self.compose['services'][service_name][key] = value

    def service_key(self, service_name, key):
        return self.compose['services'][service_name][key]

    def service_image(self, service_name):
        image_path = self.service_key(service_name, 'image').split(':')
        image_dict = {
            "name": image_path[0],
            "version": image_path[1]
        }
        return image_dict

    def dumps(self, stream=None):
        return yaml.dump(self.compose, stream, default_flow_style=False)

