#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Fixtures for network filter
"""


import pytest

import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import rhevmtests.networking.config as conf
from art.rhevm_api.utils import test_utils
from rhevmtests.networking.fixtures import (
    NetworkFixtures, network_cleanup_fixture
)  # flake8: noqa


class NetworkFilter(NetworkFixtures):
    """
    Fixtures for network filter
    """
    pass


@pytest.fixture(scope="module")
def network_filter_prepare_setup(request, network_cleanup_fixture):
    """
    Prepare setup
    """
    network_filter = NetworkFilter()

    def fin():
        """
        Finalizer for stopping VM
        """
        network_filter.stop_vm(positive=True, vm=network_filter.vm_0)
    request.addfinalizer(fin)

    network_filter.run_vm_once_specific_host(
        vm=network_filter.vm_0, host=network_filter.host_0_name,
        wait_for_up_status=True
    )


@pytest.fixture(scope="class")
def case_01_fixture(request, network_filter_prepare_setup):
    """
    Fixture for case01
    """
    network_filter = NetworkFilter()

    def fin():
        """
        Finalizer for un-plug and remove nic2 from VM
        """

        ll_vms.hotUnplugNic(
            positive=True, vm=network_filter.vm_0, nic=conf.NIC_NAME[1]
        )

        ll_vms.removeNic(
            positive=True, vm=network_filter.vm_0, nic=conf.NIC_NAME[1]
        )
    request.addfinalizer(fin)

    assert ll_vms.addNic(
        positive=True, vm=network_filter.vm_0, name=conf.NIC_NAME[1],
        interface=conf.NIC_TYPE_RTL8139, network=network_filter.mgmt_bridge
    )


@pytest.fixture(scope="class")
def case_02_fixture(request, network_filter_prepare_setup):
    """
    Fixture for case02
    """
    network_filter = NetworkFilter()

    def fin():
        """
        Finalizer for start the VM
        """
        network_filter.run_vm_once_specific_host(
            vm=network_filter.vm_0, host=network_filter.host_0_name,
            wait_for_up_status=True
        )
    request.addfinalizer(fin)


@pytest.fixture(scope="class")
def case_04_fixture(request, network_filter_prepare_setup):
    """
    Fixture for case04
    """
    network_filter = NetworkFilter()

    def fin():
        """
        Finalizer for enabling network filter on engine
        """
        test_utils.set_network_filter_status(
            enable=True, engine_resource=conf.ENGINE
        )
    request.addfinalizer(fin)

    network_filter.stop_vm(positive=True, vm=network_filter.vm_0)

    test_utils.set_network_filter_status(
        enable=False, engine_resource=conf.ENGINE
    )

    assert ll_vms.startVm(
        positive=True, vm=network_filter.vm_0, wait_for_status="up"
    )
