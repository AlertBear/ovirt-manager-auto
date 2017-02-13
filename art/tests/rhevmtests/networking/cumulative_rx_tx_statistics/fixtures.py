#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Fixtures for cumulative_rx_tx_statistics
"""

import pytest

import art.rhevm_api.tests_lib.high_level.hosts as hl_hosts
import art.rhevm_api.tests_lib.high_level.networks as hl_networks
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import art.rhevm_api.utils.test_utils as test_utils
import config as rx_tx_conf
import rhevmtests.helpers as global_helper
import rhevmtests.networking.config as conf
import rhevmtests.networking.helper as network_helper
from art.unittest_lib import testflow
from rhevmtests.networking.fixtures import NetworkFixtures


@pytest.fixture(scope="module")
def host_vm_prepare_setup(request):
    """
    Create networks on setup
    """
    rx_tx_stats = NetworkFixtures()

    def fin():
        """
        Remove networks from setup
        """
        testflow.teardown("Remove networks from setup")
        assert network_helper.remove_networks_from_setup(
            hosts=rx_tx_stats.host_0_name
        )
    request.addfinalizer(fin)

    testflow.setup("Create networks on setup")
    network_helper.prepare_networks_on_setup(
        networks_dict=rx_tx_conf.NET_DICT, dc=rx_tx_stats.dc_0,
        cluster=rx_tx_stats.cluster_0
    )


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
    nic_name = request.node.cls.nic_name
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
        Finalizer for remove vNIC from VMs
        """
        for vm in vms_list:
            testflow.teardown("Remove vNIC %s from VM %s", nic_name, vm)
            result.append(
                (
                    ll_vms.removeNic(positive=True, vm=vm, nic=nic_name),
                    "fin2: ll_vms.removeNic"
                )
            )
    request.addfinalizer(fin2)

    def fin1():
        """
        Finalizer for stop VMs
        """
        testflow.teardown("Stop VMs %s", vms_list)
        result.append((ll_vms.stopVms(vms=vms_list), "fin1: ll_vms.stopVms"))
    request.addfinalizer(fin1)

    for host, vm, temp_ip in zip(
        rx_tx_state.hosts_list, vms_list, rx_tx_conf.VM_IPS
    ):
        testflow.setup("Add vNIC %s to VM %s", nic_name, vm)
        assert ll_vms.addNic(
            positive=True, vm=vm, name=nic_name, network=network,
            vnic_profile=network
        )
        testflow.setup("Run VM %s on host %s", vm, host)
        assert network_helper.run_vm_once_specific_host(
            vm=vm, host=host, wait_for_up_status=True
        )
        ip = ll_vms.wait_for_vm_ip(vm=vm, timeout=conf.TIMEOUT)[1]
        mgmt_ip = ip.get("ip")
        assert mgmt_ip

        vm_resource = global_helper.get_vm_resource(vm=vm, start_vm=False)
        testflow.setup(
            "Get VM %s interface excluding mgmt interface", vm
        )
        interface = network_helper.get_non_mgmt_nic_name(vm=vm)
        assert interface, "Failed to get interface from %s" % vm

        testflow.setup(
            "Configure temporary static IP %s on specific interface %s",
            temp_ip, interface[0]
        )
        assert test_utils.configure_temp_static_ip(
            vds_resource=vm_resource, ip=temp_ip, nic=interface[0],
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
        testflow.teardown(
            "Move host %s back to original cluster %s",
            rx_tx_stats.host_0_name, rx_tx_stats.cluster_0
        )
        assert hl_hosts.move_host_to_another_cluster(
            host=rx_tx_stats.host_0_name, cluster=rx_tx_stats.cluster_0
        )
    request.addfinalizer(fin)

    testflow.setup(
        "Move host %s to another cluster %s", rx_tx_stats.host_0_name,
        rx_tx_stats.cluster_1
    )
    assert hl_hosts.move_host_to_another_cluster(
        host=rx_tx_stats.host_0_name, cluster=rx_tx_stats.cluster_1
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
