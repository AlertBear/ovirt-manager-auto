#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Testing network VM QoS feature.
1 DC, 1 Cluster, 2 Hosts and 1 VM will be created for testing.
Create, update, remove and migration tests will be done for Network QoS feature
"""

import logging

import pytest

import art.rhevm_api.tests_lib.low_level.datacenters as ll_datacenters
import art.rhevm_api.tests_lib.low_level.networks as ll_networks
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import config as qos_conf
import helper
import rhevmtests.networking.config as conf
from art.test_handler.tools import polarion
from art.unittest_lib import (
    tier2,
)
from art.unittest_lib import NetworkTest, testflow
from fixtures import add_qos_to_dc_and_qos_profile_to_nic
from rhevmtests.fixtures import start_vm

logger = logging.getLogger("Network_VNIC_QoS_Tests")


@pytest.mark.incremental
@pytest.mark.usefixtures(
    add_qos_to_dc_and_qos_profile_to_nic.__name__,
    start_vm.__name__
)
class TestNetQOSCase01(NetworkTest):
    """
    Add new network QOS
    """
    __test__ = True
    qos_name_1 = qos_conf.QOS_NAME[1][0]
    qos_name_2 = qos_conf.QOS_NAME[1][1]
    new_qos_name = "network_qos_new_qos"
    vnic_profile_1 = qos_conf.VNIC_NAME[1][0]
    vnic_profile_2 = qos_conf.VNIC_NAME[1][1]
    vm_name = conf.VM_0
    vms = [conf.VM_0, conf.VM_1]
    start_vms_dict = {
        vm_name: {}
    }
    vms_to_stop = vms

    @tier2
    @polarion("RHEVM3-3998")
    def test_01_add_network_qos(self):
        """
        1) Create new Network QoS profile under DC
        2) Provide Inbound and Outbound parameters for this QOS
        3) Create VNIC profile with configured QoS and add it to the NIC of
        the VM
        4) Check that provided bw values are the same as the values
        configured on libvirt
        """
        dict_compare = helper.build_dict(
            inbound_dict=qos_conf.INBOUND_DICT,
            outbound_dict=qos_conf.OUTBOUND_DICT, vm=conf.VM_0,
            nic=conf.VM_NIC_1
        )
        testflow.step(
            "Compare provided QoS %s and %s exists with libvirt values",
            qos_conf.INBOUND_DICT, qos_conf.OUTBOUND_DICT
        )
        assert helper.compare_qos(vm_name=conf.VM_0, **dict_compare)

    @tier2
    @polarion("RHEVM3-19152")
    def test_02_several_network_qos(self):
        """
        1) Check that provided bw values are the same as the values
        configured on libvirt for QoSProfile1
        2) Check that provided bw values are different from the values
        configured on libvirt for QoSProfile2
        3) Restart VM
        4) Check that provided bw values are the same as the values
        configured on libvirt for QoSProfile2 and QoSProfile1
        """
        assert ll_networks.add_vnic_profile(
            positive=True, name=self.vnic_profile_2, data_center=conf.DC_0,
            network=conf.MGMT_BRIDGE
        )
        assert ll_vms.addNic(
            positive=True, vm=conf.VM_0, name=conf.VM_NIC_2,
            network=conf.MGMT_BRIDGE, vnic_profile=self.vnic_profile_2
        )
        assert ll_networks.update_qos_on_vnic_profile(
            datacenter=conf.DC_0, qos_name=self.qos_name_2,
            vnic_profile_name=self.vnic_profile_2,
            network_name=conf.MGMT_BRIDGE
        )
        dict_compare = helper.build_dict(
            inbound_dict=qos_conf.INBOUND_DICT,
            outbound_dict=qos_conf.OUTBOUND_DICT, vm=conf.VM_0,
            nic=conf.VM_NIC_2
        )
        testflow.step(
            "Compare provided QoS %s and %s are not equal to libvirt values"
            "when Network QoS %s was updated after the VNIC profile "
            "%s already existed on VM",
            qos_conf.INBOUND_DICT, qos_conf.OUTBOUND_DICT, self.qos_name_2,
            self.vnic_profile_2
        )
        assert not helper.compare_qos(vm_name=conf.VM_0, **dict_compare)
        testflow.step("Restart VM %s", conf.VM_0)
        assert ll_vms.restartVm(
            vm=conf.VM_0, placement_host=conf.HOST_0_NAME
        )
        testflow.step(
            "Check that after restart VM the QoS %s is equal to "
            "libvirt values", self.qos_name_2
        )
        assert helper.compare_qos(vm_name=conf.VM_0, **dict_compare)

    @tier2
    @polarion("RHEVM3-3999")
    def test_03_update_network_qos(self):
        """
        1) Update existing QoS profile for DC
        2) Change the name of QoS and provide Inbound and
        Outbound parameters different than before
        3) Check that for VM that is down, the specific VNIC profile got
        the changes of QoS (when started)
        4) Check that VM that is up will get the change of VNIC profile
         after the VM reboot (or unplug/plug)
        """
        testflow.step("Update existing Network QoS profile under DC")
        assert ll_datacenters.update_qos_in_datacenter(
            datacenter=conf.DC_0, qos_name=self.qos_name_1,
            new_name=self.new_qos_name,
            inbound_average=qos_conf.UPDATED_BW_PARAMS[0],
            inbound_peak=qos_conf.UPDATED_BW_PARAMS[1],
            inbound_burst=qos_conf.UPDATED_BW_PARAMS[2],
            outbound_average=qos_conf.UPDATED_BW_PARAMS[0],
            outbound_peak=qos_conf.UPDATED_BW_PARAMS[1],
            outbound_burst=qos_conf.UPDATED_BW_PARAMS[2]
        )
        dict_compare = helper.build_dict(
            inbound_dict=qos_conf.INBOUND_DICT_UPDATE,
            outbound_dict=qos_conf.OUTBOUND_DICT_UPDATE, vm=conf.VM_0,
            nic=conf.VM_NIC_1
        )
        testflow.step(
            "Check provided QoS %s and %s doesn't match libvirt values",
            qos_conf.INBOUND_DICT_UPDATE, qos_conf.OUTBOUND_DICT_UPDATE
        )
        assert not helper.compare_qos(vm_name=conf.VM_0, **dict_compare)
        assert ll_vms.addNic(
            positive=True, vm=conf.VM_1, name=conf.VM_NIC_1,
            network=conf.MGMT_BRIDGE, vnic_profile=self.vnic_profile_1
        )
        testflow.step(
            "Start vm %s on host %s", conf.VM_1, conf.HOST_0_NAME
        )
        assert ll_vms.startVm(
            positive=True, vm=conf.VM_1, placement_host=conf.HOST_0_NAME
        )
        testflow.step(
            "Unplug and plug %s on %s", conf.VM_NIC_1, conf.VM_0
        )
        assert ll_vms.updateNic(
            positive=True, vm=conf.VM_0, nic=conf.VM_NIC_1, plugged="false"
        )
        assert ll_vms.updateNic(
            positive=True, vm=conf.VM_0, nic=conf.VM_NIC_1, plugged="true"
        )
        testflow.step(
            "Check that provided QoS values %s and %s are equal to what was"
            " found on libvirt for both VMs", qos_conf.INBOUND_DICT,
            qos_conf.OUTBOUND_DICT
        )
        for vm in self.vms:
            assert helper.compare_qos(vm_name=vm, **dict_compare)

    @tier2
    @polarion("RHEVM-19153")
    def test_04_migrate_network_qos(self):
        """
        1) Check that provided bw values are the same as the values
        configured on libvirt
        2) Migrate VM to another Host
        3) Check that provided bw values are the same as the values
        configured on libvirt after migration
        """
        dict_compare = helper.build_dict(
            inbound_dict=qos_conf.INBOUND_DICT_UPDATE,
            outbound_dict=qos_conf.OUTBOUND_DICT_UPDATE, vm=conf.VM_1,
            nic=conf.VM_NIC_1
        )
        testflow.step("Migrate VM %s", conf.VM_1)
        assert ll_vms.migrateVm(positive=True, vm=conf.VM_1)
        testflow.step(
            "Compare provided QoS %s and %s exists with libvirt values",
            qos_conf.INBOUND_DICT_UPDATE, qos_conf.OUTBOUND_DICT_UPDATE
        )
        assert helper.compare_qos(vm_name=conf.VM_1, **dict_compare)

    @tier2
    @polarion("RHEVM3-4000")
    def test_05_remove_network_qos(self):
        """
        1) Remove QoS profile
        2) Check that the change is applicable on the VM that is up after
        unplug/plug
        """
        testflow.step("Remove the QoS from DC")
        assert ll_datacenters.delete_qos_from_datacenter(
            datacenter=conf.DC_0, qos_name=self.new_qos_name
        )
        dict_compare = helper.build_dict(
            inbound_dict={}, outbound_dict={}, vm=conf.VM_0, nic=conf.VM_NIC_1
        )
        testflow.step(
            "Check that after deletion of QoS libvirt is not updated with "
            "unlimited values till plug/unplug action"
        )
        assert not helper.compare_qos(vm_name=conf.VM_0, **dict_compare)
        testflow.step("Unplug and plug NIC on %s", conf.VM_0)
        assert ll_vms.updateNic(
            positive=True, vm=conf.VM_0, nic=conf.VM_NIC_1, plugged="false"
        )
        assert ll_vms.updateNic(
            positive=True, vm=conf.VM_0, nic=conf.VM_NIC_1, plugged="true"
        )
        testflow.step(
            "Check that libvirt Network QoS values were updated to be "
            "unlimited"
        )
        for vm, host in zip(self.vms, [conf.VDS_0_HOST, conf.VDS_1_HOST]):
            assert helper.compare_qos(vm_name=vm, **dict_compare)
