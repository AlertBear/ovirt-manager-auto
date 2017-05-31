"""
Test actions of all admin roles positive & negative.
"""
import pytest
from rhevmtests.coresystem.user_tests import base


@pytest.fixture(autouse=True, scope="module")
def setup_module(request):
    base.setup_module(request)
