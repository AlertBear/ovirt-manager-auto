#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Networking fixtures
"""

import pytest

import fixtures_helper as network_fixture_helper
import config as conf
from rhevmtests import fixtures_helper
from art.rhevm_api.tests_lib.high_level import (
    vms as hl_vms,
    networks as hl_networks
)
import art.rhevm_api.tests_lib.low_level.networks as ll_networks
import rhevmtests.helpers as global_helper


class NetworkFixtures(object):
    """
    Class for networking fixtures
    """
    def __init__(self):
        conf.VDS_0_HOST = conf.VDS_HOSTS[0]
        conf.VDS_1_HOST = conf.VDS_HOSTS[1]
        conf.VDS_2_HOST = (
            conf.VDS_HOSTS[2] if len(conf.VDS_HOSTS) > 2 else None
        )
        conf.HOST_0_NAME = conf.HOSTS[0]
        conf.HOST_1_NAME = conf.HOSTS[1]
        conf.HOST_2_NAME = conf.HOSTS[2] if len(conf.HOSTS) > 2 else None
        conf.HOST_0_IP = conf.VDS_0_HOST.ip
        conf.HOST_1_IP = conf.VDS_1_HOST.ip
        conf.HOST_0_NICS = conf.VDS_0_HOST.nics
        conf.HOST_1_NICS = conf.VDS_1_HOST.nics
        self.vds_0_host = conf.VDS_0_HOST
        self.vds_1_host = conf.VDS_1_HOST
        self.vds_2_host = conf.VDS_2_HOST
        self.vds_list = [
            v for v in [self.vds_0_host, self.vds_1_host, self.vds_2_host]
            if v
        ]
        self.host_0_name = conf.HOST_0_NAME
        self.host_1_name = conf.HOST_1_NAME
        self.host_2_name = conf.HOST_2_NAME
        self.hosts_list = [
            h for h in [self.host_0_name, self.host_1_name, self.host_2_name]
            if h
        ]
        self.host_0_ip = conf.HOST_0_IP
        self.host_1_ip = conf.HOST_1_IP
        self.host_0_nics = conf.HOST_0_NICS
        self.host_1_nics = conf.HOST_1_NICS
        self.dc_0 = conf.DC_0
        self.cluster_0 = conf.CL_0
        self.cluster_1 = conf.CL_1
        self.bond_0 = conf.BOND[0]
        self.bond_1 = conf.BOND[1]
        self.vm_0 = conf.VM_0
        self.vm_1 = conf.VM_1
        self.vms_list = [self.vm_0, self.vm_1]
        self.mgmt_bridge = conf.MGMT_BRIDGE
        conf.HOSTS_LIST = self.hosts_list
        conf.VDS_HOSTS_LIST = self.vds_list


@pytest.fixture(scope="class")
def clean_host_interfaces(request):
    """
    Clean host(s) interfaces networks (except the management network)
    """
    hosts_nets_nic_dict = request.node.cls.hosts_nets_nic_dict

    def fin():
        """
        Clean host(s) interfaces networks (except the management network)
        """
        assert network_fixture_helper.clean_host_interfaces_helper(
            hosts_nets_nic_dict=hosts_nets_nic_dict
        )
    request.addfinalizer(fin)


@pytest.fixture()
def clean_host_interfaces_fixture_function(request):
    """
    Clean host(s) interfaces networks (except the management network)
    """
    hosts_nets_nic_dict = fixtures_helper.get_fixture_val(
        request=request, attr_name="hosts_nets_nic_dict"
    )

    def fin():
        """
        Clean host(s) interfaces networks (except the management network)
        """
        network_fixture_helper.clean_host_interfaces_helper(
            hosts_nets_nic_dict=hosts_nets_nic_dict
        )
    request.addfinalizer(fin)


@pytest.fixture(scope="class")
def setup_networks_fixture(request, clean_host_interfaces):
    """
    Perform network operation on host via setup network
    """
    NetworkFixtures()
    hosts_nets_nic_dict = request.node.cls.hosts_nets_nic_dict
    sriov_nics = getattr(request.node.cls, "sriov_nics", False)
    persist = getattr(request.node.cls, "persist", False)
    network_fixture_helper.setup_network_helper(
        hosts_nets_nic_dict=hosts_nets_nic_dict, sriov_nics=sriov_nics,
        persist=persist
    )


@pytest.fixture()
def setup_networks_fixture_function(
    request, clean_host_interfaces_fixture_function
):
    """
    Perform network operation on host via setup network
    """
    sriov_nics = fixtures_helper.get_fixture_val(
        request=request, attr_name="sriov_nics", default_value=False
    )
    persist = fixtures_helper.get_fixture_val(
        request=request, attr_name="persist", default_value=False
    )
    hosts_nets_nic_dict = request.getfixturevalue("hosts_nets_nic_dict")
    network_fixture_helper.setup_network_helper(
        hosts_nets_nic_dict=hosts_nets_nic_dict, sriov_nics=sriov_nics,
        persist=persist
    )


@pytest.fixture(scope="class")
def store_vms_params(request):
    """
    Store VM params (IP, resource) into config variable
    """
    vms = getattr(request.node.cls, "vms_to_store", list())
    for vm in vms:
        ip = hl_vms.get_vm_ip(vm_name=vm)
        resource = global_helper.get_host_resource(
            ip=ip, password=conf.VDC_ROOT_PASSWORD
        )
        conf.VMS_TO_STORE[vm] = dict()
        conf.VMS_TO_STORE[vm]["ip"] = ip
        conf.VMS_TO_STORE[vm]["resource"] = resource


@pytest.fixture(scope="class")
def update_cluster_network_usages(request):
    """
    Update cluster network usages
    """
    cluster = request.cls.update_cluster
    network = request.cls.update_cluster_network
    usages = request.cls.update_cluster_network_usages

    assert ll_networks.update_cluster_network(
        positive=True, cluster=cluster, network=network, usages=usages
    )


@pytest.fixture(scope="class")
def create_and_attach_networks(request, remove_all_networks):
    """
    Create and attach network to Data-Centers and clusters
    """
    create_network_dict = request.cls.create_networks

    for val in create_network_dict.values():
        dc = val.get("datacenter")
        cluster = val.get("cluster")
        network_dict = val.get("networks")
        assert hl_networks.create_and_attach_networks(
            data_center=dc, cluster=cluster, network_dict=network_dict
        )


@pytest.fixture(scope="class")
def remove_all_networks(request):
    """
    Remove all networks from Data-Centers
    """
    dcs = getattr(request.node.cls, "remove_dcs_networks", list())

    def fin():
        """
        Remove all networks from Data-Centers
        """
        results = [
            hl_networks.remove_all_networks(datacenter=dc) for dc in dcs
        ]
        assert all(results)
    request.addfinalizer(fin)


@pytest.fixture(scope="class")
def restore_network_usage(request):
    """
    Set management network as default route
    """
    network = request.cls.network_usage
    cluster = request.cls.cluster_usage

    def fin():
        """
        Set management network as default route
        """
        assert ll_networks.update_cluster_network(
            positive=True, cluster=cluster, network=network,
            usages=conf.ALL_NETWORK_USAGES
        )
    request.addfinalizer(fin)
