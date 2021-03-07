
def add_cmdline_options(parser):
    parser.addoption("--skip-docker-setup", action="store_true", default=False,
                     help="skip down, pull and up to containers, "
                          "only do pretest setup")
    parser.addoption("--skip-docker-down", action="store_true", default=True,
                     help="skip down at installer fixture session end")
    parser.addoption("--services", action="store", default="",
                     help="Services to change image. sperate with comma eg. pipeng,camera-service")
    parser.addoption("--tag", action="store", default="", help="image tag to use in spesified services")
    parser.addoption("--yaml-file", action="store", default="docker-compose-devops.yml",
                     help="yaml file to pull and up")
    parser.addoption("--sync-time", type=bool, default=False,
                     help="sync time between host running test to remote running tests")
    parser.addoption("--hostmode", action='store_true', default=False, help="run compose in host mode")
