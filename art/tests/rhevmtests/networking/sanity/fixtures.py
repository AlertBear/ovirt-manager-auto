#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Fixtures for sanity
"""

import pytest

import art.rhevm_api.tests_lib.low_level.clusters as ll_clusters
import art.rhevm_api.tests_lib.low_level.datacenters as ll_dc
import art.rhevm_api.tests_lib.low_level.networks as ll_networks
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import config as sanity_conf
import rhevmtests.networking.helper as network_helper
import rhevmtests.networking.mac_pool_range_per_dc.helper as mac_pool_helper
from art.unittest_lib import testflow
from rhevmtests.networking.fixtures import NetworkFixtures


@pytest.fixture(scope="class")
def add_vnic_profile(request):
    """
    Add vNIC profile
    """
    NetworkFixtures()
    vnic_profile = request.node.cls.vnic_profile
    dc = request.node.cls.dc
    net = request.node.cls.net
    description = request.node.cls.description

    def fin():
        """
        Remove vNIC profile
        """
        testflow.teardown("Remove vNIC profile %s", vnic_profile)
        assert ll_networks.remove_vnic_profile(
            positive=True, vnic_profile_name=vnic_profile, network=net
        )
    request.addfinalizer(fin)

    testflow.setup("Add vNIC profile %s", vnic_profile)
    assert ll_networks.add_vnic_profile(
        positive=True, name=vnic_profile, data_center=dc,
        network=net, port_mirroring=True, description=description
    )


@pytest.fixture(scope="class")
def remove_qos(request):
    """
    Remove QoS from setup
    """
    sanity = NetworkFixtures()
    qos_name = request.node.cls.qos_name

    def fin():
        """
        Remove QoS from setup
        """
        testflow.teardown("Remove QoS %s", qos_name)
        assert ll_dc.delete_qos_from_datacenter(
            datacenter=sanity.dc_0, qos_name=qos_name
        )
    request.addfinalizer(fin)


@pytest.fixture(scope="class")
def create_vnics_on_vm(request):
    """
    Create 5 VNICs on VM with different params for plugged/linked
    """
    NetworkFixtures()
    nets = request.node.cls.nets
    vm = request.node.cls.vm_name
    vnics = sanity_conf.VNICS[6]

    def fin():
        """
        Remove vNICs from VM
        """
        results = list()
        for nic in vnics[:5]:
            testflow.teardown("Remove vNIC %s from VM %s", nic, vm)
            results.append(ll_vms.removeNic(positive=True, vm=vm, nic=nic))
        assert all(results)
    request.addfinalizer(fin)

    plug_link_param_list = [
        ("true", "true"),
        ("true", "false"),
        ("false", "true"),
        ("false", "false"),
        ("true", "true"),
    ]
    for i in range(len(plug_link_param_list)):
        nic_name = vnics[i]
        testflow.setup("Add vNIC %s to VM %s", nic_name, vm)
        network = nets[i] if i != 4 else None
        assert ll_vms.addNic(
            positive=True, vm=vm, name=nic_name,
            network=network, plugged=plug_link_param_list[i][0],
            linked=plug_link_param_list[i][1]
        )


@pytest.fixture(scope="class")
def create_cluster(request):
    """
    Create new cluster
    """
    NetworkFixtures()
    ext_cl = request.node.cls.ext_cl

    def fin():
        """
        Remove cluster
        """
        testflow.teardown("Remove cluster %s", ext_cl)
        assert ll_clusters.removeCluster(positive=True, cluster=ext_cl)
    request.addfinalizer(fin)

    testflow.setup("Create cluster %s", ext_cl)
    mac_pool_helper.create_cluster_with_mac_pool(mac_pool_name="")


@pytest.fixture(scope="class")
def add_network_to_dc(request):
    """
    Add network to datacenter
    """
    NetworkFixtures()
    dc = request.node.cls.dc
    net = request.node.cls.net

    net_dict = {
        net: {
            "required": "true",
        }
    }
    testflow.setup("Create network %s on datacenter %s", net, dc)
    network_helper.prepare_networks_on_setup(
        networks_dict=net_dict, dc=dc,
    )


@pytest.fixture(scope="class")
def update_vnic_profile(request):
    """
    Update vNIC profile with queue
    """
    NetworkFixtures()
    dc = request.node.cls.dc
    prop_queue = request.node.cls.prop_queue
    mgmt_bridge = request.node.cls.mgmt_bridge

    def fin():
        """
        Remove queue from vNIC profile
        """
        testflow.teardown(
            "Remove custom properties from vNIC profile %s", mgmt_bridge
        )
        assert ll_networks.update_vnic_profile(
            name=mgmt_bridge, network=mgmt_bridge,
            data_center=dc, custom_properties="clear"
        )
    request.addfinalizer(fin)

    testflow.setup(
        "Set queues custom properties on vNIC profile %s", mgmt_bridge
    )
    assert ll_networks.update_vnic_profile(
        name=mgmt_bridge, network=mgmt_bridge,
        data_center=dc, custom_properties=prop_queue
    )


@pytest.fixture(scope="class")
def add_labels(request):
    """
    Add labels
    """
    NetworkFixtures()
    labels = request.node.cls.labels

    for lb, nets in labels.iteritems():
        label_dict = {
            lb: {
                "networks": nets
            }
        }
        testflow.setup("Add label %s to %s", lb, nets)
        assert ll_networks.add_label(**label_dict)
