#! /usr/bin/python
# -*- coding: utf-8 -*-

# Test plan: RHEVM3/wiki/Compute/V2V%20automation%20cases

"""
Import VM from external providers like VMWare, KVM, Zen
"""
import pytest
import config
import helper
from art.test_handler.tools import polarion
from art.unittest_lib import testflow, VirtTest
from art.unittest_lib import (
    tier3
)
from fixtures import (
    attach_and_activate_iso_domain,
    v2v_parallel_import_fixture
)


@pytest.mark.usefixtures(
    attach_and_activate_iso_domain.__name__,
    v2v_parallel_import_fixture.__name__,
)
class TestMixCase1(VirtTest):
    """
    Import Windows vm
    TBD: Test virtio driver on guest
    """

    vms_to_import = [
        (
            config.VM_WARE_WINDOWS_7,
            config.V2V_WIN_7_NAME,
            config.VIRTIO_WIN_DRIVER
        ),
        (
            config.VM_WARE_WINDOWS_10,
            config.V2V_WIN_10_NAME,
            config.VIRTIO_WIN_DRIVER
        ),
        (
            config.VM_WARE_WINDOWS_12,
            config.V2V_WIN_2012_NAME,
            config.VIRTIO_WIN_DRIVER
        ),
    ]

    @tier3
    @pytest.mark.parametrize(
        ("vm_name_on_provider", "new_vm_name", "number_of_disks"),
        [
            polarion("RHEVM-24444")(
                [config.VM_WARE_WINDOWS_7, config.V2V_WIN_7_NAME, 1]
            ),
            polarion("RHEVM-24443")(
                [config.VM_WARE_WINDOWS_10, config.V2V_WIN_10_NAME, 1]
            ),
            polarion("RHEVM-24411")(
                [config.VM_WARE_WINDOWS_12, config.V2V_WIN_2012_NAME, 1]
            ),
        ],
        ids=[
            "Check_imported_windows_7_from_wmware",
            "Check_imported_windows_10_from_wmware",
            "Check_imported_windows_2012_from_wmware",
        ]
    )
    def test_import_windows_vm(
        self, vm_name_on_provider, new_vm_name, number_of_disks
    ):
        """
        Check the imported VM: disk size, memory, sockets, cores, threads,
                windows_drivers(TBD), number_of_disks

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
class TestMixCase2(VirtTest):
    """
    Mix cases:
    1. Import VM with long name
    2. Import VMs 20 disks
    """
    vms_to_import = [
        (config.VM_WARE_WITH_NAME_64_CHARS, config.VM_WITH_LONG_NAME, None),
        (config.VM_WARE_WITH_20_DISKS, config.VM_WARE_WITH_20_DISKS, None)
    ]

    @tier3
    @pytest.mark.parametrize(
        ("vm_name_on_provider", "new_vm_name", "number_of_disks"),
        [
            polarion("RHEVM-24413")(
                [config.VM_WARE_WITH_NAME_64_CHARS,
                 config.VM_WITH_LONG_NAME, 1]
            ),
            polarion("RHEVM-24415")(
                [
                    config.VM_WARE_WITH_20_DISKS,
                    config.VM_WARE_WITH_20_DISKS,
                    20
                ]
            )
        ],
        ids=[
            "Check_imported_VM_with_long_name",
            "Check_imported_VM_with_20_disks",
        ]
    )
    def test_import_vm(
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
