#! /usr/bin/python
# -*- coding: utf-8 -*-

# Virt VMs: RHEVM3/wiki/Compute/Virt_VMs

import logging

import pytest

import art.rhevm_api.tests_lib.low_level.templates as ll_templates
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import config
import rhevmtests.compute.virt.helper as helper
from art.rhevm_api.utils import test_utils
from art.test_handler.settings import ART_CONFIG
from art.test_handler.tools import polarion
from art.unittest_lib import VirtTest, testflow
from art.unittest_lib import (
    tier1,
    tier2,
)
from fixtures import (
    add_vm_fixture, basic_teardown_fixture,
    create_vm_and_template_with_small_disk, vm_display_fixture,
    add_vm_from_template_fixture
)

logger = logging.getLogger("vm_mix_cases")
NFS = ART_CONFIG['elements_conf']['RHEVM Enums']['storage_type_nfs']


class TestMixCases(VirtTest):

    storages = set([NFS])
    cluster_name = config.CLUSTER_NAME[0]
    template_name = config.TEMPLATE_NAME[0]
    vm_name = config.MIX_CASE_TEST
    add_disk = True
    vm_parameters = None
    VM_DISK_CLONE_TIMEOUT = 1500
    master_domain, export_domain, non_master_domain = (
        helper.get_storage_domains()
    )

    @tier1
    @polarion("RHEVM3-12522")
    @pytest.mark.usefixtures(add_vm_fixture.__name__)
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

    @tier1
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

    @tier1
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

    @tier2
    @polarion("RHEVM3-12524")
    @pytest.mark.usefixtures(add_vm_fixture.__name__)
    def test_vm_statistics(self):
        """
        Add vm and check vm stats
        """
        testflow.step("Check vm %s statistics", self.vm_name)
        assert ll_vms.checkVmStatistics(True, self.vm_name)

    @tier2
    @polarion("RHEVM3-12577")
    @pytest.mark.usefixtures(add_vm_fixture.__name__)
    def test_network_vm(self):
        """
        Create, update and remove vm nic
        """
        testflow.step("Add nic %s to vm %s", config.NIC_NAME[0], self.vm_name)
        assert ll_vms.addNic(
            True, vm=self.vm_name,
            name=config.NIC_NAME[0],
            network=config.MGMT_BRIDGE
        )
        testflow.step(
            "Add additional nic %s to vm %s", config.NIC_NAME[1], self.vm_name
        )

        assert ll_vms.addNic(
            True, vm=self.vm_name,
            name=config.NIC_NAME[1],
            network=config.MGMT_BRIDGE
        )
        testflow.step(
            "Update nic %s name to %s", config.NIC_NAME[1], config.NIC_NAME[2]
        )
        assert ll_vms.updateNic(
            True, vm=self.vm_name,
            nic=config.NIC_NAME[1], name=config.NIC_NAME[2]
        )
        testflow.step(
            "Remove nic %s from vm %s", config.NIC_NAME[2], self.vm_name
        )
        assert ll_vms.removeNic(
            True, vm=self.vm_name,
            nic=config.NIC_NAME[2]
        )

    @tier2
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

    @tier2
    @polarion("RHEVM3-12571")
    @pytest.mark.usefixtures(add_vm_fixture.__name__)
    def test_different_interfaces_and_formats(self):
        """
        Add disks to vm with different interfaces and formats
        """

        testflow.step("Add new vm with different interfaces and formats")
        disk_interfaces = [config.INTERFACE_VIRTIO]
        if not config.PPC_ARCH:
            disk_interfaces.append(config.INTERFACE_IDE)
        for disk_interface in disk_interfaces:
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

    @tier1
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

    @tier1
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

    @tier1
    @polarion("RHEVM3-12585")
    @pytest.mark.usefixtures(create_vm_and_template_with_small_disk.__name__)
    def test_template_with_wrong_sd(self):
        """
        Negative: Create new vm with wrong storage domain
        """
        testflow.step("Negative: Create new vm with wrong storage domain")
        assert not ll_vms.addVm(
            positive=True,
            name=self.vm_name,
            cluster=config.CLUSTER_NAME[0],
            template=config.BASE_TEMPLATE,
            storagedomain=self.non_master_domain
        )


@pytest.mark.usefixtures(vm_display_fixture.__name__)
class TestVmDisplay(VirtTest):
    """
    Create vms with different display types, run it and check
    if address and port appear under display options
    """
    display_types = [config.ENUMS['display_type_vnc']]
    if not config.PPC_ARCH:
        display_types.append(config.ENUMS['display_type_spice'])
    vm_names = {
        display_type: '%s_vm' % display_type for display_type in display_types
        }

    @tier1
    @pytest.mark.skipif(config.PPC_ARCH, reason=config.PPC_SKIP_MESSAGE)
    @polarion("RHEVM3-12574")
    def test_check_spice_parameters(self):
        """
        Check address and port parameters under display with type spice
        """
        testflow.step("Set spice and check address and port")
        assert helper.check_display_parameters(
            self.vm_names[config.SPICE], config.SPICE
        )

    @tier1
    @polarion("RHEVM3-12575")
    def test_check_vnc_parameters(self):
        """
        Check address and port parameters under display with type vnc
        """
        testflow.step("Set vnc and check address and port")
        assert helper.check_display_parameters(
            self.vm_names[config.VNC], config.VNC
        )


@pytest.mark.usefixtures(add_vm_from_template_fixture.__name__)
class TestLockVM(VirtTest):
    __test__ = True
    base_vm_name = 'lock_vm_test'
    cluster_name = config.CLUSTER_NAME[0]
    template_name = config.TEMPLATE_NAME[0]
    add_disk = True

    @tier2
    @polarion("RHEVM3-12587")
    def test_locked_vm(self):
        """
        Change vm status in database to locked and try to remove it
        """
        testflow.step("remove locked vm")
        test_utils.update_vm_status_in_database(
            self.base_vm_name,
            vdc=config.VDC_HOST,
            status=int(config.ENUMS['vm_status_locked_db']),
            vdc_pass=config.VDC_ROOT_PASSWORD
        )
        test_utils.wait_for_tasks(config.ENGINE, config.DC_NAME[0])
        assert ll_vms.remove_locked_vm(
            self.base_vm_name,
            vdc=config.VDC_HOST,
            vdc_pass=config.VDC_ROOT_PASSWORD
        )


class TestAddQcowDisk(VirtTest):

    __test__ = True

    vm_name = config.MIX_CASE_TEST
    add_disk = False
    master_domain, _, _ = helper.get_storage_domains()

    @tier2
    @polarion("RHEVM3-12573")
    @pytest.mark.usefixtures(add_vm_fixture.__name__)
    def test_sparse_cow_virtio_data_disk(self):
        """
        Add sparse cow virtio data disk to vm
        """

        testflow.step(
            "Adding a new qcow2 disk with virtio interface to vm: %s",
            self.vm_name
        )
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

    @tier2
    @polarion("RHEVM3-12568")
    @pytest.mark.usefixtures(add_vm_fixture.__name__)
    @pytest.mark.skipif(config.PPC_ARCH, reason=config.PPC_SKIP_MESSAGE)
    def test_add_bootable_cow_ide_data_disk(self):
        """
        Add bootable cow ide data disk to vm
        """

        testflow.step(
            "Adding a new qcow2 disk with ide interface to vm: %s",
            self.vm_name
        )
        assert ll_vms.addDisk(
            True,
            vm=self.vm_name,
            provisioned_size=config.GB,
            storagedomain=self.master_domain,
            type=config.DISK_TYPE_DATA,
            format=config.DISK_FORMAT_COW,
            interface=config.INTERFACE_IDE,
            bootable=True,
            wipe_after_delete=True
        )
