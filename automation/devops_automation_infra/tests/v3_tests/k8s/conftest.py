import gossip

# import ssh and docker "installers" so that the handlers will be registered
from devops_automation_infra.installers import ssh
from devops_automation_infra.installers import docker

from compose_util import compose_options


def pytest_addoption(parser):
    compose_options.add_cmdline_options(parser)

# An example handler - will run if triggered by someone in pytest_runtest_setup
@gossip.register("runtest_setup")
def setup_handler():
    pass
