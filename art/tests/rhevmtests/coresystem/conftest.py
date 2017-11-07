# -*- coding: utf-8 -*-

"""
Pytest conftest for CoreSystem tests
"""

import pytest


@pytest.fixture(scope="session", autouse=True)
def prepare_env_coresystem(request):
    """
    Run setup inventory
    """
    pytest.config.hook.pytest_rhv_setup(team="coresystem")
