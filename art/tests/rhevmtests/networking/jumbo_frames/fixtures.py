#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Fixtures for jumbo frame
"""

import pytest

import helper
import rhevmtests.helpers as global_helper
import rhevmtests.networking.jumbo_frames.config as jumbo_conf
from art.rhevm_api.tests_lib.high_level import (
    networks as hl_networks,
    vms as hl_vms
)
from art.rhevm_api.tests_lib.low_level import (
    networks as ll_networks,
    vms as ll_vms
)
from art.rhevm_api.utils import test_utils
from art.unittest_lib import testflow
from rhevmtests.networking import (
    config as conf,
    helper as network_helper
)
from rhevmtests.networking.fixtures import NetworkFixtures


@pytest.fixture(scope="module")
def prepare_setup_jumbo_frame(request):
    """
    Prepare setup for jumbo frame test
    """
    jumbo_frame = NetworkFixtures()

    def fin2():
        """
        Remove networks from setup
        """
        testflow.teardown("Remove networks from setup")
        assert hl_networks.remove_net_from_setup(
            host=jumbo_frame.hosts_list, data_center=jumbo_frame.dc_0,
            mgmt_network=jumbo_frame.mgmt_bridge, all_net=True
        )
    request.addfinalizer(fin2)

    def fin1():
        """
        Stop VMs
        """
        testflow.teardown("Stop VMs %s", jumbo_frame.vms_list)
        assert ll_vms.stop_vms(vms=jumbo_frame.vms_list)
    request.addfinalizer(fin1)

    testflow.setup("Create networks %s", jumbo_conf.NETS_DICT)
    network_helper.prepare_networks_on_setup(
        networks_dict=jumbo_conf.NETS_DICT, dc=jumbo_frame.dc_0,
        cluster=jumbo_frame.cluster_0
    )

    for vm, host in zip(jumbo_frame.vms_list, jumbo_frame.hosts_list):
        testflow.setup("Run vm %s once on specific host %s", vm, host)
        assert hl_vms.run_vm_once_specific_host(
            vm=vm, host=host, wait_for_up_status=True
        )
        vm_resource = global_helper.get_vm_resource(vm=vm)
        assert vm_resource
        jumbo_conf.VMS_RESOURCES[vm] = vm_resource


@pytest.fixture(scope="class")
def configure_mtu_on_host(request, restore_hosts_mtu):
    """
    Configure MTU on hosts interfaces
    """
    jumbo_frame = NetworkFixtures()
    mtu = request.node.cls.mtu
    host_nic_index = request.node.cls.host_nic_index
    host_nic = jumbo_frame.host_0_nics[host_nic_index]
    testflow.setup(
        "Configure MTU %s on host %s host NIC %s", mtu,
        jumbo_frame.vds_0_host, host_nic
    )
    assert test_utils.configure_temp_mtu(
        vds_resource=jumbo_frame.vds_0_host, mtu=mtu,
        nic=host_nic
    )


@pytest.fixture(scope="class")
def add_vnics_to_vms(request):
    """
    Add vNICs to VMs
    """
    NetworkFixtures()
    vms_ips = request.node.cls.vms_ips
    vnics_to_add = request.node.cls.vnics_to_add

    def fin():
        """
        Remove NICs from VMs
        """
        for vm_name in conf.VM_NAME[:2]:
            for vnic_to_remove in vnics_to_add:
                nic_name = vnic_to_remove.get("nic_name")
                testflow.teardown(
                    "Remove vNIC %s from VM %s", nic_name, vm_name
                )
                ll_vms.updateNic(
                    positive=True, vm=vm_name, nic=nic_name, plugged=False
                )
                ll_vms.removeNic(positive=True, vm=vm_name, nic=nic_name)
    request.addfinalizer(fin)

    for vnic_to_add in vnics_to_add:
        vnic_to_add["ips"] = vms_ips
        testflow.setup("Add vNIC: %s to VMs", vnic_to_add)
        assert helper.add_vnics_to_vms(**vnic_to_add)


@pytest.fixture(scope="class")
def update_cluster_network(request):
    """
    Update cluster network usages
    """
    jumbo_frame = NetworkFixtures()
    net = request.node.cls.net

    def fin():
        """
        Update management cluster network to default
        """
        testflow.teardown(
            "Update cluster network %s as "
            "display,vm,migration,management,default_route",
            jumbo_frame.mgmt_bridge
        )
        assert ll_networks.update_cluster_network(
            positive=True, cluster=jumbo_frame.cluster_0,
            network=jumbo_frame.mgmt_bridge,
            usages="display,vm,migration,management,default_route"
        )
    request.addfinalizer(fin)

    testflow.setup("Update cluster network %s as display,vm", net)
    assert ll_networks.update_cluster_network(
        positive=True, cluster=jumbo_frame.cluster_0, network=net,
        usages='display,vm'
    )


@pytest.fixture(scope="class")
def restore_hosts_mtu(request):
    """
    Restore hosts interfaces MTU
    """
    NetworkFixtures()

    def fin():
        """
        Set default MTU on all hosts interfaces
        """
        testflow.teardown("Restore hosts interfaces MTU to 1500")
        helper.restore_mtu_and_clean_interfaces()
    request.addfinalizer(fin)
