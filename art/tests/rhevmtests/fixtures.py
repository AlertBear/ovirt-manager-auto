#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Global fixtures
"""

import pytest

import art.rhevm_api.tests_lib.low_level.clusters as ll_clusters
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import rhevmtests.networking.config as conf
from art.unittest_lib import testflow


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

    for vm, val in vms_dict.iteritems():
        host_index = val.get("host")
        wait_for_status = val.get("wait_for_status", conf.VM_UP)
        host_name = conf.HOSTS[host_index] if host_index is not None else None
        log = "on host %s" % host_name if host_name else ""
        testflow.setup("Start VM %s %s", vm, log)
        assert ll_vms.runVmOnce(
            positive=True, vm=vm, host=host_name,
            wait_for_state=wait_for_status
        )


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
