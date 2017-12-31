#! /usr/bin/python
# -*- coding: utf-8 -*-

# Test plan: RHEVM3/wiki/Compute/V2V%20automation%20cases

"""
Import VM from external providers like VMWare, KVM
"""

import pytest
import config
import helper
from art.test_handler.tools import polarion
from art.unittest_lib import testflow, VirtTest
from art.unittest_lib import (
    tier2
)
from fixtures import (
    v2v_parallel_import_fixture
)


@pytest.mark.usefixtures(v2v_parallel_import_fixture.__name__)
class TestV2VRhelKVM(VirtTest):
    """
    Test RHEL VM import from external KVM provider
    """
    providers = [config.KVM_PROVIDER]
    vms_to_import = [
        (config.KVM_RHEL_7, config.KVM_RHEL_7, None),
    ]

    @tier2
    @pytest.mark.parametrize(
        ("vm_name_on_provider", "new_vm_name", "number_of_disks"),
        [
            polarion("RHEVM-24697")(
                [
                    config.KVM_RHEL_7,
                    config.KVM_RHEL_7,
                    1
                ]
            )
        ],
        ids=[
            "Import RHEL VM from KVM"
        ]
    )
    def test_import_rhel_vm(
        self, vm_name_on_provider, new_vm_name, number_of_disks
    ):
        """
        Check the imported VM: disk size, memory, sockets, cores, threads,
        number_of_disks

        Args:
            vm_name_on_provider (str): VM name on vmware data center
            new_vm_name (str): New VM name on RHEVM
            number_of_disks(int): Number of disks on VM
        """
        for provider in config.VMWARE_PROVIDERS:
            testflow.step(
                "Checking imported vm:{p_vm} from: {p} to vm: {vm}".format(
                    p_vm=vm_name_on_provider, p=provider, vm=new_vm_name
                )
            )
            helper.check_imported_vm(
                vm_name=new_vm_name,
                number_of_disks=number_of_disks
            )


@pytest.mark.usefixtures(
    v2v_parallel_import_fixture.__name__,
)
class TestV2VRhelVMware(VirtTest):
    """
    Test RHEL VM import from external VMware providers
    """
    vms_to_import = [
        (config.VM_WARE_RHEL_7_2,  config.V2V_RHEL_7_2_NAME, None),
    ]

    @tier2
    @pytest.mark.parametrize(
        ("vm_name_on_provider", "new_vm_name", "number_of_disks"),
        [
            polarion("RHEVM-24428")(
                [
                    config.VM_WARE_RHEL_7_2,
                    config.V2V_RHEL_7_2_NAME,
                    1
                ]
            )
        ],
        ids=[
            "Import RHEL VM from vmware"
        ]
    )
    def test_import_rhel_vm(
        self, vm_name_on_provider, new_vm_name, number_of_disks
    ):
        """
        Check the imported VM: disk size, memory, sockets, cores, threads,
        number_of_disks

        Args:
            vm_name_on_provider (str): VM name on vmware data center
            new_vm_name (str): New VM name on RHEVM
            number_of_disks(int): Number of disks on VM
        """
        for provider in config.VMWARE_PROVIDERS:
            testflow.step(
                "Checking imported vm:{p_vm} from: {p} to vm: {vm}".format(
                    p_vm=vm_name_on_provider, p=provider, vm=new_vm_name
                )
            )
            helper.check_imported_vm(
                vm_name=new_vm_name,
                number_of_disks=number_of_disks
            )
