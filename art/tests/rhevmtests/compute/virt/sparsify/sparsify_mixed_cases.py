#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Sparsify sanity test with: ISCSI, NFS, Gluster
"""
import pytest
from concurrent.futures import ThreadPoolExecutor

import config
import rhevmtests.compute.virt.helper as helper
from art.rhevm_api.tests_lib.low_level import (
    vms as ll_vms
)
from art.test_handler.tools import polarion
from art.unittest_lib import (
    tier3,
)
from fixtures import (
    file_storage_domain_setup,
    add_vms_on_specific_sd,
)
from sparsify_sanity_test import SparsifySanityBase


class TestSparsifyMixedCasesWithFileStorageDomain(SparsifySanityBase):
    """
    Sparsify negative tests with storage type file (NFS)
    """
    storage = config.STORAGE_TYPE_NFS
    nfs_version = config.NFS_VERSION_AUTO
    disk_path = None

    @tier3
    @polarion('RHEVM-18289')
    @pytest.mark.initialization_param(number_of_thin_vms=3)
    @pytest.mark.usefixtures(
        file_storage_domain_setup.__name__,
        add_vms_on_specific_sd.__name__,
    )
    def test_1_sparsify_multiple_vms_thin_disk(self):
        """
        Tests sparsification of several vms at once.
        """
        results = []
        vms_list = config.THIN_PROVISIONED_VMS
        with ThreadPoolExecutor(max_workers=len(vms_list)) as executor:
            for vm in vms_list:
                results.append(
                    executor.submit(
                        helper.prepare_vm_for_sparsification,
                        vm_name=vm,
                        storage_manager=self.storage_manager,
                        storage_domain_name=self.storage_domain_name
                    )
                )
        disks_ids = [ll_vms.get_vm_disks_ids(vm)[0] for vm in vms_list]
        helper.execute_multi_sparsify(disks_ids, self.storage_domain_name)

    @tier3
    @polarion('RHEVM-18289')
    @pytest.mark.initialization_param(number_of_thin_vms=1)
    @pytest.mark.usefixtures(
        file_storage_domain_setup.__name__,
        add_vms_on_specific_sd.__name__,
    )
    def test_2_sparsify_multiple_disks_on_vm(self):
        """
        Tests sparsification of several disks on 1 vm
        """
        vm = config.THIN_PROVISIONED_VMS[0]
        helper.prepare_vm_for_sparsification(
            vm_name=vm,
            storage_manager=self.storage_manager,
            storage_domain_name=self.storage_domain_name,
            all_disks=True
        )
        disks_ids = ll_vms.get_vm_disks_ids(vm)
        helper.execute_multi_sparsify(disks_ids, self.storage_domain_name)
