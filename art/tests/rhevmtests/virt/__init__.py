import logging
import pytest

logger = logging.getLogger(__name__)


def teardown_package():
    """
    Run package teardown
    """
    pytest.config.hook.pytest_rhv_teardown(team="virt")


def setup_package():
    """
    Run package setup
    """
    pytest.config.hook.pytest_rhv_setup(team="virt")
