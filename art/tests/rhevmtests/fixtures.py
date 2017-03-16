#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Global fixtures
"""

import pytest

import fixtures_helper
from art.rhevm_api.tests_lib.low_level import (
    clusters as ll_clusters,
    datacenters as ll_datacenters,
    vms as ll_vms,
)
from art.unittest_lib import testflow


@pytest.fixture()
def stop_vms_fixture_function(request):
    """
    Stop VM(s).
    """
    vms_dict = request.getfixturevalue("start_vms_dict")
    vms_dict = vms_dict or dict()
    vms_to_stop = fixtures_helper.get_fixture_val(
        request=request, attr_name="vms_to_stop", default_value=vms_dict.keys()
    )

    def fin():
        """
        Stop VM(s).
        """
        testflow.teardown("Stop VMs %s", vms_to_stop)
        assert ll_vms.stop_vms_safely(vms_list=vms_to_stop)
    request.addfinalizer(fin)


@pytest.fixture(scope="class")
def start_vm(request):
    """
    Run VM once.
    """
    vms_dict = getattr(request.node.cls, "start_vms_dict", dict())
    vms_to_stop = getattr(request.node.cls, 'vms_to_stop', vms_dict.keys())

    def fin():
        """
        Stop VM(s).
        """
        testflow.teardown("Stop VMs %s", vms_to_stop)
        assert ll_vms.stop_vms_safely(vms_list=vms_to_stop)
    request.addfinalizer(fin)

    fixtures_helper.start_vm_helper(vms_dict=vms_dict)


@pytest.fixture()
def start_vms_fixture_function(request, stop_vms_fixture_function):
    """
    Run VMs once.
    """
    vms_dict = request.getfixturevalue("start_vms_dict") or dict()
    fixtures_helper.start_vm_helper(vms_dict=vms_dict)


@pytest.fixture(scope="class")
def create_clusters(request):
    """
    Add cluster(s).

    Example:
        clusters_dict = {
            ext_cls_1: {
                "name": ext_cls_1,
                "data_center": dc,
                "cpu": conf.CPU_NAME,
                "version": conf.COMP_VERSION,
                "management_network": net_1
            },
            ext_cls_2: {
                "name": ext_cls_2,
                "data_center": dc,
                "cpu": conf.CPU_NAME,
                "version": conf.COMP_VERSION,
                "management_network": net_2
            },
        }
    """
    clusters_dict = getattr(request.node.cls, "clusters_dict", dict())
    clusters_to_remove = getattr(
        request.node.cls, 'clusters_to_remove', clusters_dict.keys()
    )
    result_list = list()

    def fin():
        """
        Remove clusters
        """
        for cluster in clusters_to_remove:
            testflow.teardown("Remove cluster %s", cluster)
            result_list.append(
                ll_clusters.removeCluster(positive=True, cluster=cluster)
            )
        assert all(result_list)
    request.addfinalizer(fin)

    for cluster_name, params in clusters_dict.iteritems():
        testflow.setup("Add cluster %s with %s", cluster_name, params)
        assert ll_clusters.addCluster(positive=True, **params)


@pytest.fixture(scope="class")
def create_datacenters(request):
    """
    Add datacenter(s).
    """
    datacenters_dict = getattr(request.node.cls, "datacenters_dict", dict())
    dcs_to_remove = getattr(
        request.node.cls, 'dcs_to_remove', datacenters_dict.keys()
    )
    result_list = list()

    def fin():
        """
        Remove datacenter(s).
        """
        for dc in dcs_to_remove:
            testflow.teardown("Remove datacenter %s", dc)
            result_list.append(
                ll_datacenters.remove_datacenter(positive=True, datacenter=dc)
            )
        assert all(result_list)
    request.addfinalizer(fin)

    for dc_params in datacenters_dict.itervalues():
        testflow.setup("Add datacenter with %s", dc_params)
        assert ll_datacenters.addDataCenter(positive=True, **dc_params)
