from integration.rhevm_utils import base
from utilities.rhevm_tools.config import ConfigUtility
from art.test_handler.tools import polarion  # pylint: disable=E0611
from art.unittest_lib import attr

CONFIG_TEST_PLAN = 3727
NAME = 'config'


@attr(tier=0)
class ConfigTestCase(base.RHEVMUtilsTestCase):

    __test__ = True  # FIXME: change to True, when you implement this
    utility = NAME
    utility_class = ConfigUtility
    _multiprocess_can_split_ = True

    @polarion("RHEVM3-7664")
    def test_config_list_long(self):
        """
        config list long option
        """
        self.ut('--list')
        self.ut.autoTest()
        self.ut('-l')
        self.ut.autoTest()

    @polarion("RHEVM3-7663")
    def test_config_get(self):
        """
        rhevm-config --get
        """

        self.ut(get='SSLEnabled')
        self.ut.autoTest()

        # should return 1 when trying to get missing property
        self.ut(get='SomeWeirdProperty', rc=1)
        self.ut.autoTest()

        self.ut(get='LocalAdminPassword')
        self.ut.autoTest()

    def test_config_set(self):
        """
        rhevm-config --set
        """
        self.ut(set='SSLEnabled=false')
        # set it to known value
        current = self.ut.getValue('SSLEnabled')
        self.ut.autoTest()
        self.assertEqual(current, 'false')

        self.ut(set='SSLEnabled=true')
        # change value
        current = self.ut.getValue('SSLEnabled')
        self.ut.autoTest()
        self.assertEqual(current, 'true')

        self.ut(set='SSLEnabled=true')
        # try if it works when new value is same as old
        current = self.ut.getValue('SSLEnabled')
        self.ut.autoTest()
        self.assertEqual(current, 'true')

    def test_config_all(self):
        """
        rhevm-config --all
        """
        self.ut(all=None)
        self.ut.autoTest()
