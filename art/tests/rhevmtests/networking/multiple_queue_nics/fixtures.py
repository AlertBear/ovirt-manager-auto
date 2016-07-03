#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Fixtures for multiple_queue_nics
"""

import pytest

import art.rhevm_api.tests_lib.low_level.networks as ll_networks
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import rhevmtests.networking.config as conf
from rhevmtests.networking.fixtures import NetworkFixtures


@pytest.fixture(scope="class")
def update_vnic_profile(request,):
    """
    Config and update queue value on vNIC profile for exiting
    network (vNIC CustomProperties).
    """
    multiple_queue_nics = NetworkFixtures()

    def fin():
        """
        Remove custom properties on MGMT.
        """
        ll_networks.update_vnic_profile(
            name=multiple_queue_nics.mgmt_bridge,
            network=multiple_queue_nics.mgmt_bridge,
            data_center=multiple_queue_nics.dc_0, custom_properties="clear"
        )
    request.addfinalizer(fin)

    assert ll_networks.update_vnic_profile(
        name=multiple_queue_nics.mgmt_bridge,
        network=multiple_queue_nics.mgmt_bridge,
        data_center=multiple_queue_nics.dc_0,
        custom_properties=conf.PROP_QUEUES[0]
    )


@pytest.fixture(scope="class")
def run_vm(request):
    """
    Start VM.
    """
    multiple_queue_nics = NetworkFixtures()
    vm_name = request.node.cls.vm_name

    def fin():
        """
        Stop VM.
        """
        ll_vms.stopVm(positive=True, vm=vm_name)
    request.addfinalizer(fin)

    assert multiple_queue_nics.run_vm_once_specific_host(
        vm=vm_name, host=multiple_queue_nics.host_0_name,
        wait_for_up_status=True
    )


@pytest.fixture(scope="class")
def create_vm(request):
    """
    Create VM.
    """
    multiple_queue_nics = NetworkFixtures()
    vm_name = request.node.cls.vm_name

    def fin():
        """
        Remove vm
        """
        ll_vms.removeVm(
            positive=True, vm=vm_name, stopVM="True", wait=True
        )
    request.addfinalizer(fin)

    assert ll_vms.createVm(
        positive=True, vmName=vm_name, cluster=multiple_queue_nics.cluster_0,
        vmDescription="from_template", template=conf.TEMPLATE_NAME[0]
    )
