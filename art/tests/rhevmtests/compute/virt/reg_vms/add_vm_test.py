#! /usr/bin/python
# -*- coding: utf-8 -*-

# Virt VMs: /RHEVM3/wiki/Compute/Virt_VMs

import pytest

import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import config
import rhevmtests.compute.virt.helper as helper
import rhevmtests.helpers as gen_helper
from art.test_handler.tools import polarion
from art.unittest_lib import VirtTest, testflow
from art.unittest_lib import (
    tier1
)
from fixtures import (
    basic_teardown_fixture
)


class TestAddVm(VirtTest):
    """
    Add vms with different parameters test cases
    """
    vm_name = config.ADD_VM_TEST
    vm_parameters = {
        'cluster': config.CLUSTER_NAME[0],
        'os_type': config.VM_OS_TYPE,
        'type': config.VM_TYPE,
        'display_type': config.VM_DISPLAY_TYPE
    }
    master_domain, export_domain, non_master_domain = (
        helper.get_storage_domains()
    )

    @tier1
    @polarion("RHEVM3-12382")
    @pytest.mark.usefixtures(basic_teardown_fixture.__name__)
    def test_custom_boot_sequence(self):
        """
        Add vm with custom boot sequence
        """
        testflow.step("Add vm with custom boot sequence")
        vm_parameters = self.vm_parameters.copy()
        vm_parameters['name'] = self.vm_name
        vm_parameters['boot'] = ['network', 'hd']
        assert ll_vms.addVm(True, **vm_parameters)

        testflow.step(
            "Check if network first and hard disk second "
            "in boot sequence on vm %s", self.vm_name
        )
        boot_list = ll_vms.get_vm_boot_sequence(self.vm_name)
        assert boot_list[0] == config.ENUMS['boot_sequence_network'] and (
            boot_list[1] == config.ENUMS['boot_sequence_hd']
        )

    @tier1
    @polarion("RHEVM3-10087")
    @pytest.mark.usefixtures(basic_teardown_fixture.__name__)
    def test_default_vm(self):
        """
        Positive: Add default vm without special parameters
        """
        testflow.step("Positive: Add default vm without special parameters")
        vm_parameters = self.vm_parameters.copy()
        vm_parameters['name'] = self.vm_name

        assert ll_vms.addVm(True, **vm_parameters)

    @tier1
    @polarion("RHEVM3-12361")
    @pytest.mark.usefixtures(basic_teardown_fixture.__name__)
    def test_ha_server_vm(self):
        """
        Positive: Add HA server vm
        """
        testflow.step("Positive: Add HA server vm")
        vm_parameters = self.vm_parameters.copy()
        vm_parameters['name'] = self.vm_name
        vm_parameters['highly_available'] = 'true'
        vm_parameters['vm_type'] = config.ENUMS['vm_type_server']

        assert ll_vms.addVm(True, **vm_parameters)

    @tier1
    @polarion("RHEVM3-12363")
    @pytest.mark.usefixtures(basic_teardown_fixture.__name__)
    def test_custom_property(self):
        """
        Positive: Add vm with custom property
        """
        testflow.step("Positive: Add vm with custom property")
        vm_parameters = self.vm_parameters.copy()
        vm_parameters['name'] = self.vm_name
        vm_parameters['custom_properties'] = 'sndbuf=111'

        assert ll_vms.addVm(True, **vm_parameters)

    @tier1
    @polarion("RHEVM3-12385")
    @pytest.mark.usefixtures(basic_teardown_fixture.__name__)
    def test_guaranteed_memory(self):
        """
        Positive: Add vm with guaranteed memory
        """
        testflow.step("Positive: Add vm with guaranteed memory")
        vm_parameters = self.vm_parameters.copy()
        vm_parameters['name'] = self.vm_name
        vm_parameters['memory'] = config.TWO_GB
        vm_parameters['max_memory'] = gen_helper.get_gb(2)
        vm_parameters['memory_guaranteed'] = config.TWO_GB

        assert ll_vms.addVm(True, **vm_parameters)

    @tier1
    @polarion("RHEVM3-12383")
    @pytest.mark.usefixtures(basic_teardown_fixture.__name__)
    def test_disk_vm(self):
        """
        Positive: Add vm with disk
        """
        testflow.step("Positive: Add vm with disk")
        vm_parameters = self.vm_parameters.copy()
        vm_parameters['name'] = self.vm_name
        vm_parameters['disk_type'] = config.DISK_TYPE_DATA
        vm_parameters['provisioned_size'] = config.TWO_GB
        vm_parameters['format'] = config.DISK_FORMAT_COW
        vm_parameters['interface'] = config.INTERFACE_VIRTIO

        assert ll_vms.addVm(True, **vm_parameters)

    @tier1
    @polarion("RHEVM3-12517")
    @pytest.mark.usefixtures(basic_teardown_fixture.__name__)
    def test_linux_boot_options(self):
        """
        Positive: Add vm with linux_boot_options
        """
        testflow.step("Positive: Add vm with linux_boot_options")
        vm_parameters = self.vm_parameters.copy()
        vm_parameters['name'] = self.vm_name
        vm_parameters['kernel'] = '/kernel-path'
        vm_parameters['initrd'] = '/initrd-path'
        vm_parameters['cmdline'] = 'rd_NO_LUKS rd_NO_MD'

        assert ll_vms.addVm(True, **vm_parameters)

    @tier1
    @polarion("RHEVM3-12518")
    @pytest.mark.usefixtures(basic_teardown_fixture.__name__)
    def test_rhel_os(self):
        """
        Add vm with Rhel OS type
        """
        testflow.step("Add vm with Rhel OS type")
        vm_parameters = self.vm_parameters.copy()
        vm_parameters['name'] = self.vm_name
        vm_parameters['os_type'] = (
            config.RHEL7PPC64 if config.PPC_ARCH else config.RHEL6_64
        )
        assert ll_vms.addVm(True, **vm_parameters)

    @tier1
    @polarion("RHEVM3-12520")
    @pytest.mark.usefixtures(basic_teardown_fixture.__name__)
    @pytest.mark.skipif(config.PPC_ARCH, reason=config.PPC_SKIP_MESSAGE)
    def test_windows_7_os(self):
        """
        Positive: Add vm with Windows 7 OS type
        """
        testflow.step("Positive: Add vm with Windows 7 OS type")
        vm_parameters = self.vm_parameters.copy()
        vm_parameters['name'] = self.vm_name
        vm_parameters['os_type'] = config.WIN_7
        assert ll_vms.addVm(True, **vm_parameters)

    @tier1
    @polarion("RHEVM3-12384")
    @pytest.mark.usefixtures(basic_teardown_fixture.__name__)
    def test_disk_on_specific_storage_domain(self):
        """
        Positive: Add vm with disk on specific storage domain
        """
        testflow.step("Positive: Add vm with disk on specific storage domain")
        vm_parameters = self.vm_parameters.copy()
        vm_parameters['name'] = self.vm_name
        vm_parameters['storagedomain'] = self.master_domain
        vm_parameters['disk_type'] = config.DISK_TYPE_DATA
        vm_parameters['provisioned_size'] = config.TWO_GB
        vm_parameters['interface'] = config.INTERFACE_VIRTIO
        assert ll_vms.addVm(True, **vm_parameters)

    @tier1
    @polarion("RHEVM3-12519")
    @pytest.mark.usefixtures(basic_teardown_fixture.__name__)
    def test_specific_domain(self):
        """
        Positive: Add vm with specific domain
        """
        testflow.step("Positive: Add vm with specific domain")
        vm_parameters = self.vm_parameters.copy()
        vm_parameters['name'] = self.vm_name
        vm_parameters['storagedomain'] = self.master_domain
        vm_parameters['disk_type'] = config.DISK_TYPE_DATA
        assert ll_vms.addVm(True, **vm_parameters)

    @tier1
    @polarion("RHEVM3-12386")
    @pytest.mark.usefixtures(basic_teardown_fixture.__name__)
    def test_name_that_already_exist(self):
        """
        Negative: Add vm with name that already in use
        """
        testflow.step("Negative: Add vm with name that already in use")
        vm_parameters = self.vm_parameters.copy()
        vm_parameters['name'] = self.vm_name
        assert ll_vms.addVm(True, **vm_parameters)
        testflow.step("Create vm with name that already exist")
        assert not ll_vms.addVm(True, **vm_parameters)

    @tier1
    @polarion("RHEVM3-12521")
    @pytest.mark.usefixtures(basic_teardown_fixture.__name__)
    def test_wrong_number_of_displays(self):
        """
        Negative: Add vm with wrong number of displays
        """
        testflow.step("Negative: Add vm with wrong number of displays")
        vm_parameters = self.vm_parameters.copy()
        vm_parameters['name'] = self.vm_name
        vm_parameters['monitors'] = 36
        assert not ll_vms.addVm(True, **vm_parameters)

    @tier1
    @polarion("RHEVM-14952")
    @pytest.mark.usefixtures(basic_teardown_fixture.__name__)
    def test_add_vm_with_wrong_name(self):
        """
        Negative: Add vm with wrong name use special characters
        """
        testflow.step(
            "Negative: Add vm with wrong name use special characters"
        )
        vm_name = "wrong_name+*////*_VM"
        vm_parameters = self.vm_parameters.copy()
        vm_parameters['name'] = vm_name
        assert not ll_vms.addVm(True, **vm_parameters)

    @tier1
    @polarion("RHEVM-14953")
    @pytest.mark.usefixtures(basic_teardown_fixture.__name__)
    @pytest.mark.skipif(config.PPC_ARCH, reason=config.PPC_SKIP_MESSAGE)
    def test_add_and_remove_win_vm_name_long(self):
        """
        Positive: Add vm with windows os and nome long the 40 characters
        """
        testflow.step(
            "Positive: Add vm with windows os and nome long the 40 characters"
        )
        vm_name = 'a' * 40
        vm_parameters = self.vm_parameters.copy()
        vm_parameters['name'] = vm_name
        vm_parameters['os_type'] = config.WIN_7
        assert ll_vms.addVm(True, **vm_parameters)
        testflow.step("Remove vm with long name")
        assert ll_vms.safely_remove_vms([vm_name])

    @tier1
    @polarion("RHEVM-17023")
    @pytest.mark.usefixtures(basic_teardown_fixture.__name__)
    def test_vm_with_wrong_length_name(self):
        """
        Negative: Add vm with name longer then 65 characters
        """
        testflow.step("Negative: Add vm with name longer then 65 characters")
        vm_name = 'a' * 66
        vm_parameters = self.vm_parameters.copy()
        vm_parameters['name'] = vm_name
        assert not ll_vms.addVm(True, **vm_parameters)

    @tier1
    @polarion("RHEVM-15002")
    def test_add_vm_with_long_name_crud(self):
        """
        Positive: Add vm with name equals to 64 characters
                  check that we can update, run, remove  VM
        """
        testflow.step(
            "Positive: Add vm with name equals to 64 characters"
            "check that we can update, run, remove  VM"
        )
        cluster_name = config.CLUSTER_NAME[0]
        template_name = config.TEMPLATE_NAME[0]
        vm_name = 'a' * 64

        assert helper.create_vm_from_template(
            vm_name=vm_name,
            cluster=cluster_name,
            template=template_name), "Failed to add vm with 64 characters"
        assert ll_vms.updateVm(
            positive=True, vm=vm_name,
            description="TEST"
        ), "Failed to update VM"
        assert ll_vms.startVm(
            positive=True, vm=vm_name,
            wait_for_status=config.VM_UP
        ), "Failed to run VM"
        assert ll_vms.safely_remove_vms([vm_name]), "Failed to remove VM"
