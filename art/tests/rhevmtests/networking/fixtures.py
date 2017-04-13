#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Networking fixtures
"""

import pytest

import fixtures_helper as network_fixture_helper
import rhevmtests.networking.config as conf
from rhevmtests import fixtures_helper
import art.rhevm_api.tests_lib.high_level.vms as hl_vms
import rhevmtests.helpers as global_helper


class NetworkFixtures(object):
    """
    Class for networking fixtures
    """
    def __init__(self):
        conf.VDS_0_HOST = conf.VDS_HOSTS[0]
        conf.VDS_1_HOST = conf.VDS_HOSTS[1]
        conf.HOST_0_NAME = conf.HOSTS[0]
        conf.HOST_1_NAME = conf.HOSTS[1]
        conf.HOST_0_IP = conf.VDS_0_HOST.ip
        conf.HOST_1_IP = conf.VDS_1_HOST.ip
        conf.HOST_0_NICS = conf.VDS_0_HOST.nics
        conf.HOST_1_NICS = conf.VDS_1_HOST.nics
        self.vds_0_host = conf.VDS_0_HOST
        self.vds_1_host = conf.VDS_1_HOST
        self.vds_list = [self.vds_0_host, self.vds_1_host]
        self.host_0_name = conf.HOST_0_NAME
        self.host_1_name = conf.HOST_1_NAME
        self.hosts_list = [self.host_0_name, self.host_1_name]
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
    hosts_nets_nic_dict = request.getfixturevalue("hosts_nets_nic_dict")

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
