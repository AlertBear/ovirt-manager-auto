from rhevmtests.system.rhevm_utils import base
from utilities.rhevm_tools.config import ConfigUtility
from utilities.rhevm_tools import errors
from art.test_handler.tools import tcms
from art.unittest_lib import attr

CONFIG_TEST_PLAN = 3727
NAME = 'config'


@attr(tier=0)
class ConfigTestCase(base.RHEVMUtilsTestCase):

    __test__ = True  # FIXME: change to True, when you implement this
    utility = NAME
    utility_class = ConfigUtility
    _multiprocess_can_split_ = True

    @tcms(CONFIG_TEST_PLAN, 86796)
    def test_config_list_long(self):
        """
        config list long option
        """
        failed = False
        self.ut('--list')
        try:
            self.ut.autoTest()
        except (errors.ConfigUtilityError,
                errors.OutputVerificationError) as ex:
            failed = True
        self.ut('-l')
        try:
            self.ut.autoTest()
        except (errors.ConfigUtilityError,
                errors.OutputVerificationError) as ex:
            failed = True
        if failed:
            raise ex

    @tcms(CONFIG_TEST_PLAN, 86797)
    def test_config_get(self):
        """
        rhevm-config --get
        """
        failed = False
        exceptions = []

        self.ut(get='SSLEnabled')
        try:
            self.ut.autoTest()
        except (errors.MissingPropertyFile, errors.OptionIsNotAllowed,
                errors.FetchOptionError, errors.OutputVerificationError) as ex:
                failed = True
                exceptions.append(ex)

        # should return 1 when trying to get missing property
        self.ut(get='SomeWeirdProperty', rc=1)
        try:
            self.ut.autoTest()
        except (errors.MissingPropertyFile, errors.OptionIsNotAllowed,
                errors.FetchOptionError, errors.OutputVerificationError) as ex:
                failed = True
                exceptions.append(ex)
        self.ut.autoTest()

        self.ut(get='LocalAdminPassword')
        self.ut.autoTest()
        try:
            self.ut.autoTest()
        except (errors.MissingPropertyFile, errors.OptionIsNotAllowed,
                errors.FetchOptionError, errors.OutputVerificationError) as ex:
            failed = True
            exceptions.append(ex)

        if failed:
            raise exceptions

    def test_config_set(self):
        """
        rhevm-config --set
        """
        failed = False
        self.ut(set='SSLEnabled=false')
        # set it to known value
        current = self.ut.getValue('SSLEnabled')
        try:
            self.ut.autoTest()
        except (ValueError, errors.OutputVerificationError,
                errors.FailedToSetValue) as ex:
            failed = True
        assert current == 'false'

        self.ut(set='SSLEnabled=true')
        # change value
        current = self.ut.getValue('SSLEnabled')
        try:
            self.ut.autoTest()
        except (ValueError, errors.OutputVerificationError,
                errors.FailedToSetValue) as ex:
            failed = True
        assert current == 'true'

        self.ut(set='SSLEnabled=true')
        # try if it works when new value is same as old
        current = self.ut.getValue('SSLEnabled')
        try:
            self.ut.autoTest()
        except (ValueError, errors.OutputVerificationError,
                errors.FailedToSetValue) as ex:
            failed = True
        assert current == 'true'

        if failed:
            raise ex

    def test_config_all(self):
        """
        rhevm-config --all
        """
        self.ut(all=None)
        self.ut.autoTest()
