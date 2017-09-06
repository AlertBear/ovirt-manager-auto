#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Fixtures for MultiHost feature
"""

import pytest

import art.rhevm_api.tests_lib.high_level.hosts as hl_hosts
import art.rhevm_api.tests_lib.low_level.templates as ll_templates
import rhevmtests.networking.config as conf
from art.unittest_lib import testflow


@pytest.fixture(scope="class")
def add_vnic_to_template(request):
    """
    Add vNIC to template
    """
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
