import sys

from rhevm_utils import base, unittest_conf
import art.rhevm_api.tests_lib.low_level.storagedomains as storagedomains
from art.test_handler.tools import polarion  # pylint: disable=E0611
from art.unittest_lib import attr
from utilities.rhevm_tools.iso_uploader import ISOUploadUtility


ISO_UPLOADER_TEST_PLAN = 3741
NAME = 'iso-uploader'

DUMMY_ISO_FILE_PATTERN = '/tmp/%s.iso'
ISO_UPLOAD_COMMAND = 'upload'


def setup_module():
    if unittest_conf.GOLDEN_ENV:
        iso_domain = storagedomains.findIsoStorageDomains()[1]
        storagedomains.attachStorageDomain(True, unittest_conf.DC_NAME[0],
                                           iso_domain)
    else:
        base.setup_module()


def teardown_module():
    if unittest_conf.GOLDEN_ENV:
        iso_domain = storagedomains.findIsoStorageDomains()[1]
        storagedomains.deactivateStorageDomain(True, unittest_conf.DC_NAME[0],
                                               iso_domain)
        storagedomains.detachStorageDomain(True, unittest_conf.DC_NAME[0],
                                           iso_domain)
    else:
        base.teardown_module()


@attr(tier=2)
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
        assert self.ut.setRestConnPassword(NAME, unittest_conf.ISO_UP_CONF,
                                           unittest_conf.VDC_PASSWORD)

    def tearDown(self):
        if self.current_iso_file:
            self.ut.setup.removeFile(self.current_iso_file)
            self.current_iso_file = None
        super(ISOUploaderTestCase, self).tearDown()

    def setInConfFile(self, option, value):
        """
        Change a row in the config file
        """
        cmd = ['sed', '-i', "'s/#[[:space:]]*%s[[:space:]]*=.*/%s=%s/'" %
               (option, option, value), unittest_conf.ISO_UP_CONF, '--copy']
        self.ut.execute(name=NAME, cmd=cmd)

    @polarion("RHEVM3-7965")
    def test_iso_uploader_upload(self):
        """ iso_uploder_upload """
        isoFile = DUMMY_ISO_FILE_PATTERN % sys._getframe().f_code.co_name
        self.ut.createDummyIsoFile(isoFile)
        self.current_iso_file = isoFile
        if unittest_conf.GOLDEN_ENV:
            self.ut(ISO_UPLOAD_COMMAND, isoFile, force=None,
                    i=unittest_conf.ISO_DOMAIN_NAME)
        else:
            self.ut(ISO_UPLOAD_COMMAND, isoFile,
                    i=unittest_conf.ISO_DOMAIN_NAME)
        self.ut.autoTest()

    @polarion("RHEVM3-7963")
    def test_iso_uploader_list(self):
        """ iso_uploder_list """
        self.ut('list')
        self.ut.autoTest()

    @polarion("RHEVM3-7951")
    def test_iso_uploader_upload_twice(self):
        """ iso_uploder_upload """
        isoFile = DUMMY_ISO_FILE_PATTERN % sys._getframe().f_code.co_name
        self.ut.createDummyIsoFile(isoFile)
        self.current_iso_file = isoFile
        if unittest_conf.GOLDEN_ENV:
            self.ut(ISO_UPLOAD_COMMAND, isoFile, force=None,
                    i=unittest_conf.ISO_DOMAIN_NAME)
        else:
            self.ut(ISO_UPLOAD_COMMAND, isoFile,
                    i=unittest_conf.ISO_DOMAIN_NAME)
        self.ut.autoTest()
        self.ut(ISO_UPLOAD_COMMAND, isoFile, i=unittest_conf.ISO_DOMAIN_NAME)
        self.ut.autoTest(rc=3)

    @polarion("RHEVM3-7964")
    def test_iso_uploader_upload_local(self):
        """ iso_uploder_upload """
        isoFile = DUMMY_ISO_FILE_PATTERN % sys._getframe().f_code.co_name
        self.ut.createDummyIsoFile(isoFile)
        self.current_iso_file = isoFile

        if unittest_conf.GOLDEN_ENV:
            self.ut(ISO_UPLOAD_COMMAND, isoFile, force=None,
                    i=unittest_conf.LOCAL_ISO_DOMAIN_NAME,)
        else:
            self.ut(ISO_UPLOAD_COMMAND, isoFile,
                    i=unittest_conf.LOCAL_ISO_DOMAIN_NAME)
        self.ut.autoTest()

    @polarion("RHEVM3-7960")
    def test_iso_uploader_upload_unatached(self):
        """ iso_uploder_upload """
        isoFile = DUMMY_ISO_FILE_PATTERN % sys._getframe().f_code.co_name
        self.ut.createDummyIsoFile(isoFile)
        self.current_iso_file = isoFile

        if unittest_conf.GOLDEN_ENV:
            self.ut(ISO_UPLOAD_COMMAND, isoFile, force=None,
                    i=unittest_conf.LOCAL_ISO_DOMAIN_NAME)
        else:
            self.ut(ISO_UPLOAD_COMMAND, isoFile,
                    i=unittest_conf.LOCAL_ISO_DOMAIN_NAME)
        self.ut.autoTest()

    @polarion("RHEVM3-7950")
    def test_iso_uploader_help(self):
        """ iso_uploder_help """
        self.ut(ISO_UPLOAD_COMMAND, help=None)
        self.ut.autoTest()

    @polarion("RHEVM3-7952")
    def test_iso_uploader_upload_conf_file(self):
        """ iso_uploder_upload """
        isoFile = DUMMY_ISO_FILE_PATTERN % sys._getframe().f_code.co_name
        self.ut.createDummyIsoFile(isoFile)
        self.current_iso_file = isoFile

        self.setInConfFile('user', 'admin@internal')
        self.setInConfFile('engine', unittest_conf.VDC_HOST + ':443')
        self.setInConfFile('iso-domain', unittest_conf.ISO_DOMAIN_NAME)

        if unittest_conf.GOLDEN_ENV:
            self.ut(ISO_UPLOAD_COMMAND, isoFile, force=None,
                    i=unittest_conf.ISO_DOMAIN_NAME)
        else:
            self.ut(ISO_UPLOAD_COMMAND, isoFile,
                    i=unittest_conf.ISO_DOMAIN_NAME)
        self.ut.autoTest()
