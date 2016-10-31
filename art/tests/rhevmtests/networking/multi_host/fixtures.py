#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Fixtures for MultiHost
"""

import pytest

import art.rhevm_api.tests_lib.high_level.hosts as hl_hosts
import art.rhevm_api.tests_lib.low_level.networks as ll_networks
import art.rhevm_api.tests_lib.low_level.templates as ll_templates
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import helper
import rhevmtests.networking.config as conf
from art.unittest_lib import testflow
from rhevmtests.networking.fixtures import NetworkFixtures


@pytest.fixture(scope="class")
def restore_hosts_mtu_interfaces(request):
    """
    Restore hosts interfaces MTU
    """
    NetworkFixtures()

    def fin():
        """
        Restore interfaces default MTU
        """
        if request.node.cls.restore_mtu:
            testflow.teardown("Restore hosts interfaces MTU to 1500")
            net = request.node.cls.net
            mtu_1500 = request.node.cls.mtu_1500
            assert helper.update_network_and_check_changes(
                net=net, mtu=mtu_1500, hosts=conf.HOSTS_LIST,
                vds_hosts=conf.VDS_HOSTS_LIST
            )
    request.addfinalizer(fin)


@pytest.fixture(scope="class")
def add_vnics_to_vms(request):
    """
    Add vNIC to VMs
    """
    NetworkFixtures()
    net = request.node.cls.net
    vm_nic = request.node.cls.vm_nic
    vm_list = request.node.cls.vm_list
    vm_0 = request.node.cls.vm_name

    def fin():
        """
        Un-plug vNIC
        Remove vNIC from VMs
        """
        testflow.teardown("Un-plug vNIC %s from VM %s", vm_nic, vm_0)
        assert ll_vms.updateNic(
            positive=True, vm=vm_0, nic=vm_nic, plugged="false"
        )
        for vm in vm_list:
            testflow.teardown("Remove vNIC %s from VM %s", vm_nic, vm)
            assert ll_vms.removeNic(positive=True, vm=vm, nic=vm_nic)
    request.addfinalizer(fin)

    for vm in vm_list:
        testflow.setup("Add vNIC %s to VM %s", vm_nic, vm)
        assert ll_vms.addNic(positive=True, vm=vm, name=vm_nic, network=net)


@pytest.fixture(scope="class")
def add_vnic_to_tamplate(request):
    """
    Add vNIC to template
    """
    NetworkFixtures()
    net = request.node.cls.net
    vm_nic = request.node.cls.vm_nic
    dc = request.node.cls.dc
    template = request.node.cls.template

    def fin():
        """
        Remove vNIC from template
        """
        testflow.teardown("Remove vNIC %s from template %s", vm_nic, template)
        assert ll_templates.removeTemplateNic(
            positive=True, template=template, nic=vm_nic
        )
    request.addfinalizer(fin)

    testflow.setup("Add vNIC %s to template %s", vm_nic, template)
    assert ll_templates.addTemplateNic(
        positive=True, template=conf.TEMPLATE_NAME[0], name=vm_nic,
        data_center=dc, network=net
    )


@pytest.fixture(scope="class")
def move_host_to_cluster(request):
    """
    Move host to new cluster
    """
    multi_host = NetworkFixtures()
    cl = request.node.cls.cl
    cl_name2 = request.node.cls.cl_name2

    def fin1():
        """
        Move host back to original cluster
        """
        testflow.teardown(
            "Move host %s to cluster %s", multi_host.host_1_name, cl
        )
        assert hl_hosts.move_host_to_another_cluster(
            host=multi_host.host_1_name, cluster=cl
        )
    request.addfinalizer(fin1)

    testflow.setup(
        "Move host %s to cluster %s", multi_host.host_1_name, cl_name2
    )
    assert hl_hosts.move_host_to_another_cluster(
        host=multi_host.host_1_name, cluster=cl_name2
    )


@pytest.fixture(scope="class")
def add_network_to_cluster(request):
    """
    Attach network to cluster.
    """
    cl_name2 = request.node.cls.cl_name2
    net = request.node.cls.net

    testflow.setup("Add network %s to cluster %s", net, cl_name2)
    assert ll_networks.add_network_to_cluster(
        positive=True, network=net, cluster=cl_name2, required=False
    )
