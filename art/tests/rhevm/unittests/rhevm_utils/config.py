from rhevm_utils.base import RHEVMUtilsTestCase
from utilities.rhevm_tools.config import ConfigUtility

NAME = 'config'


class ConfigTestCase(RHEVMUtilsTestCase):

    __test__ = False # FIXME: change to True, when you implement this
    utility = NAME
    utility_class = ConfigUtility
    _multiprocess_can_split_ = True

