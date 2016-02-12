"""
This module defines new ART related hooks. See doc string relevant hook.
"""


def pytest_artconf_ready(config):
    """
    Called once ART_CONFIG is ready to use.
    You can access ART config as config.ART_CONFIG.

    :param config: pytest config
    """


def pytest_art_ensure_resources(config):
    """
    Suitable in case you need to ensure any resource for ART's test
    """


def pytest_art_release_resources(config):
    """
    It is reverse hook to pytest_art_ensure_resources.
    """


def pytest_package_setup(entry):
    """
    It gets executed just before package_setup function.

    :param entry: reference to package
    :type entry: instance of package_fixtures.Entry
    """


def pytest_package_teardown(entry):
    """
    It gets executed just after package_teardown function.

    :param entry: reference to package
    :type entry: instance of package_fixtures.Entry
    """
