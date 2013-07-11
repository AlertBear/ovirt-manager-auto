from rhevm_utils.base import RHEVMUtilsTestCase, istest, logger, \
    REST_API_PASS, IMAGE_UP_CONF, EXPORT_DOMAIN_NAME
from utilities.rhevm_tools.image_uploader import ImageUploadUtility
from art.test_handler.tools import tcms
IMAGE_UPLOADER_TEST_PLAN = 5200
NAME = 'image-uploader'

IMAGE_UPLOAD_FILE_PATH = '/opt/art/shared_data/image_uploader_test/img_up_test.ovf'
IMAGE_UPLOAD_COMMAND = 'upload'

class ImageUploaderTestCase(RHEVMUtilsTestCase):
    """
        rhevm image uploder test cases
    """
    __test__ = True
    utility = NAME
    utility_class = ImageUploadUtility
    _multiprocess_can_split_ = True

    @istest
    @tcms(IMAGE_UPLOADER_TEST_PLAN, 287464)
    def imageUploderUpload(self):
        """ image_uploder_upload """
        assert self.ut.setRestConnPassword(NAME, IMAGE_UP_CONF, REST_API_PASS)
        self.ut(IMAGE_UPLOAD_COMMAND, IMAGE_UPLOAD_FILE_PATH,
              e=EXPORT_DOMAIN_NAME)
        self.ut.autoTest()

    @istest
    @tcms(IMAGE_UPLOADER_TEST_PLAN, 287465)
    def imageUploderList(self):
        """ image_uploder_list """
        assert self.ut.setRestConnPassword(NAME, IMAGE_UP_CONF, REST_API_PASS)
        self.ut('list')
        self.ut.autoTest()


