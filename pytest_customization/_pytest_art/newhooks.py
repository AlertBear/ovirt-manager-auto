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


def pytest_rhv_setup(team):
    """
    It gets executed at package setup

    :param team: reference to the team that owns the package that is
    going to be executed
    :type team: string
    """


def pytest_rhv_teardown(team):
    """
    It gets executed at package teardown

    :param team: reference to the team that owns the package that was
    executed
    :type team: string
    """
