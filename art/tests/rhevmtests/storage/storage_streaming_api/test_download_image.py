"""
Download image via sdk instead of directly using a tool or downloading the
image from the host itself.
https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
Storage_4_0/4_1_Storage_Download_Disk_Image_with_python_sdk
"""
import config
import pytest
from art.test_handler.tools import polarion, bz

from art.rhevm_api.tests_lib.low_level import (
    vms as ll_vms,
)

from art.unittest_lib import (
    tier1, tier2
)

from art.unittest_lib import StorageTest as TestCase, testflow
from rhevmtests.storage.fixtures import (
    delete_disks, create_vm, create_disks_with_fs, poweroff_vm, start_vm,
    create_snapshot,
)
from fixtures import (  # noqa
    create_certificate_for_test,  # noqa
    prepare_images_for_download  # noqa
)  # noqa
from rhevmtests.storage.fixtures import remove_vm  # noqa

from fixtures import (
    initialize_variables, test_detach_disks, test_delete_downloaded_files,
    disk_names_for_test, extend_disks_for_test
)
from art.rhevm_api.tests_lib.high_level import (
    streaming_api as hl_sapi,
)


@pytest.mark.skipif(config.PPC_ARCH, reason=config.PPC_SKIP_MESSAGE)
@pytest.mark.usefixtures(
    test_delete_downloaded_files.__name__,
    initialize_variables.__name__,
    delete_disks.__name__,
    create_vm.__name__,
    create_disks_with_fs.__name__,
    disk_names_for_test.__name__,
)
class BaseTestCase(TestCase):
    """
    This class implements setup and teardown for the permutation of disks
    download used as part of the tests
    """
    @bz({'1497511': {'storage': ['glusterfs']}})
    def basic_disk_download_flow(
        self, storage, snapshot=False, extend=False, pause=False,
        interrupt=False, positive=True
    ):
        sapi_obj = hl_sapi.StreamingApiHl(
            config.TARGET_FILE_PATH, config.IMAGE_FULL_SIZE, config.DOWNLOAD
        )
        testflow.step("Check md5sums and sizes of disks %s pre download", (
                self.disk_names
        ))
        if snapshot:
            sdisks_objs = ll_vms.get_snapshot_disks(
                self.vm_name, self.snapshot_description
            )
            test_sdisks_objs = [
                sdisks_objs[i] for i in range(len(sdisks_objs))
                if sdisks_objs[i].get_alias() in self.disk_names
            ]

            md5sums_before, sizes_before = (
                sapi_obj.md5sums_sizes_before_transfer(
                    self.spm_host, storage, self.disk_names, self.sp_id,
                    snapshot=snapshot, sdisks_objects=test_sdisks_objs,
                )
            )
            testflow.step(
                "Starting parallel download of snapshot disks of the following"
                "disks %s matching snapshot %s", self.disk_names,
                self.snapshot_description
            )
            output_path = sapi_obj.transfer_multiple_disks(
                self.disk_names, sizes_before, snapshot=snapshot,
                sdisk_objs=test_sdisks_objs
            )
        else:
            md5sums_before, sizes_before = (
                sapi_obj.md5sums_sizes_before_transfer(
                    self.spm_host, storage, self.disk_names, self.sp_id,
                    extend=extend
                )
            )

            testflow.step(
                "Starting parallel download of disks %s", self.disk_names
            )

            output_path = sapi_obj.transfer_multiple_disks(
                self.disk_names, sizes_before, pause=pause,
                vm_name=self.vm_name, interrupt=interrupt, positive=positive
            )

        testflow.step("Comparing md5sum before and after download")

        for index in range(len(self.disk_names)):
            sapi_obj.compare_md5sum_before_after_transfer(
                md5sums_before[index], output=output_path[index]
            )


@pytest.mark.usefixtures(
    test_detach_disks.__name__,
)
class TestCase18258(BaseTestCase):
    """
    Download image - floating disks matrix

    1. Create floating disk permutations with data content
    2. Download image (using disk-id,output-file,download size) of disks
    3. Verify data correctness via md5sum of original and downloaded images

    """
    polarion_test_case = '18258'
    add_file_on_each_disk = True

    @polarion("RHEVM3-%s" % polarion_test_case)
    @tier1
    def test_floating_disks_matrix_downloads(self, storage):
        self.basic_disk_download_flow(storage)


@pytest.mark.usefixtures(
    start_vm.__name__,
    poweroff_vm.__name__,
)
class TestCase18259(BaseTestCase):
    """
    Download disks attached to a running VM - should fail

    1. Create disk permutations with data content attached to a VM
    2. Try to Download images of disks ->  Test should fail

    """
    polarion_test_case = '18259'
    add_file_on_each_disk = True

    @polarion("RHEVM3-%s" % polarion_test_case)
    @tier2
    def test_download_disk_on_running_vm(self, storage):
        sapi_obj = hl_sapi.StreamingApiHl(
            config.TARGET_FILE_PATH, config.IMAGE_FULL_SIZE, config.DOWNLOAD)

        testflow.step(
            "Starting parallel download of disks %s should fail as they are "
            "attach to running VM %s", self.disk_names, self.vm_name
        )
        sapi_obj.transfer_multiple_disks(
            self.disk_names, sizes_before=[0, 0, 0, 0], positive=False
        )


@pytest.mark.usefixtures(
    create_snapshot.__name__,
)
class TestCase18829(BaseTestCase):
    """
    Download disks snapshot

    1. Create disk permutations with data content attached to a VM
    2. Create a snapshot
    3. Download the relevant disk snapshots
    4. Verify correctness via md5sum

    """
    polarion_test_case = '18829'

    @polarion("RHEVM3-%s" % polarion_test_case)
    @tier2
    def test_download_disk_on_running_vm(self, storage):
        self.basic_disk_download_flow(storage, snapshot=True)


@pytest.mark.usefixtures(
    extend_disks_for_test.__name__,
    test_detach_disks.__name__,
)
class TestCase18268(BaseTestCase):
    """
    Download extended image - floating disks matrix

    1. Create extended floating disk permutations with data content
    2. Download images (using disk-id,output-file,download size) of disks
    3. Verify data correctness via md5sum of original and downloaded images

    """
    polarion_test_case = '18268'
    new_size = 2147483648

    @polarion("RHEVM3-18268")
    @tier2
    def test_download_extended_floating_disks(self, storage):
        self.basic_disk_download_flow(storage, extend=True)


@pytest.mark.usefixtures(
    test_detach_disks.__name__,
)
class TestCase18275(BaseTestCase):
    """
     Download disks Pause and resume - floating disks matrix

    1. Create extended floating disk permutations with data content
    2. Download images (using disk-id,output-file,download size) of disks
    3. Pause reaching 50% download for 1min and then resume download
    4. Verify data correctness via md5sum of original and downloaded images

    """
    polarion_test_case = '18275'

    @polarion("RHEVM3-%s" % polarion_test_case)
    @tier2
    def test_download_pause_resume_disks(self, storage):
        self.basic_disk_download_flow(storage, pause=True)


@pytest.mark.usefixtures(
    test_detach_disks.__name__,
)
class TestCase19265(BaseTestCase):
    """
    Attach disks to VM while being downloaded - attach should fail but download
    should succeed

    1. Create extended floating disk permutations with data content
    2. Download images (using disk-id,output-file,download size) of disks
    3. Reaching 50% of each downloaded disk try to attach the disks to the VM
        operation should fail but download should continue without issues.
    4. Verify data correctness via md5sum of original and downloaded images

    """
    polarion_test_case = '19265'

    @polarion("RHEVM3-%s" % polarion_test_case)
    @tier2
    def test_attach_disks_during_downloads(self, storage):
        self.basic_disk_download_flow(storage, interrupt=True)
