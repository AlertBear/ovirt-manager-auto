# -*- coding: utf-8 -*-

"""
Pytest conftest for sla tests
"""

import pytest


@pytest.fixture(scope="session", autouse=True)
def prepare_env_sla(request):
    """
    Run setup inventory
    """
    pytest.config.hook.pytest_rhv_setup(team="sla")
