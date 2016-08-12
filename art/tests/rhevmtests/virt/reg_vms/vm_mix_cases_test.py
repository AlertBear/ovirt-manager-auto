#! /usr/bin/python
# -*- coding: utf-8 -*-

# Virt VMs: RHEVM3/wiki/Compute/Virt_VMs

import logging
import pytest
from art.unittest_lib import attr, VirtTest, testflow
from art.test_handler.tools import polarion
import art.rhevm_api.tests_lib.low_level.templates as ll_templates
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import rhevmtests.virt.helper as helper
from rhevmtests.virt.reg_vms.fixtures import (
    add_vm_fixture, basic_teardown_fixture, add_vm_from_template_fixture,
    add_template_fixture, vm_display_fixture,
)
import config

logger = logging.getLogger("vm_mix_cases")


class TestMixCases(VirtTest):

    __test__ = True
    cluster_name = config.CLUSTER_NAME[0]
    template_name = config.TEMPLATE_NAME[0]
    vm_name = 'mix_cases'
    add_disk = False
    vm_parameters = None
    master_domain, export_domain, non_master_domain = (
        helper.get_storage_domains()
    )

    @attr(tier=1)
    @polarion("RHEVM3-12522")
    @pytest.mark.usefixtures(add_vm_from_template_fixture.__name__)
    def test_set_ticket(self):
        """
        Start vm, check set ticket
        """
        testflow.step("Set ticket test")
        assert ll_vms.startVm(
            positive=True, vm=self.vm_name
        ), "Failed to start vm"
        testflow.step("Ticket running vm %s", self.vm_name)
        assert ll_vms.ticketVm(
            True, self.vm_name, config.ticket_expire_time
        ), "Failed to set ticket to VM"

    @attr(tier=1)
    @polarion("RHEVM3-14773")
    @pytest.mark.usefixtures(add_vm_fixture.__name__)
    def test_template_from_running_vm(self):
        """
         Negative:
         Create template from running vm
        """
        testflow.step("Negative: Create template from running vm")
        assert not ll_templates.createTemplate(
            True, vm=self.vm_name,
            name=config.template_name
        )

    @attr(tier=1)
    @polarion("RHEVM3-12523")
    @pytest.mark.usefixtures(add_vm_fixture.__name__)
    def test_check_vm_cdrom(self):
        """
        Add new vm and check that vm have attached cdrom
        """
        testflow.step("Check if vm %s have cdrom", self.vm_name)
        assert ll_vms.checkVmHasCdromAttached(
            positive=True,
            vmName=self.vm_name
        )

    @attr(tier=2)
    @polarion("RHEVM3-12524")
    @pytest.mark.usefixtures(add_vm_fixture.__name__)
    def test_vm_statistics(self):
        """
        Add vm and check vm stats
        """
        testflow.step("Check vm %s statistics", self.vm_name)
        assert ll_vms.checkVmStatistics(True, self.vm_name)

    @attr(tier=2)
    @polarion("RHEVM3-12577")
    @pytest.mark.usefixtures(add_vm_fixture.__name__)
    def test_network_vm(self):
        """
        Create, update and remove vm nic
        """

        nics = ["%s_%d" % (config.NIC_NAME, i) for i in range(3)]

        testflow.step("Add nic %s to vm %s", nics[0], self.vm_name)
        assert ll_vms.addNic(
            True, vm=self.vm_name,
            name=nics[0],
            network=config.MGMT_BRIDGE
        )
        testflow.step("Add additional nic %s to vm %s", nics[1], self.vm_name)

        assert ll_vms.addNic(
            True, vm=self.vm_name,
            name=nics[1],
            network=config.MGMT_BRIDGE
        )
        testflow.step("Update nic %s name to %s", nics[1], nics[2])
        assert ll_vms.updateNic(
            True, vm=self.vm_name,
            nic=nics[1], name=nics[2]
        )
        testflow.step("Remove nic %s from vm %s", nics[2], self.vm_name)
        assert ll_vms.removeNic(
            True, vm=self.vm_name,
            nic=nics[2]
        )

    @attr(tier=2)
    @polarion("RHEVM3-12572")
    @pytest.mark.usefixtures(add_vm_fixture.__name__)
    def test_add_raw_virtio_disk_without_sparse(self):
        """
        Add raw virtio disk to vm without sparse
        """
        testflow.step("Add new vm with raw virtio disk to vm without sparse")
        assert ll_vms.addDisk(
            True,
            vm=self.vm_name,
            provisioned_size=config.GB,
            storagedomain=self.master_domain,
            type=config.DISK_TYPE_DATA,
            format=config.DISK_FORMAT_RAW,
            interface=config.INTERFACE_VIRTIO,
            sparse=False
        )

    @attr(tier=2)
    @polarion("RHEVM3-12568")
    @pytest.mark.usefixtures(add_vm_fixture.__name__)
    @pytest.mark.skipif(config.PPC_ARCH, reason=config.PPC_SKIP_MESSAGE)
    def test_add_bootable_cow_ide_data_disk(self):
        """
        Add bootable cow ide data disk to vm
        """

        testflow.step("Add new VM with bootable cow ide data disk")
        assert ll_vms.addDisk(
            True,
            vm=self.vm_name,
            provisioned_size=config.GB,
            storagedomain=self.master_domain,
            type=config.DISK_TYPE_DATA,
            format=config.DISK_FORMAT_COW,
            interface=config.INTERFACE_IDE,
            bootable=True,
            wipe_after_delete=True)

    @attr(tier=2)
    @polarion("RHEVM3-12573")
    @pytest.mark.usefixtures(add_vm_fixture.__name__)
    def test_sparse_cow_virtio_data_disk(self):
        """
        Add sparse cow virtio data disk to vm
        """

        testflow.step("Add new VM with sparse cow virtio data disk")
        assert ll_vms.addDisk(
            True,
            vm=self.vm_name,
            provisioned_size=config.GB,
            storagedomain=self.master_domain,
            type=config.DISK_TYPE_DATA,
            format=config.DISK_FORMAT_COW,
            interface=config.INTERFACE_VIRTIO,
            sparse=True
        )

    @attr(tier=2)
    @polarion("RHEVM3-12571")
    @pytest.mark.usefixtures(add_vm_fixture.__name__)
    @pytest.mark.skipif(config.PPC_ARCH, reason=config.PPC_SKIP_MESSAGE)
    def test_different_interfaces_and_formats(self):
        """
        Add disks to vm with different interfaces and formats
        """

        testflow.step("Add new vm with different interfaces and formats")
        for disk_interface in [config.INTERFACE_VIRTIO, config.INTERFACE_IDE]:
            for disk_format in [
                config.DISK_FORMAT_COW,
                config.DISK_FORMAT_RAW
            ]:
                testflow.step(
                    "Add data disk to vm %s with format %s and interface %s",
                    self.vm_name, disk_format, disk_interface
                )
                result = ll_vms.addDisk(
                    True,
                    vm=self.vm_name,
                    provisioned_size=config.GB,
                    storagedomain=self.master_domain,
                    type=config.DISK_TYPE_DATA,
                    format=disk_format,
                    interface=disk_interface
                )
                assert result

    @attr(tier=1)
    @polarion("RHEVM3-12583")
    @pytest.mark.usefixtures(basic_teardown_fixture.__name__)
    def test_vm_template(self):
        """
        Create vm from template
        """

        testflow.step("Create new vm from template")
        assert ll_vms.addVm(
            True,
            name=self.vm_name,
            cluster=config.CLUSTER_NAME[0],
            template=config.TEMPLATE_NAME[0]
        )

    @attr(tier=1)
    @polarion("RHEVM3-12584")
    @pytest.mark.usefixtures(basic_teardown_fixture.__name__)
    def test_template_with_specific_sd(self):
        """
        Create new vm with specified storage domain
        """

        testflow.step("Create new vm with specified storage domain")
        assert ll_vms.addVm(
            True,
            name=self.vm_name,
            cluster=config.CLUSTER_NAME[0],
            template=self.template_name,
            storagedomain=self.master_domain
        )

    @attr(tier=1)
    @polarion("RHEVM3-12585")
    @pytest.mark.usefixtures(add_template_fixture.__name__)
    def test_template_with_wrong_sd(self):
        """
        Negative: Create new vm with wrong storage domain
        """
        template_base = 'template_virt'
        testflow.step("Negative: Create new vm with wrong storage domain")
        assert not ll_vms.addVm(
            positive=True,
            name=self.vm_name,
            cluster=config.CLUSTER_NAME[0],
            template=template_base,
            storagedomain=self.non_master_domain
        )

    @attr(tier=1)
    @polarion("RHEVM3-12582")
    @pytest.mark.usefixtures(basic_teardown_fixture.__name__)
    def test_clone_vm_from_template(self):
        """
        Clone vm from template
        """

        testflow.step("Clone vm from template")
        assert ll_vms.cloneVmFromTemplate(
            positive=True,
            name=self.vm_name,
            template=self.template_name,
            cluster=config.CLUSTER_NAME[0]
        )


@attr(tier=1)
@pytest.mark.usefixtures(vm_display_fixture.__name__)
@pytest.mark.skipif(config.PPC_ARCH, reason=config.PPC_SKIP_MESSAGE)
class VmDisplay(VirtTest):
    """
    Create vms with different display types, run it and check
    if address and port appear under display options
    """
    __test__ = True

    display_types = [
        config.ENUMS['display_type_spice'],
        config.ENUMS['display_type_vnc']
    ]
    vm_names = ['%s_vm' % display_type for display_type in display_types]

    @polarion("RHEVM3-12574")
    def test_check_spice_parameters(self):
        """
        Check address and port parameters under display with type spice
        """
        testflow.step("Set spice and check address and port")
        assert helper.check_display_parameters(self.vm_names[0], config.SPICE)

    @polarion("RHEVM3-12575")
    def test_check_vnc_parameters(self):
        """
        Check address and port parameters under display with type vnc
        """
        testflow.step("Set vnc and check address and port")
        assert helper.check_display_parameters(self.vm_names[1], config.VNC)
