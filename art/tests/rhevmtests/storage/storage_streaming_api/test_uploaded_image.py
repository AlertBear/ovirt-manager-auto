"""
Download image via sdk instead of directly using a tool or downloading the
image from the host itself.
https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
Storage_4_0/4_1_Storage_Upload_Disk_Image_Through_REST_AP
"""

import config
import pytest
from art.test_handler.tools import polarion, bz
import rhevmtests.helpers as global_helper

from art.unittest_lib import (
    tier1, tier2
)

from art.unittest_lib import StorageTest as TestCase, testflow
from rhevmtests.storage.fixtures import (
    delete_disks,
)
from rhevmtests.storage.fixtures import remove_vm  # noqa
from fixtures import prepare_images_for_upload  # noqa
from rhevmtests.storage.storage_streaming_api.fixtures import (  # noqa
    create_certificate_for_test  # noqa
)  # noqa
from fixtures import (
    add_disks_for_upload, initialize_variables,
)

from art.rhevm_api.tests_lib.low_level import (
    vms as ll_vms,
)
from art.rhevm_api.tests_lib.high_level import (
    streaming_api as hl_sapi,
)


@pytest.mark.skipif(config.PPC_ARCH, reason=config.PPC_SKIP_MESSAGE)
@pytest.mark.usefixtures(
    initialize_variables.__name__,
    delete_disks.__name__,
    add_disks_for_upload.__name__,
)
class TestUploadImages(TestCase):
    """
    Upload images - upload disks matrix with optional pause during upload

    1. Uploads of disk images (raw, qcow2_v3, qcow2_v3, ISO) from localhost
    2. Only If pause is enabled than Reaching 50% upload initiate pause wait
        for a defined timeout & resume uploads
    3. Verify data correctness via md5sum of original and uploaded images
    """
    @bz({'1532537': {}})
    @pytest.mark.parametrize(
        "pause",
        [
            pytest.param(False, marks=(polarion("RHEVM3-17322"), tier1)),
            pytest.param(True, marks=(polarion("RHEVM3-17323"), tier2))

        ],
        ids=[
            "UPLOAD_DISK_MATRIX",
            "UPLOAD_DISK_MATRIX_WITH_PAUSE_RESUME",
        ]
    )
    def test_base_disks_matrix_uploads(self, storage, pause):
        _id = global_helper.get_test_parametrize_ids(
            item=self.test_base_disks_matrix_uploads.parametrize,
            params=[pause]
        )
        testflow.step(_id)
        disks_objs = [ll_vms.get_disk_obj(
            disks_id, attribute='id'
        ) for disks_id in self.disks_ids]

        sapi_obj = hl_sapi.StreamingApiHl(
            config.TARGET_FILE_PATH, config.IMAGE_FULL_SIZE, config.UPLOAD)
        testflow.step("Check md5sums and sizes of disks %s pre upload", (
                self.disk_names
        ))
        md5sums_before, sizes_before = sapi_obj.md5sums_sizes_before_transfer()
        testflow.step(
            "Starting parallel upload of disks %s", self.disk_names
        )
        sapi_obj.transfer_multiple_disks(
            self.disk_names, sizes_before, pause=pause
        )

        testflow.step("Comparing md5sum before and after download")
        for index in range(len(self.disk_names)):
            sapi_obj.compare_md5sum_before_after_transfer(
                md5sums_before[index], host=self.spm_host, sp_id=self.sp_id,
                storage_type=storage, disk_object=disks_objs[index],
            )
