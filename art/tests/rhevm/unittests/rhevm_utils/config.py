from rhevm_utils.base import RHEVMUtilsTestCase, istest
from utilities.rhevm_tools.config import ConfigUtility
from utilities.rhevm_tools import errors
from art.test_handler.tools import tcms

CONFIG_TEST_PLAN = 3727
NAME = 'config'


class ConfigTestCase(RHEVMUtilsTestCase):

    __test__ = True # FIXME: change to True, when you implement this
    utility = NAME
    utility_class = ConfigUtility
    _multiprocess_can_split_ = True

    @istest
    @tcms(CONFIG_TEST_PLAN, 86796)
    def configListLong(self):
        """
        config list long option
        """
        failed = False
        self.ut('--list')
        try:
            self.ut.autoTest()
        except (errors.ConfigUtilityError, errors.OutputVerificationError) as ex:
            failed = True
        self.ut('-l')
        try:
            self.ut.autoTest()
        except (errors.ConfigUtilityError, errors.OutputVerificationError) as ex:
            failed = True
        if failed:
            raise ex

    @istest
    @tcms(CONFIG_TEST_PLAN, 86797)
    def configGet(self):
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

        self.ut(get='SomeWeirdProperty', rc=1) # should return 1 when trying to get missing property
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

    @istest
    def configSet(self):
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

    @istest
    def configAll(self):
        """
        rhevm-config --all
        """
        self.ut(all=None)
        self.ut.autoTest()
