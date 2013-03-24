from rhevm_utils.base import RHEVMUtilsTestCase, istest, logger, \
    REST_API_PASS, ISO_UP_CONF
from utilities.rhevm_tools.iso_uploader import ISOUploadUtility

NAME = 'iso-uploader'


class ISOUploaderTestCase(RHEVMUtilsTestCase):
    """
        rhevm iso uploder test cases
    """
    __test__ = True
    utility = NAME
    utility_class = ISOUploadUtility
    _multiprocess_can_split_ = True

    @istest
    def isoUploderList(self):
        """ iso_uploder_list """
        assert self.ut.setRestConnPassword(NAME, ISO_UP_CONF, REST_API_PASS)
        self.ut('list')
        self.ut.autoTest()


