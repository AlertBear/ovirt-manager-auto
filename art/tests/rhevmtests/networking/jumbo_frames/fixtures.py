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
import art.rhevm_api.tests_lib.low_level.vms as ll_vms

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
        assert hl_networks.remove_net_from_setup(
            host=jumbo_frame.hosts_list[:2], data_center=jumbo_frame.dc_0,
            all_net=True
        )
    request.addfinalizer(fin2)

    def fin1():
        """
        Stop VMs
        """
        assert ll_vms.stop_vms(vms=jumbo_frame.vms_list)
    request.addfinalizer(fin1)

    assert hl_networks.create_and_attach_networks(
        networks=jumbo_conf.NETS_DICT, data_center=jumbo_frame.dc_0,
        clusters=[jumbo_frame.cluster_0]
    )

    for vm, host in zip(jumbo_frame.vms_list, jumbo_frame.hosts_list[:2]):
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
    assert network_helper.configure_temp_mtu(
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
                ll_vms.updateNic(
                    positive=True, vm=vm_name, nic=nic_name, plugged=False
                )
                ll_vms.removeNic(positive=True, vm=vm_name, nic=nic_name)
    request.addfinalizer(fin)

    for vnic_to_add in vnics_to_add:
        vnic_to_add["ips"] = vms_ips
        assert helper.add_vnics_to_vms(**vnic_to_add)


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
