#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Fixtures for network QoS
"""

import pytest

import art.rhevm_api.tests_lib.low_level.datacenters as ll_datacenters
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import config as qos_conf
import helper
from rhevmtests import networking
from rhevmtests.networking import helper as network_helper
from rhevmtests.networking.fixtures import NetworkFixtures


@pytest.fixture(scope="class")
def case_01_fixture(request):
    """
    Create QoSs and add them to vNIC profiles
    Update vNIC to plugged False
    Remove vNIC from VM
    Remove vNIC profile
    Delete QoS from datacenter
    """
    network_qos = NetworkFixtures()
    qos_name_1 = request.node.cls.qos_name_1
    qos_name_2 = request.node.cls.qos_name_2
    vnic_profile_1 = request.node.cls.vnic_profile_1
    vnic_profile_2 = request.node.cls.vnic_profile_2
    vms = request.node.cls.vms

    def fin2():
        """
        Remove vNIC profile
        Delete QoS from datacenter
        """
        networking.remove_unneeded_vms_nics()
        networking.remove_qos_from_setup()
        networking.remove_unneeded_vnic_profiles()
    request.addfinalizer(fin2)

    def fin1():
        """
        Stop VM_1
        """
        ll_vms.stop_vms_safely(vms_list=vms)
    request.addfinalizer(fin1)

    for qos_name, vnic_profile in zip(
        [qos_name_1, qos_name_2], [vnic_profile_1, vnic_profile_2]
    ):
        assert ll_datacenters.add_qos_to_datacenter(
            datacenter=network_qos.dc_0, qos_name=qos_name,
            qos_type=qos_conf.QOS_TYPE,
            inbound_average=qos_conf.BW_PARAMS[0],
            inbound_peak=qos_conf.BW_PARAMS[1],
            inbound_burst=qos_conf.BW_PARAMS[2],
            outbound_average=qos_conf.BW_PARAMS[0],
            outbound_peak=qos_conf.BW_PARAMS[1],
            outbound_burst=qos_conf.BW_PARAMS[2]
        )
    assert helper.add_qos_profile_to_nic(
        qos_name=qos_name_1, vnic_profile_name=vnic_profile_1
    )
    assert network_helper.run_vm_once_specific_host(
        vm=network_qos.vm_0, host=network_qos.host_0_name,
        wait_for_up_status=True
    )
