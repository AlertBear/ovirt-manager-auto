from rhevm_utils import base
from unittest_conf import REST_API_PASS, ISO_UP_CONF, ISO_DOMAIN_NAME
from utilities.rhevm_tools.iso_uploader import ISOUploadUtility
from art.test_handler.tools import tcms
ISO_UPLOADER_TEST_PLAN = 3741
NAME = 'iso-uploader'

ISO_UPLOAD_DUMMY_FILE_PATH = '/tmp/test_iso.iso'
ISO_UPLOAD_COMMAND = 'upload'


def setup_module():
    base.setup_module()


def teardown_module():
    base.teardown_module()


class ISOUploaderTestCase(base.RHEVMUtilsTestCase):
    """
        rhevm iso uploder test cases
    """
    __test__ = True
    utility = NAME
    utility_class = ISOUploadUtility
    _multiprocess_can_split_ = True

    @tcms(ISO_UPLOADER_TEST_PLAN, 275523)
    def test_iso_uloder_upload(self):
        """ iso_uploder_upload """
        assert self.ut.setRestConnPassword(NAME, ISO_UP_CONF, REST_API_PASS)
        self.ut.createDummyIsoFile(ISO_UPLOAD_DUMMY_FILE_PATH)
        self.ut(ISO_UPLOAD_COMMAND, ISO_UPLOAD_DUMMY_FILE_PATH,
                i=ISO_DOMAIN_NAME)
        self.ut.autoTest()

    @tcms(ISO_UPLOADER_TEST_PLAN, 97800)
    def test_iso_uploder_list(self):
        """ iso_uploder_list """
        assert self.ut.setRestConnPassword(NAME, ISO_UP_CONF, REST_API_PASS)
        self.ut('list')
        self.ut.autoTest()
