#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Fixtures for jumbo frame
"""

import pytest

import art.rhevm_api.tests_lib.high_level.networks as hl_networks
import art.rhevm_api.tests_lib.low_level.networks as ll_networks
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import helper
import rhevmtests.helpers as global_helper
import rhevmtests.networking.config as conf
import rhevmtests.networking.helper as network_helper
import rhevmtests.networking.jumbo_frames.config as jumbo_conf
from art.rhevm_api.utils import test_utils
from art.unittest_lib import testflow
from rhevmtests.networking.fixtures import NetworkFixtures


class JumboFrame(NetworkFixtures):
    """
    Fixtures for jumbo frame
    """
    def __init__(self):
        super(JumboFrame, self).__init__()
        self.vms_list = [self.vm_0, self.vm_1]


@pytest.fixture(scope="module")
def prepare_setup_jumbo_frame(request):
    """
    Prepare setup for jumbo frame test
    """
    jumbo_frame = JumboFrame()

    def fin2():
        """
        Remove networks from setup
        """
        assert hl_networks.remove_net_from_setup(
            host=jumbo_frame.hosts_list, data_center=jumbo_frame.dc_0,
            mgmt_network=jumbo_frame.mgmt_bridge, all_net=True
        )
    request.addfinalizer(fin2)

    def fin1():
        """
        Stop VMs
        """
        assert ll_vms.stopVms(vms=jumbo_frame.vms_list)
    request.addfinalizer(fin1)

    network_helper.prepare_networks_on_setup(
        networks_dict=jumbo_conf.NETS_DICT, dc=jumbo_frame.dc_0,
        cluster=jumbo_frame.cluster_0
    )

    for vm, host in zip(jumbo_frame.vms_list, jumbo_frame.hosts_list):
        assert network_helper.run_vm_once_specific_host(
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
    jumbo_frame = JumboFrame()
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
    JumboFrame()
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
    jumbo_frame = JumboFrame()
    net = request.node.cls.net

    def fin():
        """
        Update management cluster network to default
        """
        testflow.teardown(
            "Update cluster network %s as display,vm,migration,management",
            jumbo_frame.mgmt_bridge
        )
        assert ll_networks.update_cluster_network(
            positive=True, cluster=jumbo_frame.cluster_0,
            network=jumbo_frame.mgmt_bridge,
            usages="display,vm,migration,management"
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
    JumboFrame()

    def fin():
        """
        Set default MTU on all hosts interfaces
        """
        testflow.teardown("Restore hosts interfaces MTU to 1500")
        helper.restore_mtu_and_clean_interfaces()
    request.addfinalizer(fin)
