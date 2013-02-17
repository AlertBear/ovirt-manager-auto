from rhevm_utils.base import RHEVMUtilsTestCase
from utilities.rhevm_tools.iso_uploader import ISOUploadUtility

NAME = 'iso-uploader'


class ISOUploaderTestCase(RHEVMUtilsTestCase):

    __test__ = False # FIXME: change to True, when you implement this
    utility = NAME
    utility_class = ISOUploadUtility
    _multiprocess_can_split_ = True


