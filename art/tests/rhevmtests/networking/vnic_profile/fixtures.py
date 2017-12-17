#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Fixtures for vNIC profile feature tests
"""

import pytest

import config as vnic_conf
import rhevmtests.networking.config as conf
from art.rhevm_api.tests_lib.high_level import (
    host_network as hl_host_networks,
    networks as hl_networks
)
from art.rhevm_api.tests_lib.low_level import (
    templates as ll_templates,
    vms as ll_vms
)
from art.unittest_lib import testflow


@pytest.fixture(scope="class")
def remove_vnic_profiles(request):
    """
    Remove vNIC profiles
    """

    def fin():
        """
        Remove unneeded vNIC profiles
        """
        testflow.teardown("Remove unneeded vNIC profiles")
        assert hl_networks.remove_unneeded_vnic_profiles(
            dc_name=conf.DC_0
        )
    request.addfinalizer(fin)


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


@pytest.fixture()
def remove_nic_from_vm(request):
    """
    Remove vNIC from VM
    """

    def fin():
        """
        Remove vNIC from VM
        """
        assert ll_vms.removeNic(
            positive=True, vm=request.node.cls.vm_name,
            nic=request.node.cls.vnic
        )
    request.addfinalizer(fin)


@pytest.fixture()
def clean_host_interfaces(request):
    """
    Clean host interfaces
    """

    def fin():
        """
        Remove all networks from host interfaces
        """
        assert hl_host_networks.clean_host_interfaces(
            host_name=vnic_conf.HOST_NAME
        )
    request.addfinalizer(fin)
