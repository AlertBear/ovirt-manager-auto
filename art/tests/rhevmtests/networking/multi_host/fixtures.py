#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Fixtures for MultiHost feature
"""

import pytest

import art.rhevm_api.tests_lib.high_level.hosts as hl_hosts
import art.rhevm_api.tests_lib.low_level.networks as ll_networks
import art.rhevm_api.tests_lib.low_level.templates as ll_templates
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import rhevmtests.networking.config as conf
from art.unittest_lib import testflow
from rhevmtests.networking.fixtures import NetworkFixtures


@pytest.fixture(scope="class")
def add_vnics_to_vms(request):
    """
    Add vNIC(s) to VM(s)
    """
    NetworkFixtures()
    vms_list = getattr(request.node.cls, "add_vnics_to_vms_params", dict())

    def fin():
        """
        Remove vNIC(s) from VM(s)
        """
        for vm, settings in vms_list.items():
            vnic_name = settings.get("vnic_name")
            testflow.teardown("Unplugging vNIC: %s from VM: %s", vnic_name, vm)
            assert ll_vms.updateNic(
                positive=True, vm=vm, nic=vnic_name, plugged="false"
            )

            testflow.teardown("Removing vNIC: %s from VM: %s", vnic_name, vm)
            assert ll_vms.removeNic(positive=True, vm=vm, nic=vnic_name)
    request.addfinalizer(fin)

    for vm, settings in vms_list.items():
        net = settings.get("network")
        vnic_name = settings.get("vnic_name")
        testflow.setup(
            "Adding vNIC: %s attached to network:%s to VM: %s", vnic_name, net,
            vm
        )
        assert ll_vms.addNic(positive=True, vm=vm, name=vnic_name, network=net)


@pytest.fixture(scope="class")
def add_vnic_to_template(request):
    """
    Add vNIC to template
    """
    NetworkFixtures()
    net = request.node.cls.template_network
    vm_nic = request.node.cls.template_vm_nic
    dc = request.node.cls.template_dc
    template = request.node.cls.template_name

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
    NetworkFixtures()
    src_cluster = request.node.cls.cl_src_cluster
    dst_cluster = request.node.cls.cl_dst_cluster
    host_idx = request.node.cls.cl_host
    host_name = conf.HOSTS[host_idx]

    def fin():
        """
        Move host back to original cluster
        """
        testflow.teardown(
            "Move host: %s back to cluster: %s", host_name, src_cluster
        )
        assert hl_hosts.move_host_to_another_cluster(
            host=host_name, cluster=src_cluster
        )
    request.addfinalizer(fin)

    testflow.setup(
        "Move host: %s to cluster: %s", host_name, dst_cluster
    )
    assert hl_hosts.move_host_to_another_cluster(
        host=host_name, cluster=dst_cluster
    )


@pytest.fixture(scope="class")
def add_network_to_cluster(request):
    """
    Attach network to cluster
    """
    NetworkFixtures()
    cl_name = request.node.cls.cl_name
    net = request.node.cls.cl_net

    testflow.setup("Add network: %s to cluster: %s", net, cl_name)
    assert ll_networks.add_network_to_cluster(
        positive=True, network=net, cluster=cl_name, required=False
    )
