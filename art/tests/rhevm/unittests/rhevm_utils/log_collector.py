from rhevm_utils.base import RHEVMUtilsTestCase
from utilities.rhevm_tools.log_collector import  LogCollectorUtility

NAME = 'log-collector'


class LogCollectorTestCase(RHEVMUtilsTestCase):

    __test__ = False # FIXME: change to True, when you implement this
    utility = NAME
    utility_class = LogCollectorUtility
    _multiprocess_can_split_ = True

