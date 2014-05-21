import sys

from rhevm_utils import base
from unittest_conf import REST_API_PASS, ISO_UP_CONF, ISO_DOMAIN_NAME
from utilities.rhevm_tools.iso_uploader import ISOUploadUtility
from art.test_handler.tools import tcms
ISO_UPLOADER_TEST_PLAN = 3741
NAME = 'iso-uploader'

DUMMY_ISO_FILE_PATTERN = '/tmp/%s.iso'
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
    current_iso_file = None

    def setUp(self):
        super(ISOUploaderTestCase, self).setUp()
        assert self.ut.setRestConnPassword(NAME, ISO_UP_CONF, REST_API_PASS)

    def tearDown(self):
        if self.current_iso_file:
            self.ut.setup.removeFile(self.current_iso_file)
            self.current_iso_file = None
        super(ISOUploaderTestCase, self).tearDown()

    @tcms(ISO_UPLOADER_TEST_PLAN, 275523)
    def test_iso_uploader_upload(self):
        """ iso_uploder_upload """
        isoFile = DUMMY_ISO_FILE_PATTERN % sys._getframe().f_code.co_name
        self.ut.createDummyIsoFile(isoFile)
        self.current_iso_file = isoFile
        self.ut(ISO_UPLOAD_COMMAND, isoFile, i=ISO_DOMAIN_NAME)
        self.ut.autoTest()

    @tcms(ISO_UPLOADER_TEST_PLAN, 97800)
    def test_iso_uploader_list(self):
        """ iso_uploder_list """
        self.ut('list')
        self.ut.autoTest()
