#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Fixtures for vNIC profile feature tests
"""

import pytest

import art.rhevm_api.tests_lib.high_level.host_network as hl_host_networks
import art.rhevm_api.tests_lib.high_level.networks as hl_networks
import art.rhevm_api.tests_lib.low_level.datacenters as ll_datacenters
import art.rhevm_api.tests_lib.low_level.templates as ll_templates
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import config as vnic_conf
import rhevmtests.networking.config as conf
from rhevmtests.networking import helper as network_helper
from rhevmtests.networking.fixtures import NetworkFixtures


@pytest.fixture(scope="module")
def vnic_profile_prepare_setup(request):
    """
    Create networks on DC and cluster
    """
    vnic_profile = NetworkFixtures()

    def fin1():
        """
        Remove networks from setup
        """
        assert network_helper.remove_networks_from_setup(
            hosts=vnic_profile.host_0_name
        )
    request.addfinalizer(fin1)

    def fin2():
        """
        Remove unneeded vnic profiles
        """
        assert hl_networks.remove_unneeded_vnic_profiles(
            dc_name=vnic_profile.dc_0
        )
    request.addfinalizer(fin2)

    network_helper.prepare_networks_on_setup(
        networks_dict=vnic_conf.NETS_DICT, dc=vnic_profile.dc_0,
        cluster=vnic_profile.cluster_0
    )


@pytest.fixture(scope="class")
def start_vm(request):
    """
    Start a VM on a specified host
    """
    vnic_profile = NetworkFixtures()

    def fin():
        """
        Stops the VM
        """
        assert ll_vms.stopVm(positive=True, vm=vnic_profile.vm_0)
    request.addfinalizer(fin)

    assert network_helper.run_vm_once_specific_host(
        vm=vnic_profile.vm_0, host=vnic_profile.host_0_name,
        wait_for_up_status=True
    )


@pytest.fixture(scope="class")
def create_dc(request):
    """
    Creates a new Data Center with specific name and version
    """

    def fin():
        """
        Remove DC from the setup
        """
        assert ll_datacenters.remove_datacenter(
            positive=True, datacenter=request.node.cls.dc_name2
        )
    request.addfinalizer(fin)

    assert ll_datacenters.addDataCenter(
        positive=True, name=request.node.cls.dc_name2,
        version=request.node.cls.dc_ver
    )


@pytest.fixture(scope="class")
def remove_nic_from_template(request):
    """
    Remove vNIC from template
    """

    def fin():
        """
        Remove vNIC from template
        """
        assert ll_templates.removeTemplateNic(
            positive=True, template=request.node.cls.template,
            nic=request.node.cls.vnic_2
        )
    request.addfinalizer(fin)


@pytest.fixture(scope="function")
def remove_nic_from_vm(request):
    """
    Remove vNIC from VM
    """

    def fin():
        """
        Remove vNIC from VM
        """
        assert ll_vms.removeNic(
            positive=True, vm=request.node.cls.vm, nic=request.node.cls.vnic
        )
    request.addfinalizer(fin)


@pytest.fixture(scope="function")
def clean_host_interfaces(request):
    """
    Clean host interfaces
    """

    def fin():
        """
        Remove all networks from host interfaces
        """
        assert hl_host_networks.clean_host_interfaces(
            host_name=conf.HOST_0_NAME
        )
    request.addfinalizer(fin)
