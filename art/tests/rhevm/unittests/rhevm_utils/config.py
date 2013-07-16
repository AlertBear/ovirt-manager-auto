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
