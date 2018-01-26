import pytest

from .helpers import WelcomePage


@pytest.fixture(scope='class')
def welcome_page():
    """
    Class fixture for the welcome page crawler.

    Returns:
        (helpers.WelcomePage) welcome page cawler instance
    """
    return WelcomePage()
