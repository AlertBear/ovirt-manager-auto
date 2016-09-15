#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Fixtures for topologies test
"""

import pytest

import art.rhevm_api.tests_lib.high_level.host_network as hl_host_network
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import config as topologies_conf
import helper
import rhevmtests.networking.config as conf
from rhevmtests.networking import helper as network_helper
from rhevmtests.networking.fixtures import NetworkFixtures


@pytest.fixture(scope="module")
def topologies_prepare_setup(request):
    """
    prepare setup
    """
    topologies = NetworkFixtures()

    def fin():
        """
        Remove networks from setup
        """
        assert network_helper.remove_networks_from_setup(
            hosts=topologies.host_0_name
        )
    request.addfinalizer(fin)

    network_helper.prepare_networks_on_setup(
        networks_dict=topologies_conf.NETS_DICT, dc=topologies.dc_0,
        cluster=topologies.cluster_0
    )


@pytest.fixture(scope="module")
def start_vm_fixture(request, topologies_prepare_setup):
    """
    Start VM
    """
    topologies = NetworkFixtures()

    def fin():
        """
        Stop VM
        """
        ll_vms.stopVm(positive=True, vm=topologies.vm_0)
    request.addfinalizer(fin)

    assert network_helper.run_vm_once_specific_host(
        vm=topologies.vm_0, host=topologies.host_0_name,
        wait_for_up_status=True
    )


@pytest.fixture(scope="class")
def attach_network_and_update_vnic(request, start_vm_fixture):
    """
    Attach network to host, update vNIC on VM
    """
    topologies = NetworkFixtures()
    net = request.node.cls.net
    bond = request.node.cls.bond
    mode = request.node.cls.mode

    def fin3():
        """
        Clean host interfaces
        """
        hl_host_network.clean_host_interfaces(host_name=topologies.host_0_name)
    request.addfinalizer(fin3)

    def fin2():
        """
        Update VM vNIC to default one
        """
        assert helper.update_vnic_driver(
            driver=conf.NIC_TYPE_VIRTIO, vnic_profile=conf.MGMT_BRIDGE
        )
    request.addfinalizer(fin2)

    sn_dict = {
        "add": {
            "1": {
                "network": net,
                "nic": topologies.host_0_nics[1] if not bond else bond,
                "slaves": topologies.host_0_nics[2:4] if bond else None,
                "mode": mode
            }
        }
    }
    assert hl_host_network.setup_networks(
        host_name=topologies.host_0_name, **sn_dict
    )
    assert helper.update_vnic_driver(
        driver=conf.INTERFACE_VIRTIO, vnic_profile=net
    )


@pytest.fixture(scope="class")
def attach_bond(request, topologies_prepare_setup):
    """
    Attach BOND to host
    """
    topologies = NetworkFixtures()
    net = request.node.cls.net
    bond = request.node.cls.bond
    mode = request.node.cls.mode

    def fin():
        """
        Clean host interfaces
        """
        hl_host_network.clean_host_interfaces(host_name=topologies.host_0_name)
    request.addfinalizer(fin)

    sn_dict = {
        "add": {
            "1": {
                "network": net,
                "nic": bond,
                "slaves": topologies.host_0_nics[2:4],
                "mode": mode,
                "ip": {
                    "1": {
                        "address": conf.ADDR_AND_MASK[0],
                        "netmask": conf.ADDR_AND_MASK[1],
                        "boot_protocol": "static"
                    }
                }
            }
        }
    }
    assert hl_host_network.setup_networks(
        host_name=topologies.host_0_name, **sn_dict
    )
