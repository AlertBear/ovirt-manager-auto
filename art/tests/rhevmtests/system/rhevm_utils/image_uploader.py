from rhevm_utils import base
from unittest_conf import (
    REST_API_PASS, IMAGE_UP_CONF, EXPORT_DOMAIN_NAME, DC_NAME)
from art.unittest_lib import attr
from utilities.rhevm_tools.image_uploader import ImageUploadUtility
from art.rhevm_api.tests_lib.low_level.storagedomains import (
    activateStorageDomain, deactivateStorageDomain)
from art.test_handler.tools import tcms


IMAGE_UPLOADER_TEST_PLAN = 5200
NAME = 'image-uploader'

IMAGE_UPLOAD_FILE_PATH = ('/opt/art/shared_data/image_uploader_test/'
                          'img_up_test.ovf')
DUMMY_IMAGE = '/tmp/dummy.ovf'
IMAGE_UPLOAD_COMMAND = 'upload'


def setup_module():
    base.setup_module()


def teardown_module():
    base.teardown_module()


@attr(tier=1)
class ImageUploaderTestCase(base.RHEVMUtilsTestCase):
    """
        rhevm image uploder test cases
    """
    __test__ = True
    utility = NAME
    utility_class = ImageUploadUtility
    _multiprocess_can_split_ = True

    @tcms(IMAGE_UPLOADER_TEST_PLAN, 287464)
    def test_image_uploader_upload(self):
        """ image_uploader_upload """
        assert self.ut.setRestConnPassword(NAME, IMAGE_UP_CONF, REST_API_PASS)
        self.ut(IMAGE_UPLOAD_COMMAND, IMAGE_UPLOAD_FILE_PATH,
                e=EXPORT_DOMAIN_NAME)
        self.ut.autoTest()

    @tcms(IMAGE_UPLOADER_TEST_PLAN, 287465)
    def test_image_uploader_list(self):
        """ image_uploader_list """
        assert self.ut.setRestConnPassword(NAME, IMAGE_UP_CONF, REST_API_PASS)
        self.ut('list')
        self.ut.autoTest()

    @tcms(IMAGE_UPLOADER_TEST_PLAN, 129374)
    def test_image_uploader_upload_twice(self):
        """ image_uploader_upload_twice """
        assert self.ut.setRestConnPassword(NAME, IMAGE_UP_CONF, REST_API_PASS)
        self.ut(IMAGE_UPLOAD_COMMAND, IMAGE_UPLOAD_FILE_PATH,
                e=EXPORT_DOMAIN_NAME)
        self.ut.autoTest()
        self.ut(IMAGE_UPLOAD_COMMAND, IMAGE_UPLOAD_FILE_PATH,
                e=EXPORT_DOMAIN_NAME)
        self.ut.autoTest()

    @tcms(IMAGE_UPLOADER_TEST_PLAN, 129373)
    def test_image_uploader_upload_ovf_id(self):
        """ image_uploader_upload_twice_ovf_id """
        assert self.ut.setRestConnPassword(NAME, IMAGE_UP_CONF, REST_API_PASS)
        self.ut(IMAGE_UPLOAD_COMMAND, IMAGE_UPLOAD_FILE_PATH,
                e=EXPORT_DOMAIN_NAME, ovf_id=None)
        self.ut.autoTest()
        self.ut(IMAGE_UPLOAD_COMMAND, IMAGE_UPLOAD_FILE_PATH,
                e=EXPORT_DOMAIN_NAME, ovf_id=None)
        # TODO there should be non-zero return code - BZ 1104661
        self.ut.autoTest()
        assert 'exists on' in self.ut.err

    @tcms(IMAGE_UPLOADER_TEST_PLAN, 129468)
    def test_image_uploader_upload_bad_file(self):
        """ image_uploader_upload_bad_file """
        assert self.ut.setRestConnPassword(NAME, IMAGE_UP_CONF, REST_API_PASS)
        self.ut.createDummyImageFile(DUMMY_IMAGE)
        self.ut(IMAGE_UPLOAD_COMMAND, DUMMY_IMAGE, e=EXPORT_DOMAIN_NAME)
        self.ut.setup.removeFile(DUMMY_IMAGE)
        self.ut.autoTest(rc=1)
        assert 'not a gzip' in self.ut.err

    @tcms(IMAGE_UPLOADER_TEST_PLAN, 129365)
    def test_image_uploader_upload_rename(self):
        """ image_uploader_upload_rename """
        assert self.ut.setRestConnPassword(NAME, IMAGE_UP_CONF, REST_API_PASS)
        self.ut(IMAGE_UPLOAD_COMMAND, IMAGE_UPLOAD_FILE_PATH,
                e=EXPORT_DOMAIN_NAME, name='renamed')
        self.ut.autoTest()

    @tcms(IMAGE_UPLOADER_TEST_PLAN, 129370)
    def test_image_uploader_upload_wrong_domain(self):
        """ image_uploader_wrong_domain """
        assert self.ut.setRestConnPassword(NAME, IMAGE_UP_CONF, REST_API_PASS)
        self.ut(IMAGE_UPLOAD_COMMAND, IMAGE_UPLOAD_FILE_PATH,
                e='nonsense')
        self.ut.autoTest(rc=1)
        assert 'was not found' in self.ut.err

    @tcms(IMAGE_UPLOADER_TEST_PLAN, 129369)
    def test_image_uploader_upload_inactive(self):
        """ image_uploader_upload_inactive """
        assert self.ut.setRestConnPassword(NAME, IMAGE_UP_CONF, REST_API_PASS)
        deactivateStorageDomain(True, DC_NAME, EXPORT_DOMAIN_NAME)
        try:
            self.ut(IMAGE_UPLOAD_COMMAND, IMAGE_UPLOAD_FILE_PATH,
                    e=EXPORT_DOMAIN_NAME, ovf_id=None)
            self.ut.autoTest()
        finally:
            activateStorageDomain(True, DC_NAME, EXPORT_DOMAIN_NAME)
