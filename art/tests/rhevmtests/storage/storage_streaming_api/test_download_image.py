"""
Download image via sdk instead of directly using a tool or downloading the
image from the host itself.
https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
Storage_4_0/4_1_Storage_Download_Disk_Image_with_python_sdk
"""
import config
import pytest
from art.test_handler.tools import polarion, bz

from art.unittest_lib import (
    tier1,
)

from art.unittest_lib import StorageTest as TestCase, testflow
from rhevmtests.storage.fixtures import (
    delete_disks, create_vm, create_disks_with_fs,
)
from rhevmtests.storage.fixtures import remove_vm  # noqa

from fixtures import (
    test_detach_disks, initialize_variables, test_delete_downloaded_files,
)
from art.rhevm_api.tests_lib.low_level import (
    streaming_api as ll_sapi,
)


@pytest.mark.usefixtures(
    initialize_variables.__name__,
)
class BaseTestCase(TestCase):
    """
    Initialize parameters
    """
    __test__ = False


@pytest.mark.usefixtures(
    delete_disks.__name__,
    create_vm.__name__,
    create_disks_with_fs.__name__,
    test_detach_disks.__name__,
    test_delete_downloaded_files.__name__,
    )
class TestCase18258(BaseTestCase):
    """
    Download image - floating disks matrix

    1. Create floating disk permutations with data content
    2. Download image (using disk-id,output-file,download size) of disks
    3. Verify data correctness via md5sum of original and downloaded images

    """
    __test__ = True
    polarion_test_case = '18258'
    add_file_on_each_disk = True

    @polarion("RHEVM3-18258")
    @tier1
    @bz({'1506677': {}})
    def test_floating_disks_matrix_downloads(self):
        sapi_obj = ll_sapi.StreamingApi(config.TARGET_FILE_PATH, None)
        testflow.step("Check md5sums and sizes of disks %s pre download", (
                self.disks_names
        ))
        md5sums_before, sizes_before = sapi_obj.md5sums_sizes_before_download(
            self.spm_host, self.storage, self.disks_names, self.sp_id
        )

        testflow.step(
            "Starting parallel download of disks %s", self.disks_names
        )
        output_path = sapi_obj.download_multiple_disks(
            self.disks_names, sizes_before
        )

        testflow.step("Comparing md5sum before and after download")
        for index in range(len(self.disks_names)):
            sapi_obj.compare_md5sum_before_after_download(
                md5sums_before[index], output=output_path[index]
            )
        self.files_to_remove.append(output_path)
