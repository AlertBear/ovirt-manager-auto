from rhevm_utils.base import RHEVMUtilsTestCase
from utilities.rhevm_tools.upgrade import UpgradeUtility

NAME = 'upgrade'


class UpgradeTestCase(RHEVMUtilsTestCase):

    __test__ = False  # FIXME: change to True, when you implement this
    utility = NAME
    utility_class = UpgradeUtility
    _multiprocess_can_split_ = True
