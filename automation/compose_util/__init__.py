def pytest_addoption(parser):
    """
        If devops automation infra installer or any other installer being called before
        this makes some problems to call the cli option with same name.
        please prefix with core, to arguments related to core services.
    """
    parser.addoption("--skip-docker-setup", action="store_true", default=False,
                     help="skip down, pull and up to containers, "
                          "only do pretest setup")
    parser.addoption("--skip-docker-down", action="store_true", default=True,
                     help="skip down at installer fixture session end")
    parser.addoption("--services", action="store", default="",
                     help="Services to change image. sperate with comma eg. pipeng,camera-service")
    parser.addoption("--services-tag", action="store", default="", help="image tag to use in spesified services")
    parser.addoption("--yaml-file", action="store", default="docker-compose-core-gpu.yml",
                     help="yaml file to pull and up")
    parser.addoption("--sync-time", type=bool, default=False,
                     help="sync time between host running test to remote running tests")
