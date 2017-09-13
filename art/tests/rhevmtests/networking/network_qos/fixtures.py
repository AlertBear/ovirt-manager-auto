#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Fixtures for network QoS
"""

import pytest

import art.rhevm_api.tests_lib.low_level.datacenters as ll_datacenters
import config as qos_conf
import rhevmtests.networking.config as conf
import helper
from rhevmtests import networking
from art.unittest_lib import testflow


@pytest.fixture(scope="class")
def add_qos_to_dc_and_qos_profile_to_nic(request):
    """
    Create QoSs and add them to vNIC profiles
    Update vNIC to plugged False
    Remove vNIC from VM
    Remove vNIC profile
    Delete QoS from datacenter
    """
    qos_name_1 = request.node.cls.qos_name_1
    qos_name_2 = request.node.cls.qos_name_2
    vnic_profile_1 = request.node.cls.vnic_profile_1
    vnic_profile_2 = request.node.cls.vnic_profile_2

    def fin():
        """
        Remove vNIC profile
        Delete QoS from datacenter
        """
        testflow.teardown("Remove unneeded vms NICs")
        networking.remove_unneeded_vms_nics()
        testflow.teardown("Remove QoS from setup")
        networking.remove_qos_from_setup()
        testflow.teardown("Remove unneeded vNIC profiles")
        networking.remove_unneeded_vnic_profiles()
    request.addfinalizer(fin)

    for qos_name, vnic_profile in zip(
        [qos_name_1, qos_name_2], [vnic_profile_1, vnic_profile_2]
    ):
        testflow.setup(
            "Add QoS %s to datacenter %s", qos_name, conf.DC_0
        )
        assert ll_datacenters.add_qos_to_datacenter(
            datacenter=conf.DC_0, qos_name=qos_name,
            qos_type=qos_conf.QOS_TYPE,
            inbound_average=qos_conf.BW_PARAMS[0],
            inbound_peak=qos_conf.BW_PARAMS[1],
            inbound_burst=qos_conf.BW_PARAMS[2],
            outbound_average=qos_conf.BW_PARAMS[0],
            outbound_peak=qos_conf.BW_PARAMS[1],
            outbound_burst=qos_conf.BW_PARAMS[2]
        )
        testflow.setup("Add QoS profile to NIC")
    assert helper.add_qos_profile_to_nic(
        qos_name=qos_name_1, vnic_profile_name=vnic_profile_1
    )
