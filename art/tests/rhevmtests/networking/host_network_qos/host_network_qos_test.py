#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Testing network host QoS feature.
Create, update and remove tests will be done for network host QoS feature
"""

import pytest

import art.rhevm_api.tests_lib.high_level.host_network as hl_host_network
import art.rhevm_api.tests_lib.low_level.networks as ll_networks
import config as conf
import helper
import rhevmtests.networking.config as net_conf
import rhevmtests.networking.helper as net_helper
from art.test_handler.tools import polarion
from art.unittest_lib import NetworkTest, testflow, attr
from fixtures import (
    attach_network_to_host, remove_qos_from_dc, create_host_net_qos,
    set_default_engine_properties, update_network_in_datacenter
)


@attr(tier=2)
@pytest.mark.usefixtures(
    attach_network_to_host.__name__,
)
class TestHostNetQOSCase01(NetworkTest):
    """
     Try to remove anonymous host network QoS when several networks with QoS
     are attached to the host
    """
    __test__ = True
    nets = conf.NETS[1][:2]
    nics = [1, 1]
    qos = conf.QOS_1

    @polarion("RHEVM3-14300")
    def test_01_remove_anonymous_qos_for_network_on_host_nic(self):
        """
        Try to remove QoS from the first network
        """
        network_host_api_dict_1 = {
            "update": {
                "1": {
                    "network": self.nets[0],
                    "nic": net_conf.HOST_0_NICS[1],
                    "qos": {
                        "type_": conf.HOST_NET_QOS_TYPE
                    }
                }
            }
        }

        testflow.step(
            "Try to remove QoS from %s on %s", self.nets[0],
            net_conf.HOST_0_NICS[1]
        )
        assert not hl_host_network.setup_networks(
            host_name=net_conf.HOST_0_NAME, **network_host_api_dict_1
        )

    @polarion("RHEVM3-14354")
    def test_02_remove_anonymous_qos_from_all_networks_on_host_nic(self):
        """
        Remove QoS from both networks
        """
        network_host_api_dict_2 = {
            "update": {
                "1": {
                    "network": self.nets[1],
                    "nic": net_conf.HOST_0_NICS[1],
                    "qos": {
                        "type_": conf.HOST_NET_QOS_TYPE
                    },
                },
                "2": {
                    "network": self.nets[0],
                    "nic": net_conf.HOST_0_NICS[1],
                    "qos": {
                        "type_": conf.HOST_NET_QOS_TYPE
                    }
                }
            }
        }

        testflow.step("Positive: Remove QoS from network")
        assert hl_host_network.setup_networks(
            host_name=net_conf.HOST_0_NAME, **network_host_api_dict_2
        )


@attr(tier=2)
@pytest.mark.usefixtures(
    create_host_net_qos.__name__,
    attach_network_to_host.__name__,
    remove_qos_from_dc.__name__,
)
class TestHostNetQOSCase02(NetworkTest):
    """
    1) Create network on DC/Cluster/Host without QoS
    2) Update network with QoS under DC
    3) Check that vdsCaps shows network with updated QoS values
    """
    __test__ = True
    nets = conf.NETS[2][:1]
    qos_names = conf.QOS_NAME[2][:1]
    uperlimit = conf.TEST_VALUE
    realtime = conf.TEST_VALUE
    nics = [1]
    qos = None
    qos_dict = {
        "rt": conf.TEST_VALUE * conf.MB_CONVERTER,
        "ul": conf.TEST_VALUE * conf.MB_CONVERTER,
        "ls": conf.TEST_VALUE
    }

    @polarion("RHEVM3-6540")
    def test_vds_caps_values(self):
        """
        1) Update network under DC with host network QoS profile (named)
        2) Check on VDSCaps that the QoS values are correct
        """
        testflow.step(
            "Update network %s with QoS %s", self.nets[0], self.qos_names[0]
        )
        assert ll_networks.update_network_in_datacenter(
            positive=True, network=self.nets[0], datacenter=net_conf.DC_0,
            qos_dict={
                "qos_name": self.qos_names[0],
                "datacenter": net_conf.DC_0
            }
        )
        assert helper.cmp_qos_with_vdscaps(
            net=self.nets[0], qos_dict=self.qos_dict
        )


@attr(tier=2)
@pytest.mark.usefixtures(
    attach_network_to_host.__name__,
    set_default_engine_properties.__name__,
)
class TestHostNetQOSCase03(NetworkTest):
    """
    Increase default Engine limitation for QoS and test that weighted share
    and rate configuration work well with new Engine configuration

    """
    __test__ = True
    nets = conf.NETS[3][:1]
    nics = [1]
    qos = None

    @polarion("RHEVM3-6527")
    def test_weight_share_rate_new_limit(self):
        """
        Update network on host NIC with QoS weighted share parameters
        """
        network_host_api_dict = {
            "update": {
                "1": {
                    "network": self.nets[0],
                    "nic": net_conf.HOST_0_NICS[1],
                    "qos": {
                        "type_": conf.HOST_NET_QOS_TYPE,
                        "outbound_average_linkshare": conf.DEFAULT_SHARE + 5,
                        "outbound_average_upperlimit": conf.DEFAULT_RATE + 1,
                        "outbound_average_realtime": conf.DEFAULT_RATE + 1
                    }
                }
            }
        }

        testflow.step(
            "Configure weighted share and rate limit on Engine to the value "
            "of %s and %s appropriately",
            conf.UPDATED_SHARE, conf.UPDATED_SHARE
        )
        cmd1 = "=".join([conf.QOS_SHARE, conf.UPDATED_SHARE])
        assert net_conf.ENGINE.engine_config(
            action='set', param=cmd1, restart=False
        ).get('results')

        cmd2 = "=".join([conf.RATE_LIMIT, conf.UPDATED_RATE])
        assert net_conf.ENGINE.engine_config(
            action='set', param=cmd2
        ).get('results')

        testflow.step(
            "Configuring %s on %s to have weighted share and rate limit to be "
            "above their original default values", self.nets[0],
            net_conf.HOST_0_NAME
        )
        assert hl_host_network.setup_networks(
            host_name=net_conf.HOST_0_NAME, **network_host_api_dict
        )


@attr(tier=2)
@pytest.mark.usefixtures(
    attach_network_to_host.__name__,
)
class TestHostNetQOSCase04(NetworkTest):
    """
    Test weighted share and rate limitation
    """
    __test__ = True
    nets = conf.NETS[4][:1]
    nics = [1]
    qos = None

    @polarion("RHEVM3-6528")
    def test_rate_share_limit(self):
        """
        Negative: Try to update networks on host NIC with:
        1)QoS rate limit beyond configured maximum
        2)QoS committed rate beyond configured maximum
        3) weighted share beyond configured maximum
        """

        host_qos_dict_1 = {
            "update": {
                "1": {
                    "network": self.nets[0],
                    "nic": net_conf.HOST_0_NICS[1],
                    "qos": {
                        "type_": conf.HOST_NET_QOS_TYPE,
                        "outbound_average_linkshare": conf.TEST_VALUE,
                        "outbound_average_upperlimit": conf.DEFAULT_RATE + 1
                    }
                }
            }
        }

        host_qos_dict_2 = {
            "update": {
                "2": {
                    "network": self.nets[0],
                    "nic": net_conf.HOST_0_NICS[1],
                    "qos": {
                        "type_": conf.HOST_NET_QOS_TYPE,
                        "outbound_average_linkshare": conf.TEST_VALUE,
                        "outbound_average_realtime": conf.DEFAULT_RATE + 1
                    }
                }
            }
        }

        host_qos_dict_3 = {
            "update": {
                "3": {
                    "network": self.nets[0],
                    "nic": net_conf.HOST_0_NICS[1],
                    "qos": {
                        "type_": conf.HOST_NET_QOS_TYPE,
                        "outbound_average_linkshare": conf.DEFAULT_SHARE + 1,
                    }
                }
            }
        }

        for net_dict in (
            host_qos_dict_1, host_qos_dict_2, host_qos_dict_3
        ):
            testflow.step(
                "Negative: Try updating %s on %s with %s ",
                self.nets[0], net_conf.HOST_0_NAME, net_dict
            )
            assert not hl_host_network.setup_networks(
                host_name=net_conf.HOST_0_NAME, **net_dict
            )


@attr(tier=2)
@pytest.mark.incremental
@pytest.mark.usefixtures(
    remove_qos_from_dc.__name__,
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
    __test__ = True
    net1 = conf.NETS[5][0]
    net2 = conf.NETS[5][1]
    net3 = conf.NETS[5][2]
    qos_names = conf.QOS_NAME[5][:4]

    @polarion("RHEVM3-6532")
    def test_01_add_network_qos(self):
        """
        1) Create new Host Network QoS profile under DC
        2) Negative: Try to configure committed rate higher than rate limit
        3) Configure committed rate lower than rate limit
        """
        testflow.step(
            "Negative: Try to create new Network QoS profile under DC"
            "with committed rate value higher than rate limit value"
        )
        assert net_helper.create_host_net_qos(
            qos_name=self.qos_names[0],
            positive=False,
            outbound_average_linkshare=conf.TEST_VALUE,
            outbound_average_upperlimit=conf.TEST_VALUE,
            outbound_average_realtime=conf.TEST_VALUE + 2
        )

        testflow.step(
            "Create new Network QoS profile under DC with committed rate "
            "value lower than rate limit value"
        )
        assert net_helper.create_host_net_qos(
            qos_name=self.qos_names[0],
            outbound_average_linkshare=conf.TEST_VALUE,
            outbound_average_upperlimit=conf.TEST_VALUE,
            outbound_average_realtime=conf.TEST_VALUE - 2
        )

    @polarion("RHEVM3-6535")
    def test_02_create_qos_when_add_network(self):
        """
        Create QoS when creating a new network on the setup
        """
        testflow.step("Create QoS when creating a new network on the setup")
        assert ll_networks.add_network(
            positive=True, name=self.net1, data_center=net_conf.DC_0,
            qos_dict={
                "datacenter": net_conf.DC_0,
                "qos_name": self.qos_names[1],
                "qos_type": conf.HOST_NET_QOS_TYPE,
                "outbound_average_linkshare": conf.TEST_VALUE
            }
        )

    @polarion("RHEVM3-14276")
    def test_03_update_network_with_qos(self):
        """
        Update existing network on the setup with the QoS from test01
        """
        testflow.step("Update another network with the %s", self.qos_names[1])
        assert ll_networks.update_network_in_datacenter(
            positive=True, network=self.net2, datacenter=net_conf.DC_0,
            qos_dict={
                "qos_name": self.qos_names[1],
                "datacenter": net_conf.DC_0
            }
        )

    @polarion("RHEVM3-6536")
    def test_04_create_qos_when_update_network(self):
        """
        1) Create QoS when editing a network on the setup
        2) Create another QoS when editing the same network
        3) Update the network with unlimited QoS
        """
        testflow.step(
            "Create QoS %s when updating %s", self.qos_names[2], self.net3
        )
        assert ll_networks.update_network_in_datacenter(
            positive=True, network=self.net3, datacenter=net_conf.DC_0,
            qos_dict={
                "datacenter": net_conf.DC_0,
                "qos_name": self.qos_names[2],
                "qos_type": conf.HOST_NET_QOS_TYPE,
                "outbound_average_linkshare": conf.TEST_VALUE
            }
        )

    @polarion("RHEVM3-14272")
    def test_05_create_qos_when_update_network_with_qos(self):
        """
        Create another QoS when editing the same network
        """
        testflow.step(
            "Create QoS %s when updating %s", self.qos_names[3], self.net3
        )
        assert ll_networks.update_network_in_datacenter(
            positive=True, network=self.net3, datacenter=net_conf.DC_0,
            qos_dict={
                "datacenter": net_conf.DC_0,
                "qos_name": self.qos_names[3],
                "qos_type": conf.HOST_NET_QOS_TYPE,
                "outbound_average_linkshare": conf.TEST_VALUE
            }
        )

    @polarion("RHEVM3-14273")
    def test_06_unlimited_qos_when_update_network(self):
        """
        Update the network with unlimited QoS
        """
        testflow.step("Update network not to have QoS (unlimited)")
        assert ll_networks.update_network_in_datacenter(
            positive=True, network=self.net3, datacenter=net_conf.DC_0,
            qos_dict={}
        )


@attr(tier=2)
@pytest.mark.usefixtures(
    create_host_net_qos.__name__,
    update_network_in_datacenter.__name__,
    remove_qos_from_dc.__name__,
)
class TestHostNetQOSCase06(NetworkTest):
    """
    1) Try to have network with and without QoS configured on the
    same NIC
    """
    __test__ = True
    nets = conf.NETS[6][:1]
    net2 = conf.NETS[6][1]
    qos_names = conf.QOS_NAME[6][:1]
    uperlimit = None
    realtime = None

    @polarion("RHEVM3-6533")
    def test_add_networks_qos_mixed_same_nic(self):
        """
        1) Try to attach both networks to the Host
        """
        network_host_api_dict = {
            "add": {
                "1": {
                    "network": self.nets[0],
                    "nic": net_conf.HOST_0_NICS[1],
                },
                "2": {
                    "network": self.net2,
                    "nic": net_conf.HOST_0_NICS[1],
                },
            }
        }

        testflow.step(
            "Attach network %s (with QOS) and network %s (without QOS) to %s "
            "on %s",
            self.nets[0], self.net2, net_conf.HOST_0_NICS[1],
            net_conf.HOST_0_NAME
        )
        assert not hl_host_network.setup_networks(
            host_name=net_conf.HOST_0_NAME, **network_host_api_dict
        )


@attr(tier=2)
@pytest.mark.usefixtures(
    create_host_net_qos.__name__,
    update_network_in_datacenter.__name__,
    attach_network_to_host.__name__,
)
class TestHostNetQOSCase07(NetworkTest):
    """
    Remove host network QoS that is attached to the Network on the Host
    """
    __test__ = True
    nets = conf.NETS[7][:1]
    qos_names = conf.QOS_NAME[7][:1]
    nics = [1]
    qos = None
    uperlimit = None
    realtime = None

    @polarion("RHEVM3-6537")
    def test_remove_network_qos(self):
        """
        1) Remove host network QoS that is attached to the network on host
        2) Check that the network is unsynced
        3) Sync the network
        """
        net_helper.remove_qos_from_dc(qos_name=self.qos_names[0])
        testflow.step("Check the network is unsynced")
        assert not net_helper.networks_sync_status(
            host=net_conf.HOST_0_NAME, networks=self.nets
        )
        testflow.step("Sync the network")
        assert net_helper.sync_networks(
            host=net_conf.HOST_0_NAME, networks=self.nets
        )


@attr(tier=2)
@pytest.mark.usefixtures(
    attach_network_to_host.__name__,
)
class TestHostNetQOSCase08(NetworkTest):
    """
    Attach network with QoS to host NIC
    """
    __test__ = True
    nets = conf.NETS[8][:1]
    nics = [1]
    qos = conf.QOS_2
    qos_dict = {
        "rt": (conf.TEST_VALUE - 1) * conf.MB_CONVERTER,
        "ul": (conf.TEST_VALUE + 1) * conf.MB_CONVERTER,
        "ls": conf.TEST_VALUE
    }

    @polarion("RHEVM3-6534")
    def test_qos_for_network_on_host_nic(self):
        """
        Attach network to host NIC with QoS parameters (Anonymous' QoS)
        """
        testflow.step(
            "Attach network to host NIC with QoS parameters (Anonymous' QoS)"
        )
        assert helper.cmp_qos_with_vdscaps(
            net=self.nets[0], qos_dict=self.qos_dict
        )


@attr(tier=2)
@pytest.mark.usefixtures(
    create_host_net_qos.__name__,
    update_network_in_datacenter.__name__,
    attach_network_to_host.__name__,
)
class TestHostNetQOSCase09(NetworkTest):
    """
     Remove host network QoS when several networks with QoS are attached
     to the host (named)
    """
    __test__ = True
    nets = conf.NETS[9][:2]
    qos_names = conf.QOS_NAME[9][:2]
    nics = [1, 1]
    qos = None
    uperlimit = None
    realtime = None

    @polarion("RHEVM3-6538")
    def test_remove_network_qos(self):
        """
        1) Remove host network QoS that is attached to the first network
        on the host
        2) Check that the first network is unsynced
        3) Remove host network QoS that is attached to the second network
        on the host
        4) Check that the second network is unsynced
        5) Sync both networks on the host
        """
        for qos_name, net in zip(self.qos_names, self.nets):
            net_helper.remove_qos_from_dc(qos_name=qos_name)
            testflow.step("Check the network %s is unsynced", net)
            assert not net_helper.networks_sync_status(
                host=net_conf.HOST_0_NAME, networks=[net]
            )

        testflow.step("Sync both networks")
        assert net_helper.sync_networks(
            host=net_conf.HOST_0_NAME, networks=self.nets
        )
