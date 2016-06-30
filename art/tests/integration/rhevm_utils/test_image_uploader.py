from art.rhevm_api.tests_lib.low_level import storagedomains as ll_sds
from art.rhevm_api.tests_lib.high_level import storagedomains as hl_sds
from art.test_handler.tools import polarion
from art.unittest_lib import attr
from rhevm_utils import base, unittest_conf
from utilities.rhevm_tools.image_uploader import ImageUploadUtility


IMAGE_UPLOADER_TEST_PLAN = 5200
NAME = 'image-uploader'

IMAGE_UPLOAD_FILE_PATH = ('/opt/art/shared_data/image_uploader_test/'
                          'img_up_test.ova')
DUMMY_IMAGE = '/tmp/dummy.ovf'
IMAGE_UPLOAD_COMMAND = 'upload'


def setup_module():
    if unittest_conf.GOLDEN_ENV:
        export_domain = ll_sds.findExportStorageDomains()[0]
        ll_sds.attachStorageDomain(
            True, unittest_conf.DC_NAME, export_domain
        )
    else:
        base.setup_module()


def teardown_module():
    if unittest_conf.GOLDEN_ENV:
        export_domain = ll_sds.findExportStorageDomains()[0]
        hl_sds.detach_and_deactivate_domain(
            unittest_conf.DC_NAME, export_domain
        )
    else:
        base.teardown_module()


@attr(tier=2)
class ImageUploaderTestCase(base.RHEVMUtilsTestCase):
    """
        rhevm image uploder test cases
    """
    __test__ = True
    utility = NAME
    utility_class = ImageUploadUtility
    _multiprocess_can_split_ = True

    @polarion("RHEVM3-7470")
    def test_image_uploader_upload(self):
        """ image_uploader_upload """
        assert self.ut.setRestConnPassword(NAME, unittest_conf.IMAGE_UP_CONF,
                                           unittest_conf.VDC_PASSWORD)
        self.ut(IMAGE_UPLOAD_COMMAND, IMAGE_UPLOAD_FILE_PATH,
                e=unittest_conf.EXPORT_DOMAIN_NAME)
        self.ut.autoTest()

    @polarion("RHEVM3-7487")
    def test_image_uploader_list(self):
        """ image_uploader_list """
        assert self.ut.setRestConnPassword(NAME, unittest_conf.IMAGE_UP_CONF,
                                           unittest_conf.VDC_PASSWORD)
        self.ut('list')
        self.ut.autoTest()

    @polarion("RHEVM3-7475")
    def test_image_uploader_upload_twice(self):
        """ image_uploader_upload_twice """
        assert self.ut.setRestConnPassword(NAME, unittest_conf.IMAGE_UP_CONF,
                                           unittest_conf.VDC_PASSWORD)
        self.ut(IMAGE_UPLOAD_COMMAND, IMAGE_UPLOAD_FILE_PATH,
                e=unittest_conf.EXPORT_DOMAIN_NAME)
        self.ut.autoTest()
        self.ut(IMAGE_UPLOAD_COMMAND, IMAGE_UPLOAD_FILE_PATH,
                e=unittest_conf.EXPORT_DOMAIN_NAME)
        self.ut.autoTest()

    @polarion("RHEVM3-7476")
    def test_image_uploader_upload_ovf_id(self):
        """ image_uploader_upload_twice_ovf_id """
        assert self.ut.setRestConnPassword(NAME, unittest_conf.IMAGE_UP_CONF,
                                           unittest_conf.VDC_PASSWORD)
        self.ut(IMAGE_UPLOAD_COMMAND, IMAGE_UPLOAD_FILE_PATH,
                e=unittest_conf.EXPORT_DOMAIN_NAME, ovf_id=None)
        self.ut.autoTest()
        self.ut(IMAGE_UPLOAD_COMMAND, IMAGE_UPLOAD_FILE_PATH,
                e=unittest_conf.EXPORT_DOMAIN_NAME, ovf_id=None)
        # TODO there should be non-zero return code - BZ 1104661
        self.ut.autoTest()
        assert 'exists on' in self.ut.err

    @polarion("RHEVM3-7471")
    def test_image_uploader_upload_bad_file(self):
        """ image_uploader_upload_bad_file """
        assert self.ut.setRestConnPassword(NAME, unittest_conf.IMAGE_UP_CONF,
                                           unittest_conf.VDC_PASSWORD)
        self.ut.createDummyImageFile(DUMMY_IMAGE)
        self.ut(IMAGE_UPLOAD_COMMAND, DUMMY_IMAGE,
                e=unittest_conf.EXPORT_DOMAIN_NAME)
        self.ut.setup.removeFile(DUMMY_IMAGE)
        self.ut.autoTest(rc=1)
        assert 'not a gzip' in self.ut.err

    @polarion("RHEVM3-7484")
    def test_image_uploader_upload_rename(self):
        """ image_uploader_upload_rename """
        assert self.ut.setRestConnPassword(NAME, unittest_conf.IMAGE_UP_CONF,
                                           unittest_conf.VDC_PASSWORD)
        self.ut(IMAGE_UPLOAD_COMMAND, IMAGE_UPLOAD_FILE_PATH,
                e=unittest_conf.EXPORT_DOMAIN_NAME, name='renamed')
        self.ut.autoTest()

    @polarion("RHEVM3-7479")
    def test_image_uploader_upload_wrong_domain(self):
        """ image_uploader_wrong_domain """
        assert self.ut.setRestConnPassword(NAME, unittest_conf.IMAGE_UP_CONF,
                                           unittest_conf.VDC_PASSWORD)
        self.ut(IMAGE_UPLOAD_COMMAND, IMAGE_UPLOAD_FILE_PATH,
                e='nonsense')
        self.ut.autoTest(rc=1)
        assert 'was not found' in self.ut.err

    @polarion("RHEVM3-7480")
    def test_image_uploader_upload_inactive(self):
        """ image_uploader_upload_inactive """
        assert self.ut.setRestConnPassword(NAME, unittest_conf.IMAGE_UP_CONF,
                                           unittest_conf.VDC_PASSWORD)
        ll_sds.deactivateStorageDomain(
            True, unittest_conf.DC_NAME, unittest_conf.EXPORT_DOMAIN_NAME
        )
        try:
            self.ut(IMAGE_UPLOAD_COMMAND, IMAGE_UPLOAD_FILE_PATH,
                    e=unittest_conf.EXPORT_DOMAIN_NAME, ovf_id=None)
            self.ut.autoTest()
        finally:
            ll_sds.activateStorageDomain(
                True, unittest_conf.DC_NAME, unittest_conf.EXPORT_DOMAIN_NAME
            )
