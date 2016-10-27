"""
Test actions of all user roles positive & negative.
"""
import pytest
from rhevmtests.system.user_tests import test_actions


@pytest.fixture(autouse=True, scope="module")
def setup_module(request):
    test_actions.setup_module(request)
