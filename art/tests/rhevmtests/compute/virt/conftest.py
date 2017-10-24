# -*- coding: utf-8 -*-

"""
Pytest conftest for virt tests
"""

import pytest


@pytest.fixture(scope="session", autouse=True)
def prepare_env_virt(request):
    """
    Run setup inventory
    """
    def fin():
        """
        Run teardown inventory
        """
        pytest.config.hook.pytest_rhv_teardown(team="virt")
    request.addfinalizer(fin)

    pytest.config.hook.pytest_rhv_setup(team="virt")
