from pluggy import HookspecMarker

hookspec = HookspecMarker("pytest")


def pytest_after_proxy_container(base_config, request):
    """
    Called after proxy container is running and connected to.
    """