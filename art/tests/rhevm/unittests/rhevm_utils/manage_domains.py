from rhevm_utils.base import RHEVMUtilsTestCase
from utilities.rhevm_tools.manage_domains import ManageDomainsUtility

NAME = 'manage-domains'


class ManageDomainsTestCase(RHEVMUtilsTestCase):

    __test__ = False # FIXME: change to True, when you implement this
    utility = NAME
    utility_class = ManageDomainsUtility
    _multiprocess_can_split_ = True

