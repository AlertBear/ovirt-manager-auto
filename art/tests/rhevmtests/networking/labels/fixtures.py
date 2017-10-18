#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Fixtures for labels
"""

import pytest

import rhevmtests.networking.config as conf
import art.rhevm_api.tests_lib.high_level.hosts as hl_host
from art.rhevm_api.tests_lib.low_level import (
    hosts as ll_hosts,
    networks as ll_networks
)


@pytest.fixture(scope="class")
def add_label_nic_and_network(request):
    """
    Attach label on host NIC and network
    """
    labels_list = getattr(request.node.cls, "labels_list")
    labels_dict_to_send = dict()
    for params in labels_list:
        lb = params.get("label")
        host_idx = params.get("host")
        nic_idx = params.get("nic")
        networks = params.get("networks")
        labels_dict_to_send[lb] = {}
        if host_idx is not None:
            labels_dict_to_send[lb]["host"] = ll_hosts.get_host_object(
                host_name=conf.HOSTS[host_idx]
            )

        if nic_idx is not None:
            if isinstance(nic_idx, basestring):
                labels_dict_to_send[lb]["nic"] = nic_idx
            else:
                vds_host = conf.VDS_HOSTS[host_idx]
                labels_dict_to_send[lb]["nic"] = vds_host.nics[nic_idx]

        if networks:
            labels_dict_to_send[lb]["networks"] = networks

        assert ll_networks.add_label(**labels_dict_to_send)
        labels_dict_to_send = dict()


@pytest.fixture(scope="class")
def move_host_to_another_cluster(request):
    """
    Deactivate host and move it to another cluster
    """
    def fin():
        """
        Move host back to it's original cluster
        """
        assert hl_host.move_host_to_another_cluster(
            host=conf.HOST_1_NAME, cluster=conf.CL_0
        )
    request.addfinalizer(fin)

    assert ll_hosts.deactivate_host(positive=True, host=conf.HOST_1_NAME)
