"""
4.1 Feature: Reduce LUNs from storage domain
https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
Storage_4_0/4_1_Storage_Reduce_LUNs_from_SDs
"""
import pytest
import config
import os
import rhevmtests.storage.helpers as storage_helpers
from art.test_handler.tools import polarion
from art.unittest_lib import attr
from art.unittest_lib.common import StorageTest as TestCase, testflow
from art.rhevm_api.tests_lib.low_level import (
    vms as ll_vms,
    storagedomains as ll_sd,
)
from fixtures import (
    set_disk_params
)
from rhevmtests.storage.fixtures import (
    create_storage_domain, create_vm, start_vm, init_vm_executor, add_disk,
    extend_storage_domain, skip_invalid_storage_type, copy_template_disk
)
from rhevmtests.storage.fixtures import remove_vm  # noqa F401


@pytest.mark.usefixtures(
    skip_invalid_storage_type.__name__,
    create_storage_domain.__name__,
    extend_storage_domain.__name__,
)
class BaseTestCase(TestCase):
    """
    Common class for all tests with some common methods
    """
    storages = set([config.STORAGE_TYPE_ISCSI, config.STORAGE_TYPE_FCP])
    positive = True
    wait = True

    def reduce_lun(self):
        """
        Reduce LUNs from storage domain
        """
        testflow.step("Reducing storage domain %s", self.new_storage_domain)
        storage_helpers.reduce_luns_from_storage_domain(
            storage_domain=self.new_storage_domain, luns=self.extension_luns,
            expected_size=self.domain_size, wait=self.wait,
            positive=self.positive
        )


@pytest.mark.usefixtures(
    copy_template_disk.__name__,
    create_vm.__name__,
    start_vm.__name__,
    init_vm_executor.__name__,
)
class ReduceLUNVerifyDataIntegrity(BaseTestCase):
    """
    Reduce LUN with data integrity base class
    """
    template = config.TEMPLATE_NAME[0]

    def checksum_before_reduce(self):
        """
        Create file, write content to it and get checksum for it
        """
        self.file_name = os.path.join(config.FILE_PATH, config.FILE_NAME)

        testflow.step(
            "Creating file %s on VM %s", self.file_name, self.vm_name
        )
        assert storage_helpers.create_file_on_vm(
            vm_name=self.vm_name, file_name=config.FILE_NAME,
            path=config.FILE_PATH, vm_executor=self.vm_executor
        )

        testflow.step("Writing to file %s", self.file_name)
        assert storage_helpers.write_content_to_file(
            vm_name=self.vm_name, file_name=self.file_name,
            content=config.TEXT_CONTENT, vm_executor=self.vm_executor
        )

        testflow.step("Getting checksum for file %s", self.file_name)
        self.checksum_before = storage_helpers.checksum_file(
            vm_name=self.vm_name, file_name=self.file_name,
            vm_executor=self.vm_executor
        )

        testflow.step("Syncing VM %s file system", self.vm_name)
        command = 'sync'
        storage_helpers._run_cmd_on_remote_machine(
            machine_name=self.vm_name, command=command,
            vm_executor=self.vm_executor
        )

        testflow.step("Power off VM %s", self.vm_name)
        assert ll_vms.stop_vms_safely(vms_list=[self.vm_name]), (
            "Failed to power off VM %s" % self.vm_name
        )

    def verify_data_integrity(self):
        """
        Get checksum to the file that a checksum was taken for before
        storage domain reduction and compare the checksums
        """
        testflow.step("Starting VM %s", self.vm_name)
        ll_vms.start_vms(
            vm_list=[self.vm_name], max_workers=1,
            wait_for_status=config.VM_UP, wait_for_ip=True
        ), "Failed to start VM %s" % (self.vm_name)

        testflow.step("Getting checksum for file %s", self.file_name)
        checksum_after = storage_helpers.checksum_file(
            vm_name=self.vm_name, file_name=self.file_name,
            vm_executor=self.vm_executor
        )

        testflow.step(
            "Checksum before LUNs reduction: %s."
            "Checksum after LUNs reduction: %s",
            self.checksum_before, checksum_after
        )
        assert self.checksum_before == checksum_after, (
            "VM %s file %s got corrupted after LUN removal from storage "
            "domain %s" % (
                self.vm_name, self.file_name, self.new_storage_domain
            )
        )

    def reduce_lun_with_data_integrity(self):
        self.checksum_before_reduce()
        self.reduce_lun()
        self.verify_data_integrity()


class TestCase17508(ReduceLUNVerifyDataIntegrity):
    """
    RHEVM-17508 Remove LUN from storage domain and verify data integrity
    """
    __test__ = True

    @polarion("RHEVM3-17508")
    @attr(tier=1)
    def test_reduce_single_lun_data_integrity(self):
        self.reduce_lun_with_data_integrity()


class TestCase17423(ReduceLUNVerifyDataIntegrity):
    """
    RHEVM-17423 Remove multiple LUNs from storage domain and verify data
    integrity
    """
    __test__ = True
    extend_indices = [1, 2]

    @polarion("RHEVM3-17423")
    @attr(tier=3)
    def test_reduce_multiple_luns_data_integrity(self):
        self.reduce_lun_with_data_integrity()


class TestCase18164(BaseTestCase):
    """
    RHEVM-18164 Remove an empty LUN from storage domain
    """
    __test__ = True

    @polarion("RHEVM3-17510")
    @attr(tier=2)
    def test_reduce_single_lun(self):
        self.reduce_lun()


class TestCase17510(BaseTestCase):
    """
    RHEVM-17510 Re-attach LUN to the same storage domain
    """
    __test__ = True

    @polarion("RHEVM3-17510")
    @attr(tier=3)
    def test_reduce_and_extend_single_lun(self):
        self.reduce_lun()

        testflow.step("Extending storage domain %s", self.new_storage_domain)
        extenstion_luns = storage_helpers.extend_storage_domain(
            storage_domain=self.new_storage_domain, extend_indices=[1]
        )
        testflow.step(
            "storage domain %s extended successfully with LUNs %s", (
                self.new_storage_domain, extenstion_luns
            )
        )


class TestCase17427(BaseTestCase):
    """
    RHEVM-17427 Reduce LUN from storage domain and detach the storage domain
    """
    __test__ = True
    wait = False

    @polarion("RHEVM3-17427")
    @attr(tier=3)
    def test_reduce_and_extend_single_lun(self):
        self.reduce_lun()

        testflow.step(
            "Detaching storage domain %s from data center %s. "
            "The operation is expected to fail", (
                self.new_storage_domain, config.DATA_CENTER_NAME
            )
        )
        assert ll_sd.detachStorageDomain(
            positive=False, datacenter=config.DATA_CENTER_NAME,
            storagedomain=self.new_storage_domain
        ), (
            "Storage domain %s wasn't supposed to be detached while "
            "being reduced" % self.new_storage_domain
        )


@pytest.mark.usefixtures(
    set_disk_params.__name__,
    add_disk.__name__
)
class TestCase17549(BaseTestCase):
    """
    RHEVM-17427 Reduce LUN from storage domain when the remaining LUN is not
    big enough to accommodate the reduction LUN data
    """
    __test__ = True
    positive = False

    @polarion("RHEVM3-17427")
    @attr(tier=3)
    def test_treshold_on_remaining_lun(self):
        testflow.step(
            "Reducing LUNs %s from storage domain %s. The operation is "
            "expected to fail", self.extension_luns, self.new_storage_domain
        )
        self.reduce_lun()
