import pytest
import logging

from art.test_handler.tools import polarion
from art.unittest_lib import (
    CoreSystemTest,
    testflow,
    tier1,
)
import unittest_conf as conf

logger = logging.getLogger(__name__)


@pytest.fixture
def enable_ssl(request):
    def fin():
        testflow.teardown("Setting SSLEnabled = true")
        conf.ENGINE.engine_config(action='set', param="SSLEnabled=true")

    request.addfinalizer(fin)


@tier1
class TestConfigTestCase(CoreSystemTest):
    ssl_enabled = "SSLEnabled"
    wrong_property = "SomeWeirdProperty"

    @polarion("RHEVM3-7664")
    def test_config_list_long(self):
        """
        config list long option
        """

        testflow.step("Checking if list action works well.")
        assert conf.ENGINE.engine_config(action='list')['results']

    @polarion("RHEVM3-7663")
    def test_config_get(self):
        """
        rhevm-config --get
        """

        testflow.step(
            "Checking if '%s' property exists and has default value.",
            self.ssl_enabled
        )
        res = conf.ENGINE.engine_config(
            action='get', param=self.ssl_enabled
        )
        assert res['results'][self.ssl_enabled]['value'] == 'true'

        testflow.step("Checking if wrong property doesn't exist.")
        res = conf.ENGINE.engine_config(
            action='get', param=self.wrong_property
        )
        assert res['results'] is False

    @pytest.mark.usefixtures(enable_ssl.__name__)
    @polarion("RHEVM3-7661")
    def test_config_set(self):
        """
        rhevm-config --set
        """

        testflow.step("Changing '%s' property's value.", self.ssl_enabled)
        assert conf.ENGINE.engine_config(
            action='set', param="{}=false".format(self.ssl_enabled)
        )['results']

        testflow.step(
            "Checking if '%s' property's value has been changed.",
            self.ssl_enabled
        )
        res = conf.ENGINE.engine_config(
            'get', [self.ssl_enabled]
        )
        assert res['results'][self.ssl_enabled]['value'] == 'false'

    @polarion("RHEVM3-7662")
    def test_config_all(self):
        """
        rhevm-config --all
        """

        testflow.step("Checking if get all properties action works.")
        assert conf.ENGINE.engine_config(action='all')['results']
