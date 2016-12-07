#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Fixtures for cumulative_rx_tx_statistics
"""

import pytest

import art.rhevm_api.tests_lib.high_level.host_network as hl_host_network
import art.rhevm_api.tests_lib.high_level.hosts as hl_hosts
import art.rhevm_api.tests_lib.high_level.networks as hl_networks
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import config as rx_tx_conf
import helper
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


@pytest.fixture(scope="module")
def host_prepare_setup(
    request, host_vm_prepare_setup, host_attach_networks_to_hosts
):
    """
    Send ICMP to increase host NICs stats
    """
    rx_tx_stats = NetworkFixtures()
    assert network_helper.send_icmp_sampler(
        host_resource=rx_tx_stats.vds_0_host, dst=rx_tx_conf.HOST_IPS[1]
    )
    testflow.setup(
        "Send ICMP from host %s to host %s", rx_tx_stats.host_0_name,
        rx_tx_stats.host_1_name
    )
    helper.send_icmp(
        [
            (rx_tx_stats.vds_0_host, rx_tx_conf.HOST_IPS[0]),
            (rx_tx_stats.vds_1_host, rx_tx_conf.HOST_IPS[1])
        ]
    )


@pytest.fixture(scope="module")
def clean_hosts_interfaces(request):
    """
    Clean hosts interfaces
    """
    rx_tx_state = NetworkFixtures()
    result_list = list()

    def fin():
        """
        Clean hosts interfaces
        """
        for host_name in rx_tx_state.hosts_list:
            testflow.teardown("Clean host %s interfaces", host_name)
            result_list.append(
                hl_host_network.clean_host_interfaces(host_name=host_name)
            )
        assert all(result_list)
    request.addfinalizer(fin)


@pytest.fixture(scope="module")
def host_attach_networks_to_hosts(request, clean_hosts_interfaces):
    """
    Attach networks with IP to hosts
    """
    rx_tx_state = NetworkFixtures()
    host_nic_list = [rx_tx_state.host_0_nics[1], rx_tx_state.host_1_nics[1]]
    host_ips_list = rx_tx_conf.HOST_IPS[:2]
    ip_dict = rx_tx_conf.BASIC_IP_DICT_NETMASK
    sn_dict = {
        "add": {
            "1": {
                "network": rx_tx_conf.NETWORK_0,
                "nic": None,
                "ip": ip_dict,
            }
        }
    }
    for host, nic, host_ip in zip(
        rx_tx_state.hosts_list, host_nic_list, host_ips_list
    ):
        sn_dict["add"]["1"]["nic"] = nic
        ip_dict["ip_prefix"]["address"] = host_ip
        testflow.setup("Attach: %s to host %s", sn_dict, host)
        assert hl_host_network.setup_networks(host_name=host, **sn_dict)


@pytest.fixture(scope="module")
def vm_attach_networks_to_hosts(request, clean_hosts_interfaces):
    """
    Attach networks to hosts
    """
    rx_tx_state = NetworkFixtures()
    host_nic_list = [rx_tx_state.host_0_nics[1], rx_tx_state.host_1_nics[1]]

    sn_dict = {
        "add": {
            "1": {
                "network": rx_tx_conf.NETWORK_1,
                "nic": None
            },
            "2": {
                "network": rx_tx_conf.NETWORK_2,
                "nic": None
            }
        }
    }
    for host, nic in zip(rx_tx_state.hosts_list, host_nic_list):
        sn_dict["add"]["1"]["nic"] = nic
        sn_dict["add"]["2"]["nic"] = nic
        testflow.setup("Attach: %s to host %s", sn_dict, host)
        assert hl_host_network.setup_networks(host_name=host, **sn_dict)


@pytest.fixture(scope="module")
def vm_prepare_setup(
    request, host_vm_prepare_setup, vm_attach_networks_to_hosts
):
    """
    Add vNICs to VMs
    Run VMs
    Set IPs on VM vNICs
    """
    rx_tx_state = NetworkFixtures()
    vms_list = [rx_tx_state.vm_0, rx_tx_state.vm_1]
    nic_name = rx_tx_conf.VM_NIC_NAME
    network = rx_tx_conf.NETWORK_1
    result_list = list()

    def fin3():
        """
        Finalizer for remove vNIC from VMs
        """
        for vm in vms_list:
            testflow.teardown("Remove vNIC %s from VM %s", nic_name, vm)
            result_list.append(
                ll_vms.removeNic(positive=True, vm=vm, nic=nic_name)
            )
        assert all(result_list)
    request.addfinalizer(fin3)

    def fin2():
        """
        Finalizer for stop VMs
        """
        testflow.teardown("Stop VMs %s", vms_list)
        assert ll_vms.stopVms(vms=vms_list)
    request.addfinalizer(fin2)

    def fin1():
        """
        Finalizer for remove ifcfg files
        """
        testflow.teardown("Remove created ifcfg files from VMs %s", vms_list)
        vms_resources = list()
        for vm in vms_list:
            vms_resources.append(
                rx_tx_conf.VMS_IPS_PARAMS.get(vm).get("resource")
            )
        assert network_helper.remove_ifcfg_files(vms_resources=vms_resources)
    request.addfinalizer(fin1)

    for idx, (host, vm) in enumerate(zip(rx_tx_state.hosts_list, vms_list)):
        testflow.setup("Run VM %s on host %s", vm, host)
        assert network_helper.run_vm_once_specific_host(
            vm=vm, host=host, wait_for_up_status=True
        )
        ip = ll_vms.waitForIP(vm=vm, timeout=conf.TIMEOUT, json=True)[1]
        mgmt_ip = ip.get("ip")
        assert mgmt_ip
        vm_resource = global_helper.get_host_resource(
            ip=mgmt_ip, password=conf.VMS_LINUX_PW
        )
        rx_tx_conf.VMS_IPS_PARAMS[vm] = dict()
        rx_tx_conf.VMS_IPS_PARAMS[vm]["mgmt_ip"] = mgmt_ip
        rx_tx_conf.VMS_IPS_PARAMS[vm]["temp_ip"] = rx_tx_conf.VM_IPS[idx]
        rx_tx_conf.VMS_IPS_PARAMS[vm]["resource"] = vm_resource

        testflow.setup("Add vNIC %s to VM %s", nic_name, vm)
        assert ll_vms.addNic(
            positive=True, vm=vm, name=nic_name, network=network,
            vnic_profile=network
        )
    testflow.setup("Configure IPs on VMs %s", vms_list)
    helper.config_ip()


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


@pytest.fixture(scope="class")
def move_host_to_another_cluster(request):
    """
    Fixture for CumulativeNetworkUsageHostStatisticsCase2
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
    Fixture for CumulativeNetworkUsageStatisticsCase1
    """
    rx_tx_stats = NetworkFixtures()
    nic_name = rx_tx_conf.VM_NIC_NAME
    vm_0_dict = rx_tx_conf.VMS_IPS_PARAMS.get(rx_tx_stats.vm_0)
    vm_1_dict = rx_tx_conf.VMS_IPS_PARAMS.get(rx_tx_stats.vm_1)
    vm_0_resource = vm_0_dict.get("resource")
    vm_1_resource = vm_1_dict.get("resource")
    vm_0_temp_ip = vm_0_dict.get("temp_ip")
    vm_1_temp_ip = vm_1_dict.get("temp_ip")
    vms_ips = [
        (vm_0_resource, vm_0_temp_ip),
        (vm_1_resource, vm_1_temp_ip)
    ]

    nic_state_attempts = 10
    while not all(
        [int(rx_tx_conf.NIC_STAT[x]) > 1000 for x in rx_tx_conf.STAT_KEYS]
    ):
        helper.send_icmp(vms_ips)
        rx_tx_conf.NIC_STAT = hl_networks.get_nic_statistics(
            nic=nic_name, vm=rx_tx_stats.vm_1, keys=rx_tx_conf.STAT_KEYS
        )
        nic_state_attempts -= 1
        if nic_state_attempts == 0:
            assert False, "Timeout waiting for get NIC stats > 1000"

    conf.TOTAL_RX = rx_tx_conf.NIC_STAT["data.total.rx"]
    conf.TOTAL_TX = rx_tx_conf.NIC_STAT["data.total.tx"]
