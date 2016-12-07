#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Fixtures for Host Network QoS
"""

import pytest

import art.rhevm_api.tests_lib.low_level.datacenters as ll_dc
import art.rhevm_api.tests_lib.low_level.networks as ll_networks
import config as host_qos_conf
import rhevmtests.networking.config as conf
from art.unittest_lib import testflow
from rhevmtests.networking.fixtures import NetworkFixtures


@pytest.fixture(scope="class")
def remove_qos_from_dc(request):
    """
    Remove QoS objects from Data-Center
    """
    host_network_qos = NetworkFixtures()
    qos_names = request.node.cls.qos_names
    qos_remove = getattr(request.cls, "qos_names_fin_remove", True)

    def fin():
        """
        Remove QoS from datacenter
        """
        if qos_remove:
            testflow.teardown(
                "Remove QoS from datacenter %s", host_network_qos.dc_0
            )
            assert all(
                [
                    ll_dc.delete_qos_from_datacenter(
                        datacenter=host_network_qos.dc_0, qos_name=qos
                    ) for qos in qos_names
                    ]
            )
    request.addfinalizer(fin)


@pytest.fixture(scope="class")
def create_host_net_qos(request, remove_qos_from_dc):
    """
    Create host QoS objects on Data-Center
    """
    qos_names = getattr(request.cls, "qos_names", list())
    upper_limit = getattr(request.cls, "upper_limit", None)
    realtime = getattr(request.cls, "realtime", None)

    for qos in qos_names:
        testflow.setup("Creating network QoS: %s", qos)
        assert ll_dc.add_qos_to_datacenter(
            datacenter=conf.DC_0, qos_name=qos,
            qos_type=conf.HOST_NET_QOS_TYPE,
            outbound_average_linkshare=host_qos_conf.TEST_VALUE,
            outbound_average_upperlimit=upper_limit,
            outbound_average_realtime=realtime
        )


@pytest.fixture(scope="class")
def update_network_in_datacenter(request):
    """
    Update network on Data-Center
    """
    host_network_qos = NetworkFixtures()
    qos_names = request.node.cls.qos_names
    nets = request.node.cls.nets

    for net, qos_name in zip(nets, qos_names):
        testflow.setup(
            "Update network: %s QoS: %s on DC: %s", net, qos_name,
            host_network_qos.dc_0
        )
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
    Update engine to have default weighted share and rate limit values
    """
    def fin():
        """
        Update engine to have default weighted share and rate limit values
        """
        testflow.teardown(
            "Setting QoS share: %s with default value: %s ",
            host_qos_conf.QOS_SHARE, host_qos_conf.DEFAULT_SHARE
        )
        cmd1 = "%s=%s" % (host_qos_conf.QOS_SHARE, host_qos_conf.DEFAULT_SHARE)
        conf.ENGINE.engine_config(action='set', param=cmd1, restart=False)

        testflow.teardown(
            "Setting QoS share: %s with default value: %s "
            "and restarting the engine", host_qos_conf.RATE_LIMIT,
            host_qos_conf.DEFAULT_RATE
        )
        cmd2 = "%s=%s" % (host_qos_conf.RATE_LIMIT, host_qos_conf.DEFAULT_RATE)
        conf.ENGINE.engine_config(action='set', param=cmd2)
    request.addfinalizer(fin)
