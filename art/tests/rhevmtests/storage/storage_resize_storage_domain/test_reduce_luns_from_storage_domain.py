"""
4.1 Feature: Reduce LUNs from storage domain
https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
Storage_4_0/4_1_Storage_Reduce_LUNs_from_SDs
"""
import pytest
import config
import helpers
import rhevmtests.storage.helpers as storage_helpers
from art.test_handler.tools import polarion
from art.unittest_lib import (
    tier2,
    tier3,
)
from art.unittest_lib.common import StorageTest as TestCase, testflow
from art.rhevm_api.tests_lib.low_level import (
    storagedomains as ll_sd,
)
from fixtures import (
    set_disk_params, init_domain_disk_param
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
    init_domain_disk_param.__name__,
    create_vm.__name__,
    start_vm.__name__,
    init_vm_executor.__name__,
)
class ReduceLUNVerifyDataIntegrity(BaseTestCase):
    """
    Reduce LUN with data integrity base class
    """
    template = config.TEMPLATE_NAME[0]
    file_name = None
    checksum_before = None

    def reduce_lun_with_data_integrity(self):
        self.file_name, self.checksum_before = (
            helpers.write_content_and_get_checksum(
                vm_name=self.vm_name, vm_executor=self.vm_executor
            )
        )
        helpers.power_off_vm(self.vm_name)
        self.reduce_lun()
        helpers.verify_data_integrity(
            vm_name=self.vm_name, file_name=self.file_name,
            vm_executor=self.vm_executor, checksum_before=self.checksum_before
        )


class TestCase17508(ReduceLUNVerifyDataIntegrity):
    """
    RHEVM-17508 Remove LUN from storage domain and verify data integrity
    """
    __test__ = True

    @polarion("RHEVM-17508")
    @tier2
    def test_reduce_single_lun_data_integrity(self):
        self.reduce_lun_with_data_integrity()


class TestCase17423(ReduceLUNVerifyDataIntegrity):
    """
    RHEVM-17423 Remove multiple LUNs from storage domain and verify data
    integrity
    """
    __test__ = True
    extend_indices = [1, 2]

    @polarion("RHEVM-17423")
    @tier3
    def test_reduce_multiple_luns_data_integrity(self):
        self.reduce_lun_with_data_integrity()


class TestCase18164(BaseTestCase):
    """
    RHEVM-18164 Remove an empty LUN from storage domain
    """
    __test__ = True

    @polarion("RHEVM-17510")
    @tier2
    def test_reduce_single_lun(self):
        self.reduce_lun()


class TestCase17510(BaseTestCase):
    """
    RHEVM-17510 Re-attach LUN to the same storage domain
    """
    __test__ = True

    @polarion("RHEVM-17510")
    @tier3
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

    @polarion("RHEVM-17427")
    @tier3
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

    @polarion("RHEVM-17427")
    @tier3
    def test_treshold_on_remaining_lun(self):
        testflow.step(
            "Reducing LUNs %s from storage domain %s. The operation is "
            "expected to fail", self.extension_luns, self.new_storage_domain
        )
        self.reduce_lun()
