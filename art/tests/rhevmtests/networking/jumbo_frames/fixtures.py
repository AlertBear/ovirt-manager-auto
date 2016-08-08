#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Fixtures for jumbo frame
"""

import pytest

import art.rhevm_api.tests_lib.high_level.host_network as hl_host_network
import art.rhevm_api.tests_lib.high_level.networks as hl_networks
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import rhevmtests.networking.helper as network_helper
import rhevmtests.networking.config as conf
import art.rhevm_api.tests_lib.low_level.networks as ll_networks
from art.rhevm_api.utils import test_utils
import helper
import rhevmtests.networking.jumbo_frames.config as jumbo_conf
from rhevmtests.networking.fixtures import NetworkFixtures


class JumboFrame(NetworkFixtures):
    """
    Fixtures for jumbo frame
    """
    def __init__(self):
        super(JumboFrame, self).__init__()
        self.vms_list = [self.vm_0, self.vm_1]
        self.host_nics_list = [self.host_0_nics, self.host_1_nics]


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
        hl_networks.remove_net_from_setup(
            host=jumbo_frame.hosts_list, data_center=jumbo_frame.dc_0,
            mgmt_network=jumbo_frame.mgmt_bridge, all_net=True
        )
    request.addfinalizer(fin2)

    def fin1():
        """
        Stop VMs
        """
        ll_vms.stopVms(vms=jumbo_frame.vms_list)
    request.addfinalizer(fin1)

    network_helper.prepare_networks_on_setup(
        networks_dict=jumbo_conf.NETS_DICT, dc=jumbo_frame.dc_0,
        cluster=jumbo_frame.cluster_0
    )

    for vm, host in zip(jumbo_frame.vms_list, jumbo_frame.hosts_list):
        assert network_helper.run_vm_once_specific_host(
            vm=vm, host=host, wait_for_up_status=True
        )


@pytest.fixture(scope="class")
def attach_networks_to_hosts(request, restore_hosts_mtu):
    """
    Attach networks to hosts via setup_networks
    """
    JumboFrame()
    hosts_nets_nic_dict = request.node.cls.hosts_nets_nic_dict
    ip_dict = {
        "1": {
            "address": None,
            "netmask": "24",
            "boot_protocol": "static"
        }
    }
    sn_dict = {
        "add": {}
    }

    for key, val in hosts_nets_nic_dict.iteritems():
        host = conf.HOSTS[key]
        host_resource = conf.VDS_HOSTS[key]
        for net, value in val.iteritems():
            slaves_list = list()
            slaves = value.get("slaves")
            nic = value.get("nic")
            ip_addr = value.get("ip")
            mode = value.get("mode")
            if slaves:
                for nic_ in slaves:
                    slaves_list.append(host_resource.nics[nic_])

            if isinstance(nic, int):
                nic = host_resource.nics[nic]

            sn_dict["add"][net] = {
                "network": net,
                "nic": nic,
                "slaves": slaves_list,
                "mode": mode
            }
            if ip_addr:
                ip_dict["1"]["address"] = ip_addr
                sn_dict["add"][net]["ip"] = ip_dict

        assert hl_host_network.setup_networks(host_name=host, **sn_dict)


@pytest.fixture(scope="class")
def configure_mtu_on_host(request, restore_hosts_mtu):
    """
    Configure MTU on hosts interfaces
    """
    jumbo_frame = JumboFrame()
    mtu = request.node.cls.mtu
    host_nic_index = request.node.cls.host_nic_index
    assert test_utils.configure_temp_mtu(
        vds_resource=jumbo_frame.vds_0_host, mtu=mtu,
        nic=jumbo_frame.host_0_nics[host_nic_index]
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
                ll_vms.updateNic(
                    positive=True, vm=vm_name, nic=nic_name, plugged=False
                )
                ll_vms.removeNic(positive=True, vm=vm_name, nic=nic_name)
    request.addfinalizer(fin)

    for vnic_to_add in vnics_to_add:
        vnic_to_add["ips"] = vms_ips
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
        ll_networks.update_cluster_network(
            positive=True, cluster=jumbo_frame.cluster_0,
            network=jumbo_frame.mgmt_bridge,
            usages="display,vm,migration,management"
        )
    request.addfinalizer(fin)

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
        helper.restore_mtu_and_clean_interfaces()
    request.addfinalizer(fin)
