#! /usr/bin/python
# -*- coding: utf-8 -*-

# Virt Sparsify:
# https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
# Compute/4_1_VIRT_Sparsify

"""
Sparsify sanity test with: ISCSI, NFS, Gluster
"""
import pytest
import config
import rhevmtests.virt.helper as helper
from art.rhevm_api.tests_lib.low_level import (
    disks as ll_disks,
)
from art.test_handler.tools import polarion
from art.unittest_lib import VirtTest
from art.unittest_lib import attr
from rhevmtests.fixtures import (
    init_storage_manager,
    create_lun_on_storage_server
)
from rhevmtests.virt.sparsify.fixtures import (
    file_storage_domain_setup,
    add_vms_on_specific_sd,
    block_storage_domain_setup,
    copy_template_to_new_storage_domain,
)


class SparsifySanityBase(VirtTest):
    """
    Sparsify sanity base class
    """
    storage = None
    storage_manager = None
    storage_server = None
    storage_domain_name = None


class TestSparsifySanityBlockDevice(SparsifySanityBase):
    """
    Sparsify sanity block device: ISCSI
    """
    storage = config.STORAGE_TYPE_ISCSI
    storage_domain_name = config.NEW_SD_NAME % storage
    number_of_thin_vms = 1
    lun_used_space = None
    new_lun_id = None
    new_lun_identifier = None

    @attr(tier=2)
    @polarion('RHEVM-18289')
    @pytest.mark.usefixtures(
        init_storage_manager.__name__,
        create_lun_on_storage_server.__name__,
        block_storage_domain_setup.__name__,
        copy_template_to_new_storage_domain.__name__,
        add_vms_on_specific_sd.__name__,
    )
    def test_1_sparsify_linux_thin_disk_iscsi(self):
        """
        Test basic sparsify feature on iscsi
        """
        new_used_space, disk_ids = helper.prepare_vm_for_sparsification(
            vm_name=config.THIN_PROVISIONED_VMS[0],
            lun_id=self.new_lun_id,
            storage_manager=self.storage_manager,
            storage_domain_name=self.storage_domain_name
        )
        assert ll_disks.sparsify_disk(disk_ids[0], self.storage_domain_name)
        helper.verify_vm_disk_not_corrupted(config.THIN_PROVISIONED_VMS[0])
        assert helper.verify_sparsify_success(
            previous_used_space=new_used_space,
            storage_manager=self.storage_manager,
            lun_id=self.new_lun_id
        )


class TestSparsifySanityFileDevice(SparsifySanityBase):
    """
    Sparsify sanity file device: NFS, Gluster
    """
    disk_path = None
    number_of_thin_vms = 1

    @attr(tier=2)
    @pytest.mark.usefixtures(
        file_storage_domain_setup.__name__,
        add_vms_on_specific_sd.__name__,
    )
    @pytest.mark.parametrize(
        ("storage", "nfs_version"),
        [
            polarion("RHEVM-18289")([
                config.STORAGE_TYPE_NFS, config.NFS_VERSION_AUTO
            ]),
            polarion("RHEVM-21589")([
                config.STORAGE_TYPE_NFS, config.NFS_VERSION_4_2
            ]),
            polarion("RHEVM-21589")([
                config.STORAGE_TYPE_GLUSTER, config.NFS_VERSION_AUTO
            ])
        ]
    )
    def test_linux_thin_disk(self, storage, nfs_version):
        """
        Test sparsify on thin provision disk with: NFS, Gluster
        """
        new_used_space, disks_ids = helper.prepare_vm_for_sparsification(
            vm_name=config.THIN_PROVISIONED_VMS[0],
            storage_manager=self.storage_manager,
            storage_domain_name=self.storage_domain_name
        )
        assert ll_disks.sparsify_disk(disks_ids[0], self.storage_domain_name)
        helper.verify_vm_disk_not_corrupted(config.THIN_PROVISIONED_VMS[0])
        assert helper.verify_sparsify_success(
            previous_used_space=new_used_space,
            storage_manager=self.storage_manager,
            disk_path=self.disk_path
        )
