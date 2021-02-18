import pytest


def pytest_addoption(parser):
    group = parser.getgroup("pytest_devops_infra")
    group.addoption("--install", action="store_true",
                    help="trigger installation of anyvision product or skip this step")


@pytest.hookimpl(tryfirst=True)
def pytest_after_base_config(base_config, request):
    # TODO: define and call hook to allow enriching types of installers
    installers = dict()
    import pdb; pdb.set_trace()
    install = request.config.option.install
    # TODO: maybe this is wrong to iterate over hosts, rather we should iterate over clusters...
    # if I iterate over clusters then I need to handle the case of a docker machine which doesnt have grouping defined
    for name, host in base_config.hosts.items():
        host_reqs = request.session.items[0].function.__hardware_reqs[name]
        installer = host_reqs['installer']

        # TODO: send host to relevant after_base_config for initting depending on the type it is
        # TODO: if not installing there is still some setup I would like to do such as deploy proxy container.
        #  Anything else?

        pass
    # TODO: invoke after pytest_devops_infra for core_product or whoever else would like to run code


@pytest.hookimpl(tryfirst=True)
def pytest_clean_between_tests(host, item):
    # TODO: send host to relevant cleaner depending on type
    pass


def pytest_download_logs(host, dest_dir):
    # TODO: implement download acc to type
    pass
