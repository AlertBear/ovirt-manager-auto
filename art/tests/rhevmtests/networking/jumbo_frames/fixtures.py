#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Fixtures for jumbo frame
"""

import pytest

import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import helper
import rhevmtests.helpers as global_helper
import rhevmtests.networking.jumbo_frames.config as jumbo_conf
from art.rhevm_api.tests_lib.high_level import (
    networks as hl_networks,
    vms as hl_vms
)
from art.unittest_lib import testflow
from rhevmtests.networking import (
    config as conf,
    helper as network_helper
)


@pytest.fixture(scope="module")
def prepare_setup_jumbo_frame(request):
    """
    Prepare setup for jumbo frame test
    """
    results = []

    def fin3():
        """
        Check if one of the finalizers failed.
        """
        global_helper.raise_if_false_in_list(results=results)
    request.addfinalizer(fin3)

    def fin2():
        """
        Remove networks from setup
        """
        results.append(
            (
                hl_networks.remove_net_from_setup(
                    host=conf.HOSTS[:2], data_center=conf.DC_0,
                    all_net=True
                ), "fin2: hl_networks.remove_net_from_setup"
            )
        )
    request.addfinalizer(fin2)

    def fin1():
        """
        Stop VMs
        """
        results.append(
            (ll_vms.stop_vms(vms=conf.VM_NAME[:2]), "fin1: ll_vms.stop_vms")
        )
    request.addfinalizer(fin1)

    assert hl_networks.create_and_attach_networks(
        networks=jumbo_conf.NETS_DICT, data_center=conf.DC_0,
        clusters=[conf.CL_0]
    )

    for vm, host in zip(conf.VM_NAME[:2], conf.HOSTS[:2]):
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
    mtu = request.node.cls.mtu
    host_nic_index = request.node.cls.host_nic_index
    host_nic = conf.HOST_0_NICS[host_nic_index]
    testflow.setup(
        "Configure MTU %s on host %s host NIC %s", mtu,
        conf.VDS_0_HOST, host_nic
    )
    assert network_helper.configure_temp_mtu(
        vds_resource=conf.VDS_0_HOST, mtu=mtu, nic=host_nic
    )


@pytest.fixture(scope="class")
def add_vnics_to_vms(request):
    """
    Add vNICs to VMs
    """
    vms_ips = request.node.cls.vms_ips
    vnics_to_add = request.node.cls.vnics_to_add

    for vnic_to_add in vnics_to_add:
        vnic_to_add["ips"] = vms_ips
        assert helper.add_vnics_to_vms(**vnic_to_add)


@pytest.fixture(scope="class")
def restore_hosts_mtu(request):
    """
    Restore hosts interfaces MTU
    """

    def fin():
        """
        Set default MTU on all hosts interfaces
        """
        testflow.teardown("Restore hosts interfaces MTU to 1500")
        helper.restore_mtu_and_clean_interfaces()
    request.addfinalizer(fin)
