#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Tests for the Host Network QoS feature

The following elements will be created and modified during the testing:
Host NICs, networks, network QoS, engine QoS values
"""

import pytest

import art.rhevm_api.tests_lib.high_level.host_network as hl_host_network
import config as qos_conf
import helper
from art.rhevm_api.tests_lib.low_level import (
    datacenters as ll_dc,
    networks as ll_networks
)
from art.test_handler.tools import polarion
from art.unittest_lib import (
    NetworkTest,
    testflow,
    tier2,
)
from fixtures import (
    create_host_net_qos, remove_qos_from_dc,
    set_default_engine_properties, update_network_in_datacenter
)
from rhevmtests.networking import (
    config as conf,
    helper as net_helper
)
from rhevmtests.networking.fixtures import (  # noqa: F401
    clean_host_interfaces,
    setup_networks_fixture,
    remove_all_networks,
    create_and_attach_networks,
)


@pytest.mark.usefixtures(
    create_and_attach_networks.__name__,
    setup_networks_fixture.__name__
)
class TestHostNetQOSCase01(NetworkTest):
    """
    1.  Negative: try to remove anonymous host network QoS when several
        networks with QoS are attached to the host
    2.  Remove QoS from both networks
    3.  Attach network to host NIC with QoS parameters (anonymous QoS)
    """
    net_1 = qos_conf.NETS[1][0]
    net_2 = qos_conf.NETS[1][1]
    net_3 = qos_conf.NETS[1][2]
    dc = conf.DC_0

    # create_and_attach_networks params
    create_networks = {
        "1": {
            "data_center": dc,
            "clusters": [conf.CL_0],
            "networks": qos_conf.CASE_1_NETS
        }
    }

    # remove_all_networks params
    remove_dcs_networks = [dc]

    hosts_nets_nic_dict = {
        0: {
            net_1: {
                "network": net_1,
                "nic": 1,
                "qos": qos_conf.QOS_1
            },
            net_2: {
                "network": net_2,
                "nic": 1,
                "qos": qos_conf.QOS_1
            },
            net_3: {
                "network": net_3,
                "nic": 2,
                "qos": qos_conf.QOS_2
            }
        }
    }

    @tier2
    @polarion("RHEVM3-14300")
    def test_01_remove_anonymous_qos_for_network_on_host_nic(self):
        """
        Negative: try to remove QoS from the first network
        """
        net_dict = {
            "update": {
                "1": {
                    "network": self.net_1,
                    "nic": conf.HOST_0_NICS[1],
                    "qos": {
                        "type_": qos_conf.HOST_NET_QOS_TYPE
                    }
                }
            }
        }

        testflow.step(
            "Negative: try to remove QoS from %s on %s", self.net_1,
            conf.HOST_0_NICS[1]
        )
        assert not hl_host_network.setup_networks(
            host_name=conf.HOST_0_NAME, **net_dict
        )

    @tier2
    @polarion("RHEVM3-14354")
    def test_02_remove_anonymous_qos_from_all_networks_on_host_nic(self):
        """
        Remove QoS from both networks
        """
        net_dict = {
            "update": {
                "1": {
                    "network": self.net_2,
                    "nic": conf.HOST_0_NICS[1],
                    "qos": {
                        "type_": qos_conf.HOST_NET_QOS_TYPE
                    },
                },
                "2": {
                    "network": self.net_1,
                    "nic": conf.HOST_0_NICS[1],
                    "qos": {
                        "type_": qos_conf.HOST_NET_QOS_TYPE
                    }
                }
            }
        }

        testflow.step("Remove QoS from network")
        assert hl_host_network.setup_networks(
            host_name=conf.HOST_0_NAME, **net_dict
        )

    @tier2
    @polarion("RHEVM3-6534")
    def test_03_anonymous_qos_for_network_on_host_nic(self):
        """
        Attach network to host NIC with QoS parameters (Anonymous QoS)
        """
        qos_dict = {
            "rt": (qos_conf.TEST_VALUE - 1) * qos_conf.MB_CONVERTER,
            "ul": (qos_conf.TEST_VALUE + 1) * qos_conf.MB_CONVERTER,
            "ls": qos_conf.TEST_VALUE
        }

        testflow.step(
            "Attach network to host NIC with QoS parameters (Anonymous QoS)"
        )
        assert helper.cmp_qos_with_vdscaps(
            host_resource=conf.VDS_HOSTS[0], net=self.net_3, qos_dict=qos_dict
        )


@pytest.mark.usefixtures(
    create_and_attach_networks.__name__,
    create_host_net_qos.__name__,
    setup_networks_fixture.__name__
)
class TestHostNetQOSCase02(NetworkTest):
    """
    1) Create network on DC/Cluster/Host without QoS
    2) Update network with QoS under DC
    3) Check that vdsCaps shows network with updated QoS values
    """
    net_1 = qos_conf.NETS[2][0]
    dc = conf.DC_0

    # create_and_attach_networks params
    create_networks = {
        "1": {
            "data_center": dc,
            "clusters": [conf.CL_0],
            "networks": qos_conf.CASE_2_NETS
        }
    }

    # remove_all_networks params
    remove_dcs_networks = [dc]

    # setup_networks_fixture params
    hosts_nets_nic_dict = {
        0: {
            net_1: {
                "network": net_1,
                "nic": 1
            }
        }
    }
    qos_name_1 = qos_conf.QOS_NAME[2][0]

    # create_host_net_qos params
    qos_names = [qos_name_1]
    upper_limit = qos_conf.TEST_VALUE
    realtime = qos_conf.TEST_VALUE
    qos_dict = {
        "rt": qos_conf.TEST_VALUE * qos_conf.MB_CONVERTER,
        "ul": qos_conf.TEST_VALUE * qos_conf.MB_CONVERTER,
        "ls": qos_conf.TEST_VALUE
    }

    @tier2
    @polarion("RHEVM3-6540")
    def test_vds_caps_values(self):
        """
        1) Update network under DC with host network QoS profile (named)
        2) Check on VDSCaps that the QoS values are correct
        """
        testflow.step(
            "Update network: %s with QoS: %s", self.net_1, self.qos_name_1
        )
        net_helper.call_function_and_wait_for_sn(
            func=ll_networks.update_network_in_datacenter, content=self.net_1,
            positive=True, network=self.net_1, datacenter=conf.DC_0,
            qos_dict={
                "qos_name": self.qos_name_1,
                "datacenter": conf.DC_0
            }
        )
        testflow.step("Check on VDSCaps that the QoS values are correct")
        assert helper.cmp_qos_with_vdscaps(
            host_resource=conf.VDS_HOSTS[0], net=self.net_1,
            qos_dict=self.qos_dict
        )


@pytest.mark.usefixtures(
    create_and_attach_networks.__name__,
    setup_networks_fixture.__name__,
    set_default_engine_properties.__name__,
)
class TestHostNetQOSCase03(NetworkTest):
    """
    Increase default engine limitation for QoS, and test that weighted share
    and rate configuration works with the new engine configuration
    """
    net_1 = qos_conf.NETS[3][0]
    dc = conf.DC_0

    # create_and_attach_networks params
    create_networks = {
        "1": {
            "data_center": dc,
            "clusters": [conf.CL_0],
            "networks": qos_conf.CASE_3_NETS
        }
    }

    # remove_all_networks params
    remove_dcs_networks = [dc]

    # setup_networks_fixture params
    hosts_nets_nic_dict = {
        0: {
            net_1: {
                "network": net_1,
                "nic": 1,
                "qos": qos_conf.QOS_1
            }
        }
    }

    @tier2
    @polarion("RHEVM3-6527")
    def test_weight_share_rate_new_limit(self):
        """
        Update network on host NIC with new QoS weighted share parameters
        """
        network_host_api_dict = {
            "update": {
                "1": {
                    "network": self.net_1,
                    "nic": conf.HOST_0_NICS[1],
                    "qos": {
                        "type_": qos_conf.HOST_NET_QOS_TYPE,
                        "outbound_average_linkshare": (
                            qos_conf.SHARE_OVERLIMIT_C3
                        ),
                        "outbound_average_upperlimit": (
                            qos_conf.RATE_OVERLIMIT
                        ),
                        "outbound_average_realtime": (
                            qos_conf.RATE_OVERLIMIT
                        )
                    }
                }
            }
        }

        testflow.step(
            "Configure weighted share on engine to the value of %s",
            qos_conf.UPDATED_SHARE
        )
        cmd1 = "=".join([qos_conf.QOS_SHARE, qos_conf.UPDATED_SHARE])
        assert conf.ENGINE.engine_config(
            action='set', param=cmd1, restart=False
        ).get('results')

        testflow.step(
            "Configure rate limit on engine to the value of %s and "
            "restarting the engine", qos_conf.UPDATED_RATE
        )
        cmd2 = "=".join([qos_conf.RATE_LIMIT, qos_conf.UPDATED_RATE])
        assert conf.ENGINE.engine_config(
            action='set', param=cmd2
        ).get('results')

        testflow.step(
            "Configure %s on %s to have weighted share and rate limit to be "
            "above their original default values", self.net_1,
            conf.HOST_0_NAME
        )
        assert hl_host_network.setup_networks(
            host_name=conf.HOST_0_NAME, **network_host_api_dict
        )


@pytest.mark.usefixtures(
    create_and_attach_networks.__name__,
    setup_networks_fixture.__name__
)
class TestHostNetQOSCase04(NetworkTest):
    """
    Test weighted share and rate limitation
    """
    net_1 = qos_conf.NETS[4][0]
    dc = conf.DC_0

    # create_and_attach_networks params
    create_networks = {
        "1": {
            "data_center": dc,
            "clusters": [conf.CL_0],
            "networks": qos_conf.CASE_4_NETS
        }
    }

    # remove_all_networks params
    remove_dcs_networks = [dc]

    # setup_networks_fixture params
    hosts_nets_nic_dict = {
        0: {
            net_1: {
                "network": net_1,
                "nic": 1
            }
        }
    }

    @tier2
    @polarion("RHEVM3-6528")
    def test_rate_share_limit(self):
        """
        Negative: Try to update networks on host NIC with:
        1   QoS rate limit beyond configured maximum
        2   QoS committed rate beyond configured maximum
        3   weighted share beyond configured maximum
        """
        host_qos_dict_1 = {
            "update": {
                "1": {
                    "network": self.net_1,
                    "nic": conf.HOST_0_NICS[1],
                    "qos": {
                        "type_": qos_conf.HOST_NET_QOS_TYPE,
                        "outbound_average_linkshare": qos_conf.TEST_VALUE,
                        "outbound_average_upperlimit": qos_conf.RATE_OVERLIMIT
                    }
                }
            }
        }
        host_qos_dict_2 = {
            "update": {
                "2": {
                    "network": self.net_1,
                    "nic": conf.HOST_0_NICS[1],
                    "qos": {
                        "type_": qos_conf.HOST_NET_QOS_TYPE,
                        "outbound_average_linkshare": qos_conf.TEST_VALUE,
                        "outbound_average_realtime": qos_conf.RATE_OVERLIMIT
                    }
                }
            }
        }
        host_qos_dict_3 = {
            "update": {
                "3": {
                    "network": self.net_1,
                    "nic": conf.HOST_0_NICS[1],
                    "qos": {
                        "type_": qos_conf.HOST_NET_QOS_TYPE,
                        "outbound_average_linkshare": (
                            qos_conf.SHARE_OVERLIMIT_C4
                        ),
                    }
                }
            }
        }

        for net_dict in (host_qos_dict_1, host_qos_dict_2, host_qos_dict_3):
            testflow.step(
                "Negative: try updating %s on %s with %s ",
                self.net_1, conf.HOST_0_NAME, net_dict
            )
            assert not hl_host_network.setup_networks(
                host_name=conf.HOST_0_NAME, **net_dict
            )


@pytest.mark.incremental
@pytest.mark.usefixtures(
    create_and_attach_networks.__name__,
    remove_qos_from_dc.__name__
)
class TestHostNetQOSCase05(NetworkTest):
    """
    1) Add new network QOS (named) with:
        a) committed rate value higher than rate limit and fail.
        b) committed rate value lower than rate limit and succeed.
    2) Create QoS while creating a new network.
    3) Update another network with the QoS from previous step.
    4) Create QoS while updating existing network.
    5) Create another QoS when editing the same network.
    6) Update the network with unlimited QoS.
   """
    net_1 = qos_conf.NETS[5][0]
    net_2 = qos_conf.NETS[5][1]
    net_3 = qos_conf.NETS[5][2]
    dc = conf.DC_0

    # create_and_attach_networks params
    create_networks = {
        "1": {
            "data_center": dc,
            "clusters": [conf.CL_0],
            "networks": qos_conf.CASE_5_NETS
        }
    }

    # remove_all_networks params
    remove_dcs_networks = [dc]

    # remove_qos_from_dc params
    qos_name_1 = qos_conf.QOS_NAME[5][0]
    qos_name_2 = qos_conf.QOS_NAME[5][1]
    qos_name_3 = qos_conf.QOS_NAME[5][2]
    qos_name_4 = qos_conf.QOS_NAME[5][3]
    qos_names = [qos_name_1, qos_name_2, qos_name_3, qos_name_4]

    @tier2
    @polarion("RHEVM3-6532")
    def test_01_add_network_qos(self):
        """
        1) Create new Host Network QoS profile under DC
        2) Negative: Try to configure committed rate higher than rate limit
        3) Configure committed rate lower than rate limit
        """
        testflow.step(
            "Negative: try to create new Network QoS profile under DC"
            "with committed rate value higher than rate limit value"
        )
        assert not ll_dc.add_qos_to_datacenter(
            datacenter=conf.DC_0, qos_name=self.qos_name_1,
            qos_type=conf.HOST_NET_QOS_TYPE,
            outbound_average_linkshare=qos_conf.TEST_VALUE,
            outbound_average_upperlimit=qos_conf.TEST_VALUE,
            outbound_average_realtime=qos_conf.TEST_VALUE + 2
        )

        testflow.step(
            "Create new Network QoS profile under DC with committed rate "
            "value lower than rate limit value"
        )
        assert ll_dc.add_qos_to_datacenter(
            datacenter=conf.DC_0, qos_name=self.qos_name_1,
            qos_type=conf.HOST_NET_QOS_TYPE,
            outbound_average_linkshare=qos_conf.TEST_VALUE,
            outbound_average_upperlimit=qos_conf.TEST_VALUE,
            outbound_average_realtime=qos_conf.TEST_VALUE - 2
        )

    @tier2
    @polarion("RHEVM3-6535")
    def test_02_create_qos_when_add_network(self):
        """
        Create QoS when creating a new network on the setup
        """
        testflow.step("Create QoS when creating a new network on the setup")
        assert ll_networks.add_network(
            positive=True, name=self.net_1, data_center=conf.DC_0,
            qos_dict={
                "datacenter": conf.DC_0,
                "qos_name": self.qos_name_2,
                "qos_type": qos_conf.HOST_NET_QOS_TYPE,
                "outbound_average_linkshare": qos_conf.TEST_VALUE
            }
        )

    @tier2
    @polarion("RHEVM3-14276")
    def test_03_update_network_with_qos(self):
        """
        Update existing network on the setup with the QoS from test01
        """
        testflow.step("Update another network with the %s", self.qos_name_2)
        assert ll_networks.update_network_in_datacenter(
            positive=True, network=self.net_2, datacenter=conf.DC_0,
            qos_dict={
                "qos_name": self.qos_name_2,
                "datacenter": conf.DC_0
            }
        )

    @tier2
    @polarion("RHEVM3-6536")
    def test_04_create_qos_when_update_network(self):
        """
        1) Create QoS when editing a network on the setup
        2) Create another QoS when editing the same network
        3) Update the network with unlimited QoS
        """
        testflow.step(
            "Create QoS %s when updating %s", self.qos_name_3, self.net_3
        )
        assert ll_networks.update_network_in_datacenter(
            positive=True, network=self.net_3, datacenter=conf.DC_0,
            qos_dict={
                "datacenter": conf.DC_0,
                "qos_name": self.qos_name_3,
                "qos_type": qos_conf.HOST_NET_QOS_TYPE,
                "outbound_average_linkshare": qos_conf.TEST_VALUE
            }
        )

    @tier2
    @polarion("RHEVM3-14272")
    def test_05_create_qos_when_update_network_with_qos(self):
        """
        Create another QoS when editing the same network
        """
        testflow.step(
            "Create QoS %s when updating %s", self.qos_name_4, self.net_3
        )
        assert ll_networks.update_network_in_datacenter(
            positive=True, network=self.net_3, datacenter=conf.DC_0,
            qos_dict={
                "datacenter": conf.DC_0,
                "qos_name": self.qos_name_4,
                "qos_type": qos_conf.HOST_NET_QOS_TYPE,
                "outbound_average_linkshare": qos_conf.TEST_VALUE
            }
        )

    @tier2
    @polarion("RHEVM3-14273")
    def test_06_unlimited_qos_when_update_network(self):
        """
        Update the network with unlimited QoS
        """
        testflow.step("Update network not to have QoS (unlimited)")
        assert ll_networks.update_network_in_datacenter(
            positive=True, network=self.net_3, datacenter=conf.DC_0,
            qos_dict={}
        )


@pytest.mark.usefixtures(
    create_and_attach_networks.__name__,
    create_host_net_qos.__name__,
    update_network_in_datacenter.__name__
)
class TestHostNetQOSCase06(NetworkTest):
    """
    Try to have network with and without QoS configured on the same NIC
    """
    net_1 = qos_conf.NETS[6][0]
    net_2 = qos_conf.NETS[6][1]
    dc = conf.DC_0

    # create_and_attach_networks params
    create_networks = {
        "1": {
            "data_center": dc,
            "clusters": [conf.CL_0],
            "networks": qos_conf.CASE_6_NETS
        }
    }

    # remove_all_networks params
    remove_dcs_networks = [dc]

    # update_network_in_datacenter params
    nets = [net_1]
    qos_names = [qos_conf.QOS_NAME[6][0]]

    @tier2
    @polarion("RHEVM3-6533")
    def test_add_networks_qos_mixed_same_nic(self):
        """
        Try to attach both networks to the host
        """
        network_host_api_dict = {
            "add": {
                "1": {
                    "network": self.net_1,
                    "nic": conf.HOST_0_NICS[1]
                },
                "2": {
                    "network": self.net_2,
                    "nic": conf.HOST_0_NICS[1]
                }
            }
        }

        testflow.step(
            "Negative: try to attach networks: %s (with QOS) and %s "
            "(without QOS) to NIC: %s on HOST: %s", self.net_1, self.net_2,
            conf.HOST_0_NICS[1], conf.HOST_0_NAME
        )
        assert not hl_host_network.setup_networks(
            host_name=conf.HOST_0_NAME, **network_host_api_dict
        )
