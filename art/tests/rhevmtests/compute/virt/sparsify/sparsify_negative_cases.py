#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Sparsify sanity test with: ISCSI, NFS, Gluster
"""
import pytest

import config
import rhevmtests.compute.virt.helper as helper
from art.rhevm_api.tests_lib.low_level import (
    disks as ll_disks,
    vms as ll_vms
)
from art.test_handler.tools import polarion, bz
from art.unittest_lib import (
    tier3
)
from fixtures import (
    file_storage_domain_setup,
    add_vms_on_specific_sd,
    add_perallocate_disk
)
from sparsify_sanity_test import SparsifySanityBase


@bz({"1516689": {}})
@bz({"1447300": {"ppc": config.PPC_ARCH}})
class TestSparsifyNegativeCasesWithFileStorageDomain(SparsifySanityBase):
    """
    Sparsify negative tests with storage type file (NFS)
    """
    storage = config.STORAGE_TYPE_NFS
    nfs_version = config.NFS_VERSION_AUTO
    disk_path = None

    @tier3
    @polarion('RHEVM-18290')
    @pytest.mark.initialization_param(number_of_thin_vms=1)
    @pytest.mark.usefixtures(
        file_storage_domain_setup.__name__,
        add_vms_on_specific_sd.__name__,
        add_perallocate_disk.__name__
    )
    def test_1_sparsify_linux_preallocated_disk(self):
        """
        Negative - Test basic that sparsify feature is disabled for
        preallcoated disks
        """
        disk_id = ll_vms.get_vm_disks_ids(config.THIN_PROVISIONED_VMS[0])[1]
        assert not ll_disks.sparsify_disk(
            disk_id=disk_id, storage_domain_name=self.storage_domain_name
        ), "Sparsify activated on pre-allocated disk."

    @tier3
    @polarion('RHEVM-19289')
    @pytest.mark.initialization_param(number_of_thin_vms=1)
    @pytest.mark.usefixtures(
        file_storage_domain_setup.__name__,
        add_vms_on_specific_sd.__name__,
    )
    def test_2_start_vm_while_sparsifying(self):
        """
        Negative - start vm action while sparsifying it's disk
        """
        new_used_space, disks_ids = helper.prepare_vm_for_sparsification(
            vm_name=config.THIN_PROVISIONED_VMS[0],
            storage_manager=self.storage_manager,
            storage_domain_name=self.storage_domain_name
        )
        assert ll_disks.sparsify_disk(
            disk_id=disks_ids[0], storage_domain_name=self.storage_domain_name,
            wait=False
        ), "Failed to sparsify disk"
        assert not ll_vms.startVm(
            positive=True, vm=config.THIN_PROVISIONED_VMS[0]
        ), "VM started although sparsify is running on disk"

    @tier3
    @polarion('RHEVM-18309')
    @pytest.mark.initialization_param(number_of_thin_vms=1)
    @pytest.mark.usefixtures(
        file_storage_domain_setup.__name__,
        add_vms_on_specific_sd.__name__,
    )
    def test_3_sparsify_disk_with_snapshot(self):
        """
        Negative - sparsify VM with snapshot on disk
        """
        disk_id = ll_vms.get_vm_disks_ids(config.THIN_PROVISIONED_VMS[0])[0]
        assert ll_vms.addSnapshot(
            True, config.THIN_PROVISIONED_VMS[0],
            config.SNAPSHOT_DESCRIPTION[0]
        ), "Failed to add snapshot to VM."
        assert not ll_disks.sparsify_disk(
            disk_id, self.storage_domain_name, wait=False
        ), "Sparsify succeed on disk with snapshot."
