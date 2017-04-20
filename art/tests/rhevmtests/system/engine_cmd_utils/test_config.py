import pytest
import logging

from art.test_handler.tools import polarion
from art.unittest_lib import CoreSystemTest, attr
import rhevmtests.system.config as conf

logger = logging.getLogger(__name__)


@pytest.fixture
def set_sslenable_to_true(request):
    def fin():
        logging.info("Setting SSLEnabled = true")
        conf.ENGINE.engine_config(action='set', param="SSLEnabled=true")

    request.addfinalizer(fin)


@attr(tier=1)
class TestConfigTestCase(CoreSystemTest):
    sslenabled = "SSLEnabled"

    @polarion("RHEVM3-7664")
    def test_config_list_long(self):
        """
        config list long option
        """
        assert conf.ENGINE.engine_config(action='list')['results']

    @polarion("RHEVM3-7663")
    def test_config_get(self):
        """
        rhevm-config --get
        """

        res = conf.ENGINE.engine_config(
            action='get', param=self.sslenabled
        )
        assert res['results'][self.sslenabled]['value'] == 'true'

        res = conf.ENGINE.engine_config(
            action='get', param="SomeWeirdProperty"
        )
        assert res['results'] is False

    @pytest.mark.usefixtures(set_sslenable_to_true.__name__)
    @polarion("RHEVM3-7661")
    def test_config_set(self):
        """
        rhevm-config --set
        """

        assert conf.ENGINE.engine_config(
            action='set', param="%s=false" % self.sslenabled
        )['results']

        res = conf.ENGINE.engine_config(
            'get', [self.sslenabled]
        )

        assert res['results'][self.sslenabled]['value'] == 'false'

    @polarion("RHEVM3-7662")
    def test_config_all(self):
        """
        rhevm-config --all
        """
        assert conf.ENGINE.engine_config(action='all')['results']
