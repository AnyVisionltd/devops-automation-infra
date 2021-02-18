from pluggy import HookspecMarker

hookspec = HookspecMarker("pytest")


def pytest_register_installer():
    """
    Called after base_config finishes, serves as a method to register installers for infra to call
     to install some type of product on deployed machine (if installation has been requested with --install flag
    """
