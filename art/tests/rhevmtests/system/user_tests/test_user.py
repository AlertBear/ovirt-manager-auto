"""
Test actions of all user roles positive & negative.
"""
import pytest
from rhevmtests.system.user_tests import base


@pytest.fixture(autouse=True, scope="module")
def setup_module(request):
    base.setup_module(request)
