"""
Download image via sdk instead of directly using a tool or downloading the
image from the host itself.
https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
Storage_4_0/4_1_Storage_Upload_Disk_Image_Through_REST_AP
"""

import config
import pytest
from art.test_handler.tools import polarion

from art.unittest_lib import (
    tier1,
)

from art.unittest_lib import StorageTest as TestCase, testflow
from rhevmtests.storage.fixtures import (
    delete_disks,
)
from rhevmtests.storage.fixtures import remove_vm  # noqa
from fixtures import copy_images_for_upload  # noqa
from rhevmtests.storage.storage_streaming_api.fixtures import (  # noqa
    create_certificate_for_test  # noqa
)  # noqa
from fixtures import (
    add_disks_for_upload, initialize_variables,
)
from art.rhevm_api.tests_lib.low_level import (
    streaming_api as ll_sapi,
)


@pytest.mark.usefixtures(
    initialize_variables.__name__,
    delete_disks.__name__,
    add_disks_for_upload.__name__,
)
class TestCase17322(TestCase):
    """
    Upload images - upload disks matrix

    1. Upload disk images (raw,qcow2_v3,qcow2_v3) from localhost
    2. Verify data correctness via md5sum of original and uploaded images

    """

    polarion_test_case = '17322'

    @polarion("RHEVM3-17322")
    @tier1
    def test_disks_matrix_uploads(self, storage):
        sapi_obj = ll_sapi.StreamingApi(
            config.TARGET_FILE_PATH, config.IMAGE_FULL_SIZE, config.UPLOAD)
        testflow.step("Check md5sums and sizes of disks %s pre upload", (
                self.disks_names
        ))
        md5sums_before, sizes_before = sapi_obj.md5sums_sizes_before_transfer()
        testflow.step(
            "Starting parallel upload of disks %s", self.disks_names
        )
        sapi_obj.transfer_multiple_disks(
            self.disks_names, sizes_before
        )

        testflow.step("Comparing md5sum before and after download")
        for index in range(len(self.disks_names)):
            sapi_obj.compare_md5sum_before_after_transfer(
                md5sums_before[index], host=self.spm_host, sp_id=self.sp_id,
                storage_type=storage, disk_id=self.disks_ids[index],
            )
