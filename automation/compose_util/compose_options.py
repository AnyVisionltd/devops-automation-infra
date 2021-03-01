
def add_cmdline_options(parser):
    group = parser.getgroup("compose_options")
    group.addoption("--skip-docker-setup", action="store_true", default=False,
                     help="skip down, pull and up to containers, "
                          "only do pretest setup")
    group.addoption("--skip-docker-down", action="store_true", default=True,
                     help="skip down at installer fixture session end")
    group.addoption("--services", action="store", default="",
                     help="Services to change image. sperate with comma eg. pipeng,camera-service")
    group.addoption("--tag", action="store", default="", help="image tag to use in spesified services")
    group.addoption("--yaml-file", action="store", default="docker-compose-core-gpu.yml",
                     help="yaml file to pull and up")
    group.addoption("--sync-time", type=bool, default=False,
                     help="sync time between host running test to remote running tests")
    group.addoption("--hostmode", action='store_true', default=False, help="run compose in host mode")
