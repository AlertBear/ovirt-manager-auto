#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Fixtures for Multiple Queue NICs
"""

import pytest

import art.rhevm_api.tests_lib.low_level.networks as ll_networks
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import rhevmtests.networking.config as conf
import rhevmtests.networking.multiple_queue_nics.config as multiple_queue_conf
from art.unittest_lib import testflow
from rhevmtests.networking.fixtures import NetworkFixtures


@pytest.fixture(scope="class")
def update_vnic_profile(request):
    """
    Config and update queue value on vNIC profile for exiting
    network (vNIC CustomProperties).
    """
    multiple_queue_nics = NetworkFixtures()
    bridge = multiple_queue_nics.mgmt_bridge

    def fin():
        """
        Remove custom properties on MGMT.
        """
        testflow.teardown("Setting vNIC: %s properties to default", bridge)
        ll_networks.update_vnic_profile(
            name=bridge, network=bridge,
            data_center=multiple_queue_nics.dc_0, custom_properties="clear"
        )
    request.addfinalizer(fin)

    testflow.setup(
        "Updating vNIC profile: %s with custom_properties: %s",
        bridge, multiple_queue_conf.PROP_QUEUES[0]
    )
    assert ll_networks.update_vnic_profile(
        name=bridge, network=bridge, data_center=multiple_queue_nics.dc_0,
        custom_properties=multiple_queue_conf.PROP_QUEUES[0]
    )


@pytest.fixture(scope="class")
def run_vm(request):
    """
    Start VM.
    """
    multiple_queue_nics = NetworkFixtures()
    vm_name = request.node.cls.vm_name
    host_0 = multiple_queue_nics.host_0_name

    def fin():
        """
        Stop VM.
        """
        testflow.teardown("Stopping VM: %s", vm_name)
        ll_vms.stopVm(positive=True, vm=vm_name)
    request.addfinalizer(fin)

    testflow.setup("Running once VM: %s on host: %s", vm_name, host_0)
    assert multiple_queue_nics.run_vm_once_specific_host(
        vm=vm_name, host=host_0, wait_for_up_status=True
    )


@pytest.fixture(scope="class")
def create_vm(request):
    """
    Create VM.
    """
    multiple_queue_nics = NetworkFixtures()
    vm_name = request.node.cls.vm_name
    template = conf.TEMPLATE_NAME[0]

    def fin():
        """
        Remove vm
        """
        testflow.teardown("Removing VM: %s", vm_name)
        ll_vms.removeVm(positive=True, vm=vm_name, stopVM="True", wait=True)
    request.addfinalizer(fin)

    testflow.setup("Creating VM: %s from template: %s", vm_name, template)
    assert ll_vms.createVm(
        positive=True, vmName=vm_name, cluster=multiple_queue_nics.cluster_0,
        vmDescription="from_template", template=template
    )


@pytest.fixture(scope="class")
def attach_vnic_profile_to_vm(request):
    """
    Attach plugged vNIC with custom queues property to a VM (in shutdown state)
    """
    multiple_queue_nics = NetworkFixtures()
    vm_name = request.node.cls.vm_name
    vnic = request.node.cls.vm_nic
    bridge = multiple_queue_nics.mgmt_bridge

    def fin():
        """
        Remove vNIC from VM
        """
        testflow.teardown("Removing vNIC: %s from VM: %s", vnic, vm_name)
        assert ll_vms.removeNic(positive=True, vm=vm_name, nic=vnic)
    request.addfinalizer(fin)

    testflow.setup("Adding vNIC: %s to VM: %s", vnic, vm_name)
    assert ll_vms.addNic(
        positive=True, vm=vm_name, name=vnic, network=bridge,
        vnic_profile=bridge, plugged=True
    )
