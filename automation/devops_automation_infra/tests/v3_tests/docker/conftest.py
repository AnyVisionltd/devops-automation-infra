import gossip

# import ssh and docker "installers" so that the handlers will be registered
from devops_automation_infra.installers import ssh
from devops_automation_infra.installers import docker


# This is a way to populate all tests in a folder with a specific installer if installer is not specified:
def pytest_fixture_setup(request):
    installer = getattr(request.module, "installer", None)
    if not installer:
        request.module.installer = "docker"


# An example handler - will run if triggered by someone in pytest_runtest_setup
@gossip.register("runtest_setup")
def setup_handler():
    pass
