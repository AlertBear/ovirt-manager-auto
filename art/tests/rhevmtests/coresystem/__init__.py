"""
init for system tests package
"""
import pytest


def teardown_package():
    """
    Run package teardown
    """
    pytest.config.hook.pytest_rhv_teardown(team="coresystem")


def setup_package():
    """
    Run package setup
    """
    pytest.config.hook.pytest_rhv_setup(team="coresystem")
