#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Tests for Multiple Queue NICs feature

The following elements will be used for the tests:
VM from template, vNIC, vNIC profile
"""

import pytest

from art.rhevm_api.tests_lib.low_level import (
    networks as ll_networks,
    vms as ll_vms
)
import rhevmtests.networking.config as conf
import rhevmtests.networking.helper as network_helper
import rhevmtests.networking.multiple_queue_nics.config as multiple_queue_conf
from art.test_handler.tools import bz, polarion
from art.unittest_lib import (
    tier2,
    NetworkTest,
    testflow,
)
from rhevmtests.fixtures import start_vm
from fixtures import create_vm
from rhevmtests.networking.fixtures import (
    update_vnic_profiles,
    add_vnics_to_vms,
    remove_vnics_from_vms
)


@pytest.mark.incremental
@pytest.mark.usefixtures(
    update_vnic_profiles.__name__,
    start_vm.__name__
)
class TestMultipleQueueNics01(NetworkTest):
    """
    1) Verify that number of queues is not updated on running VM and check
        that number of queues is updated on new VM boot.
    2) Check that queue survive VM hibernate
    3) Check that queues survive VM migration
    """
    # General params
    vm_name = conf.LAST_VM
    num_queues_0 = multiple_queue_conf.NUM_QUEUES[0]
    num_queues_1 = multiple_queue_conf.NUM_QUEUES[1]
    prop_queues = multiple_queue_conf.PROP_QUEUES[1]

    # update_vnic_profiles params
    update_vnics_profiles = {
        conf.MGMT_BRIDGE: {
            "custom_properties": multiple_queue_conf.PROP_QUEUES[0],
            "data_center": conf.DC_0,
        }
    }

    restore_vnics_profiles = {
        conf.MGMT_BRIDGE: {
            "custom_properties": "clear",
            "data_center": conf.DC_0,
        }
    }

    # start_vm params
    start_vms_dict = {
        vm_name: {}
    }

    @tier2
    @bz({"1479808": {}})
    @polarion("RHEVM3-4310")
    def test_01_multiple_queue_nics_update(self):
        """
        1.  Update queues while VM is running.
        2.  Make sure that number of queues does not change on running VM.
        3.  Stop VM.
        4.  Start VM.
        5.  Make sure number of queues changed on new boot.
        """
        testflow.step(
            "Update custom properties on %s to %s", conf.MGMT_BRIDGE,
            self.prop_queues
        )
        assert ll_networks.update_vnic_profile(
            name=conf.MGMT_BRIDGE, network=conf.MGMT_BRIDGE,
            data_center=conf.DC_0, custom_properties=self.prop_queues
        )
        testflow.step(
            "Check that qemu still has %s queues after properties update",
            self.num_queues_0
        )
        assert network_helper.check_queues_from_qemu(
            vm=self.vm_name, num_queues=self.num_queues_0
        )
        testflow.step("Restart VM %s", self.vm_name)
        assert ll_vms.restartVm(vm=self.vm_name)
        testflow.step("Check that qemu has %s queues", self.num_queues_1)
        assert network_helper.check_queues_from_qemu(
            vm=self.vm_name, num_queues=self.num_queues_1
        )

    @tier2
    @polarion("RHEVM3-4312")
    def test_02_multiple_queue_nics(self):
        """
        Hibernate the VM and check the queue still configured on qemu
        """
        testflow.step("Suspend %s", self.vm_name)
        assert ll_vms.suspendVm(positive=True, vm=self.vm_name)

        testflow.step("Start %s", self.vm_name)
        assert ll_vms.startVm(positive=True, vm=self.vm_name)
        testflow.step("Check that qemu has %s queues", self.num_queues_1)
        assert network_helper.check_queues_from_qemu(
            vm=self.vm_name, num_queues=self.num_queues_1
        )

    @tier2
    @polarion("RHEVM3-4311")
    def test_03_multiple_queue_nics_vm_migration(self):
        """
        Check number of queues after VM migration
        """
        testflow.step("Migrate Vm %s", self.vm_name)
        assert ll_vms.migrateVm(positive=True, vm=self.vm_name)
        testflow.step(
            "Check that qemu has %s queues after VM migration",
            self.num_queues_1
        )
        assert network_helper.check_queues_from_qemu(
            vm=self.vm_name, num_queues=self.num_queues_1
        )


@pytest.mark.incremental
@pytest.mark.usefixtures(
    update_vnic_profiles.__name__,
    create_vm.__name__,
    add_vnics_to_vms.__name__,
    remove_vnics_from_vms.__name__,
    start_vm.__name__
)
class TestMultipleQueueNics02(NetworkTest):
    """
    1.  Check queue exists for VM from template
    2.  Check hot-unplug vNIC with custom queues property
    """
    # General params
    num_queues_0 = multiple_queue_conf.NUM_QUEUES[0]

    # create_vm params
    vm_name = multiple_queue_conf.VM_FROM_TEMPLATE
    vm_nic = multiple_queue_conf.VM_NIC

    # add_vnics_to_vms fixture params
    add_vnics_vms_params = {
        vm_name: {
            "1": {
                "name": vm_nic,
                "network": conf.MGMT_BRIDGE,
                "vnic_profile": conf.MGMT_BRIDGE,
                "plugged": True
            }
        }
    }
    # remove_vnics_from_vms params
    remove_vnics_vms_params = add_vnics_vms_params

    # update_vnic_profiles params
    update_vnics_profiles = {
        conf.MGMT_BRIDGE: {
            "custom_properties": multiple_queue_conf.PROP_QUEUES[0],
            "data_center": conf.DC_0,
        }
    }

    restore_vnics_profiles = {
        conf.MGMT_BRIDGE: {
            "custom_properties": "clear",
            "data_center": conf.DC_0,
        }
    }

    # start_vm params
    start_vms_dict = {
        vm_name: {}
    }

    @tier2
    @polarion("RHEVM-16866")
    def test_hot_unplug_with_custom_queues(self):
        """
        Check hot-unplug vNIC with custom queues property
        """
        testflow.step("Check hot-unplugging vNIC with queues custom property")
        assert ll_vms.updateNic(
            positive=True, vm=self.vm_name, nic=self.vm_nic, plugged="false"
        )

    @tier2
    @bz({"1478054": {}})
    @polarion("RHEVM3-4313")
    def test_multiple_queue_nics(self):
        """
        Check that queue exist on VM from template
        """
        testflow.step("Check that qemu has %s queues", self.num_queues_0)
        assert network_helper.check_queues_from_qemu(
            vm=self.vm_name, num_queues=self.num_queues_0
        )
