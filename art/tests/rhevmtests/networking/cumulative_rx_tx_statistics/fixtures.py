#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Fixtures for cumulative_rx_tx_statistics
"""

import pytest

import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import config as rx_tx_conf
import rhevmtests.helpers as global_helper
import rhevmtests.networking.config as conf
import rhevmtests.networking.helper as network_helper
from art.rhevm_api.tests_lib.high_level import (
    hosts as hl_hosts,
    networks as hl_networks,
    vms as hl_vms
)
from art.unittest_lib import testflow
from rhevmtests.networking.fixtures import NetworkFixtures


@pytest.fixture(scope="class")
def send_icmp(request):
    """
    Send ICMP to increase host NICs stats
    """
    rx_tx_stats = NetworkFixtures()
    testflow.setup(
        "Send ICMP from host %s to host %s", rx_tx_stats.host_0_name,
        rx_tx_stats.host_1_name
    )
    rx_tx_stats.vds_0_host.network.send_icmp(dst=rx_tx_conf.HOST_IPS[1])
    rx_tx_stats.vds_1_host.network.send_icmp(dst=rx_tx_conf.HOST_IPS[0])


@pytest.fixture(scope="class")
def vm_prepare_setup(request):
    """
    Add vNICs to VMs
    Run VMs
    Set IPs on VM vNICs
    """
    rx_tx_state = NetworkFixtures()
    vms_list = rx_tx_state.vms_list
    nic = request.node.cls.nic_name
    network = request.node.cls.net_1
    result = list()

    def fin3():
        """
        Check if one of the finalizers failed.
        """
        global_helper.raise_if_false_in_list(results=result)
    request.addfinalizer(fin3)

    def fin2():
        """
        Remove vNIC from VMs
        """
        for vm in vms_list:
            result.append(
                (
                    ll_vms.removeNic(positive=True, vm=vm, nic=nic),
                    "fin2: removeNic, {vm}".format(vm=vm)
                )
            )
    request.addfinalizer(fin2)

    def fin1():
        """
        Stop VMs
        """
        result.append(
            (
                ll_vms.stop_vms(
                    vms=vms_list, async="false"
                ), "fin1: stop_vms"
            )
        )
    request.addfinalizer(fin1)

    for host, vm, temp_ip in zip(
        rx_tx_state.hosts_list[:2], vms_list, rx_tx_conf.VM_IPS
    ):
        assert ll_vms.addNic(
            positive=True, vm=vm, name=nic, network=network,
            vnic_profile=network
        )
        assert hl_vms.run_vm_once_specific_host(
            vm=vm, host=host, wait_for_up_status=True
        )
        mgmt_ip = hl_vms.get_vm_ip(vm_name=vm, start_vm=False)
        assert mgmt_ip

        vm_resource = global_helper.get_vm_resource(vm=vm, start_vm=False)
        testflow.setup(
            "Get VM %s interface excluding mgmt interface", vm
        )
        interface = network_helper.get_non_mgmt_nic_name(
            vm_resource=vm_resource
        )
        assert interface, "Failed to get interface from %s" % vm
        interface = interface[0]

        testflow.setup(
            "Configure temporary static IP %s on specific interface %s",
            temp_ip, interface
        )
        assert network_helper.configure_temp_static_ip(
            vds_resource=vm_resource, ip=temp_ip, nic=interface,
            netmask="255.255.0.0"
        )
        rx_tx_conf.VMS_IPS_PARAMS[vm] = dict()
        rx_tx_conf.VMS_IPS_PARAMS[vm]["mgmt_ip"] = mgmt_ip
        rx_tx_conf.VMS_IPS_PARAMS[vm]["temp_ip"] = temp_ip
        rx_tx_conf.VMS_IPS_PARAMS[vm]["resource"] = vm_resource


@pytest.fixture(scope="class")
def update_host_nics_stats(request):
    """
    Update host NICs stats values
    """
    rx_tx_stats = NetworkFixtures()
    testflow.setup("Update host NICs stats values")
    conf.NIC_STAT = hl_networks.get_nic_statistics(
        nic=rx_tx_stats.host_0_nics[1], host=rx_tx_stats.host_0_name,
        keys=rx_tx_conf.STAT_KEYS
    )

    conf.TOTAL_RX = rx_tx_conf.NIC_STAT["data.total.rx"]
    conf.TOTAL_TX = rx_tx_conf.NIC_STAT["data.total.tx"]


@pytest.fixture()
def move_host_to_another_cluster(request):
    """
    move host to another cluster.
    """
    rx_tx_stats = NetworkFixtures()

    def fin():
        """
        Move host back to original cluster
        """
        assert hl_hosts.move_host_to_another_cluster(
            host=rx_tx_stats.host_0_name, cluster=rx_tx_stats.cluster_0,
            host_resource=rx_tx_stats.vds_0_host
        )
    request.addfinalizer(fin)

    assert hl_hosts.move_host_to_another_cluster(
        host=rx_tx_stats.host_0_name, cluster=rx_tx_stats.cluster_1,
        host_resource=rx_tx_stats.vds_0_host
    )


@pytest.fixture(scope="class")
def update_vms_nics_stats(request):
    """
    Update VMs NICs stats.
    """
    rx_tx_stats = NetworkFixtures()
    nic_name = rx_tx_conf.VM_NIC_NAME
    vm_0_dict = rx_tx_conf.VMS_IPS_PARAMS.get(rx_tx_stats.vm_0)
    vm_1_dict = rx_tx_conf.VMS_IPS_PARAMS.get(rx_tx_stats.vm_1)
    vm_0_resource = vm_0_dict.get("resource")
    vm_1_resource = vm_1_dict.get("resource")
    vm_0_temp_ip = vm_0_dict.get("temp_ip")
    vm_1_temp_ip = vm_1_dict.get("temp_ip")

    nic_state_attempts = 10
    while not all(
        [int(rx_tx_conf.NIC_STAT[x]) > 1000 for x in rx_tx_conf.STAT_KEYS]
    ):
        vm_0_resource.network.send_icmp(dst=vm_1_temp_ip)
        vm_1_resource.network.send_icmp(dst=vm_0_temp_ip)
        rx_tx_conf.NIC_STAT = hl_networks.get_nic_statistics(
            nic=nic_name, vm=rx_tx_stats.vm_1, keys=rx_tx_conf.STAT_KEYS
        )
        nic_state_attempts -= 1
        if nic_state_attempts == 0:
            assert False, "Timeout waiting for get NIC stats > 1000"

    conf.TOTAL_RX = rx_tx_conf.NIC_STAT["data.total.rx"]
    conf.TOTAL_TX = rx_tx_conf.NIC_STAT["data.total.tx"]
