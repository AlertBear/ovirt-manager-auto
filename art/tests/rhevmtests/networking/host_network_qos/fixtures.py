#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Fixtures for host_network_qos
"""

import pytest

import art.rhevm_api.tests_lib.high_level.host_network as hl_host_network
import art.rhevm_api.tests_lib.low_level.networks as ll_networks
import config as qos_conf
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
        Finalizer for remove networks from setup
        """
        host_network_qos.remove_networks_from_setup(
            hosts=host_network_qos.host_0_name
        )
    request.addfinalizer(fin)

    host_network_qos.prepare_networks_on_setup(
        networks_dict=qos_conf.NETS_DICT, dc=host_network_qos.dc_0,
        cluster=host_network_qos.cluster_0
    )


@pytest.fixture(scope="class")
def teardown_all_cases(request, host_network_qos_prepare_setup):
    """
    Teardown for all cases
    """
    host_network_qos = NetworkFixtures()

    def fin():
        """
        Finalizer for clean host interfaces
        """
        hl_host_network.clean_host_interfaces(
            host_name=host_network_qos.host_0_name
        )
    request.addfinalizer(fin)


@pytest.fixture(scope="class")
def fixture_case_01(request, teardown_all_cases):
    """
    Fixture for case01
    """
    host_network_qos = NetworkFixtures()
    nets = qos_conf.NETS[1][:2]
    sn_dict = {
        "add": {
            "1": {
                "network": nets[0],
                "nic": host_network_qos.host_0_nics[1],
                "qos": {
                    "type_": qos_conf.HOST_NET_QOS_TYPE,
                    "outbound_average_linkshare": qos_conf.TEST_VALUE,
                    "outbound_average_realtime": qos_conf.TEST_VALUE,
                    "outbound_average_upperlimit": qos_conf.TEST_VALUE
                }
            },
            "2": {
                "network": nets[1],
                "nic": host_network_qos.host_0_nics[1],
                "qos": {
                    "type_": qos_conf.HOST_NET_QOS_TYPE,
                    "outbound_average_linkshare": qos_conf.TEST_VALUE,
                    "outbound_average_realtime": qos_conf.TEST_VALUE,
                    "outbound_average_upperlimit": qos_conf.TEST_VALUE
                }
            }
        }
    }
    assert hl_host_network.setup_networks(
        host_name=host_network_qos.host_0_name, **sn_dict
    )


@pytest.fixture(scope="class")
def fixture_case_02(request, teardown_all_cases):
    """
    Fixture for case02
    """
    host_network_qos = NetworkFixtures()
    net1 = qos_conf.NETS[2][0]
    qos_name = qos_conf.QOS_NAME[13][0]

    def fin():
        """
        Finalizer for remove QoS from setup
        """
        network_helper.remove_qos_from_dc(qos_name=qos_name)
    request.addfinalizer(fin)

    network_helper.create_host_net_qos(
        qos_name=qos_name,
        outbound_average_linkshare=qos_conf.TEST_VALUE,
        outbound_average_upperlimit=qos_conf.TEST_VALUE,
        outbound_average_realtime=qos_conf.TEST_VALUE
    )
    sn_dict = {
        "add": {
            "1": {
                "network": net1,
                "nic": host_network_qos.host_0_nics[1],
            },
        }
    }
    assert hl_host_network.setup_networks(
        host_name=host_network_qos.host_0_name, **sn_dict
    )


@pytest.fixture(scope="class")
def fixture_case_03(request, teardown_all_cases):
    """
    Fixture for case03
    """
    host_network_qos = NetworkFixtures()
    net = qos_conf.NETS[3][0]

    def fin():
        """
        Finalizer for Update engine to have default value for the weighted
        share and rate limit
        """
        cmd1 = "=".join([qos_conf.QOS_SHARE, str(qos_conf.DEFAULT_SHARE)])
        conf.test_utils.set_engine_properties(
            conf.ENGINE, [cmd1], restart=False
        )
        cmd2 = "=".join([qos_conf.RATE_LIMIT, str(qos_conf.DEFAULT_RATE)])
        conf.test_utils.set_engine_properties(conf.ENGINE, [cmd2])
    request.addfinalizer(fin)

    sn_dict = {
        "add": {
            "1": {
                "network": net,
                "nic": host_network_qos.host_0_nics[1],
            }
        }
    }

    assert hl_host_network.setup_networks(
        host_name=host_network_qos.host_0_name, **sn_dict
    )


@pytest.fixture(scope="class")
def fixture_case_04(request, teardown_all_cases):
    """
    Fixture for case04
    """
    host_network_qos = NetworkFixtures()
    net1 = qos_conf.NETS[4][0]

    sn_dict = {
        "add": {
            "1": {
                "network": net1,
                "nic": host_network_qos.host_0_nics[1],
            },
        }
    }
    assert hl_host_network.setup_networks(
        host_name=host_network_qos.host_0_name, **sn_dict
    )


@pytest.fixture(scope="class")
def fixture_case_05(request, teardown_all_cases):
    """
    Fixture for case05
    """
    qos_name = qos_conf.QOS_NAME[5][0]

    def fin():
        """
        Finalizer for remove QoS from setup
        """
        network_helper.remove_qos_from_dc(qos_name=qos_name)
    request.addfinalizer(fin)


@pytest.fixture(scope="class")
def fixture_case_06(request, teardown_all_cases):
    """
    Fixture for case06
    """
    host_network_qos = NetworkFixtures()
    net1 = qos_conf.NETS[6][0]
    qos_name = qos_conf.QOS_NAME[6][0]

    def fin():
        """
        Finalizer for remove QoS from setup
        """
        network_helper.remove_qos_from_dc(qos_name=qos_name)
    request.addfinalizer(fin)

    network_helper.create_host_net_qos(
        qos_name=qos_name, outbound_average_linkshare=qos_conf.TEST_VALUE,
    )

    assert ll_networks.update_network_in_datacenter(
        positive=True, network=net1, datacenter=host_network_qos.dc_0,
        qos_dict={
            "qos_name": qos_name,
            "datacenter": host_network_qos.dc_0
        }
    )


@pytest.fixture(scope="class")
def fixture_case_07(request, teardown_all_cases):
    """
    Fixture for case07
    """
    host_network_qos = NetworkFixtures()
    net1 = qos_conf.NETS[7][0]
    qos_name = qos_conf.QOS_NAME[7][0]

    network_helper.create_host_net_qos(
        qos_name=qos_name, outbound_average_linkshare=qos_conf.TEST_VALUE,
    )

    assert ll_networks.update_network_in_datacenter(
        positive=True, network=net1, datacenter=host_network_qos.dc_0,
        qos_dict={
            "qos_name": qos_name,
            "datacenter": host_network_qos.dc_0
        }
    )
    sn_dict = {
        "add": {
            "1": {
                "network": net1,
                "nic": host_network_qos.host_0_nics[1],
            },
        }
    }
    assert hl_host_network.setup_networks(
        host_name=host_network_qos.host_0_name, **sn_dict
    )


@pytest.fixture(scope="class")
def fixture_case_08(request, teardown_all_cases):
    """
    Fixture for case08
    """
    qos_name = qos_conf.QOS_NAME[8][0]

    def fin():
        """
        Finalizer for remove QoS from setup
        """
        network_helper.remove_qos_from_dc(qos_name=qos_name)
    request.addfinalizer(fin)


@pytest.fixture(scope="class")
def fixture_case_09(request, teardown_all_cases):
    """
    Fixture for case09
    """
    qos_name1 = qos_conf.QOS_NAME[9][0]
    qos_name2 = qos_conf.QOS_NAME[9][1]

    def fin():
        """
        Finalizer for remove QoS from setup
        """
        for qos in (qos_name1, qos_name2):
            network_helper.remove_qos_from_dc(qos_name=qos)
    request.addfinalizer(fin)


@pytest.fixture(scope="class")
def fixture_case_10(request, teardown_all_cases):
    """
    Fixture for case10
    """
    host_network_qos = NetworkFixtures()
    net = qos_conf.NETS[10][0]
    sn_dict = {
        "add": {
            "1": {
                "network": net,
                "nic": host_network_qos.host_0_nics[1],
                "qos": {
                    "type_": qos_conf.HOST_NET_QOS_TYPE,
                    "outbound_average_linkshare": qos_conf.TEST_VALUE,
                    "outbound_average_realtime": qos_conf.TEST_VALUE - 1,
                    "outbound_average_upperlimit": qos_conf.TEST_VALUE + 1
                }
            }
        }
    }
    assert hl_host_network.setup_networks(
        host_name=host_network_qos.host_0_name, **sn_dict
    )


@pytest.fixture(scope="class")
def fixture_case_11(request, teardown_all_cases):
    """
    Fixture for case11
    """
    host_network_qos = NetworkFixtures()
    nets = qos_conf.NETS[11][:2]
    qos_names = qos_conf.QOS_NAME[11][:2]

    for qos_name in qos_names:
        network_helper.create_host_net_qos(
            qos_name=qos_name, outbound_average_linkshare=qos_conf.TEST_VALUE,
        )

    for net, qos_name in zip(nets, qos_names):
        assert ll_networks.update_network_in_datacenter(
            positive=True, network=net, datacenter=host_network_qos.dc_0,
            qos_dict={
                "qos_name": qos_name,
                "datacenter": host_network_qos.dc_0
            }
        )
    sn_dict = {
        "add": {
            "1": {
                "network": nets[0],
                "nic": host_network_qos.host_0_nics[1],
            },
            "2": {
                "network": nets[1],
                "nic": host_network_qos.host_0_nics[1],
            },
        }
    }

    assert hl_host_network.setup_networks(
        host_name=host_network_qos.host_0_name, **sn_dict
    )
