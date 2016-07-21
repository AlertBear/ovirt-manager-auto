#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Fixtures for host_network_qos
"""

import pytest

import art.rhevm_api.tests_lib.high_level.host_network as hl_host_network
import art.rhevm_api.tests_lib.low_level.networks as ll_networks
import config as host_qos_conf
import rhevmtests.networking.config as conf
import rhevmtests.networking.helper as network_helper
from rhevmtests.networking.fixtures import NetworkFixtures


@pytest.fixture(scope="module")
def host_network_qos_prepare_setup(request):
    """
    Prepare setup
    """
    host_network_qos = NetworkFixtures()

    def fin():
        """
        Remove networks from setup
        """
        host_network_qos.remove_networks_from_setup(
            hosts=host_network_qos.host_0_name
        )
    request.addfinalizer(fin)

    host_network_qos.prepare_networks_on_setup(
        networks_dict=host_qos_conf.NETS_DICT, dc=host_network_qos.dc_0,
        cluster=host_network_qos.cluster_0
    )


@pytest.fixture(scope="class")
def attach_network_to_host(request, host_network_qos_prepare_setup):
    """
    Attach network to host.
    """
    host_network_qos = NetworkFixtures()
    nic_list = request.node.cls.nics
    nets = request.node.cls.nets
    qos = request.node.cls.qos
    sn_dict = {
        "add": {}
    }

    def fin():
        """
        Finalizer for clean host interfaces
        """
        hl_host_network.clean_host_interfaces(
            host_name=host_network_qos.host_0_name
        )
    request.addfinalizer(fin)

    for network, nic in zip(nets, nic_list):
        sn_dict["add"][network] = {
            "network": network,
            "nic": host_network_qos.host_0_nics[nic],
        }
        if qos:
            sn_dict["add"][network]["qos"] = qos

    assert hl_host_network.setup_networks(
        host_name=host_network_qos.host_0_name, **sn_dict
    )


@pytest.fixture(scope="class")
def remove_qos_from_dc(request, host_network_qos_prepare_setup):
    """
    Remove qos from dc.
    """
    qos_names = request.node.cls.qos_names

    def fin():
        """
        Finalizer for remove QoS from setup.
        """
        for qos in qos_names:
            network_helper.remove_qos_from_dc(qos_name=qos)
    request.addfinalizer(fin)


@pytest.fixture(scope="class")
def create_host_net_qos(request, host_network_qos_prepare_setup):
    """
    Create host net qos.
    """
    qos_names = request.node.cls.qos_names
    uperlimit = request.node.cls.uperlimit
    realtime = request.node.cls.realtime

    for qos in qos_names:
        network_helper.create_host_net_qos(
            qos_name=qos, outbound_average_linkshare=host_qos_conf.TEST_VALUE,
            outbound_average_upperlimit=uperlimit,
            outbound_average_realtime=realtime
        )


@pytest.fixture(scope="class")
def update_network_in_datacenter(request):
    """
    Update network in datacenter.
    """
    host_network_qos = NetworkFixtures()
    qos_names = request.node.cls.qos_names
    nets = request.node.cls.nets

    for net, qos_name in zip(nets, qos_names):
        assert ll_networks.update_network_in_datacenter(
            positive=True, network=net, datacenter=host_network_qos.dc_0,
            qos_dict={
                "qos_name": qos_name,
                "datacenter": host_network_qos.dc_0
            }
        )


@pytest.fixture(scope="class")
def set_default_engine_properties(request):
    """
    Update engine to have default value for the weighted
    share and rate limit.
    """

    def fin():
        """
        Finalizer for Update engine to have default value for the weighted
        share and rate limit
        """
        cmd1 = "%s=%s" % (host_qos_conf.QOS_SHARE, host_qos_conf.DEFAULT_SHARE)
        conf.test_utils.set_engine_properties(
            conf.ENGINE, [cmd1], restart=False
        )
        cmd2 = "%s=%s" % (host_qos_conf.RATE_LIMIT, host_qos_conf.DEFAULT_RATE)
        conf.test_utils.set_engine_properties(conf.ENGINE, [cmd2])
    request.addfinalizer(fin)
