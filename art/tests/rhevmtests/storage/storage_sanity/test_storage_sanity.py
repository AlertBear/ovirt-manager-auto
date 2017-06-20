"""
Test storage sanity
https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
Storage/3_1_Storage_Sanity
"""
import pytest
import logging
import config
from art.rhevm_api.tests_lib.high_level import storagedomains as hl_sds
from art.rhevm_api.tests_lib.low_level import (

    storagedomains as ll_sds,
    vms as ll_vms,
    hosts as ll_hosts,
)
from art.rhevm_api.utils.test_utils import wait_for_tasks
from art.test_handler.tools import polarion
from art.test_handler.settings import opts
from art.unittest_lib import (
    tier1,
    tier2,
)
from art.unittest_lib import StorageTest as TestCase, testflow
from rhevmtests.storage.fixtures import remove_vm  # noqa
from rhevmtests.storage.fixtures import (
    create_storage_domain, create_vm,
)
from rhevmtests.storage.storage_sanity.fixtures import (
    get_storage_domain_size, prepare_storage_parameters,
)

from art.test_handler.tools import bz  # noqa


logger = logging.getLogger(__name__)

ISCSI = config.STORAGE_TYPE_ISCSI


@pytest.mark.usefixtures(
    create_storage_domain.__name__,
    get_storage_domain_size.__name__
)
class TestCase11591(TestCase):
    """
    Storage sanity test, create and extend a data domain
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_Sanity
    """
    __test__ = (ISCSI in opts['storages'])
    storages = set([ISCSI])
    polarion_test_case = '11591'

    @polarion("RHEVM3-11591")
    @tier1
    def test_create_and_extend_storage_domain(self):
        """
        Creates and extends a storage domain
        """
        self.spm = ll_hosts.get_spm_host(config.HOSTS)
        extend_lun = {
            "lun_list": [config.UNUSED_LUNS["lun_list"][1]],
            "lun_addresses": [config.UNUSED_LUNS["lun_addresses"][1]],
            "lun_targets": [config.UNUSED_LUNS["lun_targets"][1]],
            "override_luns": True
        }
        testflow.step(
            "Extending storage domain %s, current size is %s",
            self.new_storage_domain, self.domain_size
        )
        hl_sds.extend_storage_domain(
            self.new_storage_domain, self.storage, self.spm, **extend_lun
        )
        ll_sds.wait_for_change_total_size(
            self.new_storage_domain, self.domain_size
        )
        extended_sd_size = ll_sds.get_total_size(self.new_storage_domain)
        testflow.step(
            "Total size for domain '%s' after extend is '%s'",
            self.new_storage_domain, extended_sd_size
        )
        assert extended_sd_size > self.domain_size, (
            "The extended storage domain size hasn't increased"
        )


@pytest.mark.usefixtures(
    create_storage_domain.__name__,
    get_storage_domain_size.__name__
)
class TestCase11592(TestCase):
    """
    Storage sanity test, changing domain status
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_Sanity
    """
    __test__ = True
    polarion_test_case = '11592'

    @polarion("RHEVM3-11592")
    @tier2
    def test_change_domain_status_test(self):
        """
        Test checks if attaching/detaching storage domains works properly,
        includes ensuring that it's impossible to detach an active domain
        """
        testflow.step("Attempt to detach an active domain - this should fail")
        assert ll_sds.detachStorageDomain(
            False, config.DATA_CENTER_NAME, self.new_storage_domain
        ), (
            "Detaching non-master active domain '%s' worked" %
            self.new_storage_domain
           )

        logger.info("Waiting for tasks before deactivating the storage domain")
        wait_for_tasks(
            config.ENGINE, config.DATA_CENTER_NAME
        )
        testflow.step("De-activate non-master data domain")
        assert ll_sds.deactivateStorageDomain(
            True, config.DATA_CENTER_NAME, self.new_storage_domain
        ), (
            "De-activating non-master domain '%s' failed"
            % self.new_storage_domain
           )

        testflow.step("Re-activate non-master data domain")
        assert ll_sds.activateStorageDomain(
            True, config.DATA_CENTER_NAME, self.new_storage_domain
        ), (
            "Activating non-master data domain '%s' failed"
            % self.new_storage_domain
           )

        logger.info("Waiting for tasks before deactivating the storage domain")
        wait_for_tasks(
            config.ENGINE, config.DATA_CENTER_NAME
        )
        testflow.step("Deactivating non-master data domain")
        assert hl_sds.detach_and_deactivate_domain(
            config.DATA_CENTER_NAME, self.new_storage_domain,
            engine=config.ENGINE
        ), "Detaching and De-activating non-master domain '%s' failed" % (
            self.new_storage_domain
        )

        # In local DC, once a domain is detached it is removed completely
        # so it cannot be reattached - only run this part of the test
        # for non-local DCs
        if not config.LOCAL:
            testflow.step("Attaching non-master data domain")
            assert ll_sds.attachStorageDomain(
                True, config.DATA_CENTER_NAME, self.new_storage_domain
            ), "Attaching non-master data domain '%s' failed" \
               % self.new_storage_domain

            testflow.step("Activating non-master data domain")
            assert ll_sds.activateStorageDomain(
                True, config.DATA_CENTER_NAME, self.new_storage_domain
            ), "Activating non-master data domain '%s' failed" \
               % self.new_storage_domain


class TestCase11593(TestCase):
    """
    Storage sanity test, changing master domain
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_Sanity
    """
    __test__ = True
    polarion_test_case = '11593'

    @polarion("RHEVM3-11593")
    @tier2
    def test_change_master_domain_test(self):
        """
        Test checks if changing master domain works correctly
        """
        found, master_domain = ll_sds.findMasterStorageDomain(
            True, config.DATA_CENTER_NAME
        )
        assert found, "Master domain not found!"

        old_master_domain_name = master_domain['masterDomain']

        testflow.step("Deactivating master domain")
        wait_for_tasks(
            config.ENGINE, config.DATA_CENTER_NAME
        )
        assert ll_sds.deactivateStorageDomain(
            True, config.DATA_CENTER_NAME, old_master_domain_name
        ), "Cannot deactivate master domain"

        logger.info("Finding new master domain")
        found, new_master = ll_sds.findMasterStorageDomain(
            True, config.DATA_CENTER_NAME
        )
        testflow.step("New master: %s" % new_master)
        assert found, "New master domain not found"

        testflow.step("Activating old master domain")
        assert ll_sds.activateStorageDomain(
            True, config.DATA_CENTER_NAME, old_master_domain_name
        ), "Cannot activate old master domain"


@pytest.mark.usefixtures(
    prepare_storage_parameters.__name__,
    create_vm.__name__
)
class TestCase11581(TestCase):
    """
    Ensure that creating disks of different types works with a guest OS across
    different storage domains

    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_Sanity
    """
    __test__ = True
    polarion_test_case = '11581'

    @polarion("RHEVM3-11581")
    @tier2
    def test_multiple_disks_on_different_sd(self):
        """
        * Create a vm
        * Create disks on different storage domains with different
        allocation policies
        * Add the created disks to the vm and power it on
        * Ensure that the disks are visible
        """
        disks_before, _ = ll_vms.get_vm_storage_devices(
            self.vm_name, config.VM_USER, config.VM_PASSWORD, ensure_vm_on=True
        )
        ll_vms.stop_vms_safely([self.vm_name])
        logger.info("Adding new disks")
        for storage in self.domains:
            for index in range(self.num_of_disks):
                logger.info(
                    "Add new disk - format %s, interface %s",
                    self.formats[index], config.VIRTIO
                )
                if self.formats[index] == config.RAW_DISK:
                    policy_allocation = False
                else:
                    # policy_allocation = True --> sparse
                    policy_allocation = True
                assert ll_vms.addDisk(
                    True, self.vm_name, config.GB, True,
                    storage, type=config.DISK_TYPE_DATA,
                    interface=config.VIRTIO, format=self.formats[index],
                    sparse=policy_allocation
                ), "Failed to add disk"
                self.disk_count += 1
        disks_after, _ = ll_vms.get_vm_storage_devices(
            self.vm_name, config.VM_USER, config.VM_PASSWORD, ensure_vm_on=True
        )
        ll_vms.stop_vms_safely([self.vm_name])
        assert len(disks_after) == (len(disks_before) + self.disk_count), (
            "Added disks are not visible via the guest"
        )
        assert ll_vms.startVm(True, self.vm_name, wait_for_ip=True), (
            "Failed to start vm %s" % self.vm_name
        )
