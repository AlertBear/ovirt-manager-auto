#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Migration Network fixtures
"""
import pytest

import rhevmtests.networking.config as net_config
from art.rhevm_api.tests_lib.high_level import (
    hosts as hl_hosts,
    networks as hl_networks
)
from art.rhevm_api.tests_lib.low_level import (
    networks as ll_networks,
    vms as ll_vms,
    clusters as ll_clusters
)
from art.unittest_lib import testflow


@pytest.fixture(scope="class")
def deactivate_hosts(request):
    """
    Deactivate hosts (except HOST-0 and HOST-1)
    """
    hosts = net_config.HOSTS[2:]

    def fin():
        """
        Activate hosts
        """
        assert all(
            [hl_hosts.activate_host_if_not_up(host=host) for host in hosts]
        )
    request.addfinalizer(fin)

    for host in hosts:
        assert hl_hosts.deactivate_host_if_up(host=host)


@pytest.fixture()
def update_network_usages(request):
    """
    Update network usages
    """
    net_usages_dict = request.getfixturevalue("update_network_usages_params")
    cluster_obj = ll_clusters.get_cluster_object(cluster_name=net_config.CL_0)
    for net, net_usages in net_usages_dict.items():
        testflow.setup("Updating network: %s usages: %s", net, net_usages)
        assert ll_networks.update_cluster_network(
            positive=True, cluster=cluster_obj, network=net,
            usages=net_usages
        )


@pytest.fixture()
def remove_networks(request):
    """
    Remove networks by setup network host dict from test case
    """
    network_dicts = request.getfixturevalue("hosts_nets_nic_dict")

    def fin():
        """
        Remove networks by setup network host dict from test case
        """
        nets_to_remove = set()
        for net_dict in network_dicts.values():
            for net_params in net_dict.values():
                nets_to_remove.add(net_params.get("network"))

        assert hl_networks.remove_networks(
            positive=True, networks=list(nets_to_remove),
            data_center=net_config.DC_0
        )
    request.addfinalizer(fin)


@pytest.fixture()
def add_vnic_to_vms(request):
    """
    Add vNIC(s) with properties to VM(s)
    """
    add_vnic_dict = request.getfixturevalue("add_vnic_to_vms_params")

    def fin():
        """
        Remove vNIC(s) from VM(s)
        """
        results_list = []
        for vm, props_dict in add_vnic_dict.items():
            vnic = props_dict.get("name")
            text = "vNIC: {vnic} from VM: {vm}".format(vnic=vnic, vm=vm)

            testflow.teardown("Unplugging %s", text)
            res_update_nic = ll_vms.updateNic(
                positive=True, vm=vm, nic=vnic, plugged=False
            )
            results_list.append(res_update_nic)

            if res_update_nic:
                testflow.teardown("Removing %s", text)
                results_list.append(
                    ll_vms.removeNic(positive=True, vm=vm, nic=vnic)
                )

        assert all(results_list)
    request.addfinalizer(fin)

    for vm, props_dict in add_vnic_dict.items():
        assert ll_vms.addNic(positive=True, vm=vm, **props_dict)
