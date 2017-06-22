#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Fixtures for vNIC profile feature tests
"""

import pytest

from art.rhevm_api.tests_lib.high_level import (
    host_network as hl_host_networks,
    networks as hl_networks
)
from art.rhevm_api.tests_lib.low_level import (
    datacenters as ll_datacenters,
    templates as ll_templates,
    vms as ll_vms
)
import config as vnic_conf
from art.unittest_lib import testflow
from rhevmtests.networking import helper as network_helper, config as conf
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
        assert hl_networks.remove_net_from_setup(
            host=[vnic_profile.host_0_name], all_net=True,
            data_center=vnic_profile.dc_0
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

    testflow.setup(
        "Create networks %s on datacenter %s and cluster %s",
        vnic_conf.NETS_DICT, vnic_profile.dc_0, vnic_profile.cluster_0
    )
    network_helper.prepare_networks_on_setup(
        networks_dict=vnic_conf.NETS_DICT, dc=vnic_profile.dc_0,
        cluster=vnic_profile.cluster_0
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
        testflow.teardown(
            "Remove datacenter %s from setup", request.node.cls.dc_name2
        )
        assert ll_datacenters.remove_datacenter(
            positive=True, datacenter=request.node.cls.dc_name2
        )
    request.addfinalizer(fin)

    testflow.setup("Add new datacenter %s", request.node.cls.dc_name2)
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
        testflow.teardown("Remove vNIC from template")
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
        testflow.teardown("Remove vNIC from VM")
        assert ll_vms.removeNic(
            positive=True, vm=request.node.cls.vm_name,
            nic=request.node.cls.vnic
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
