"""
Testing Network Custom properties feature.
1 DC, 1 Cluster, 1 Host will be created for testing.
"Network Custom properties will be tested for untagged, tagged, bond scenarios.
It will cover scenarios for VM/non-VM networks.
"""

import pytest

import art.rhevm_api.tests_lib.high_level.host_network as hl_host_network
import art.rhevm_api.tests_lib.low_level.networks as ll_networks
import config as custom_prop_conf
import rhevmtests.networking.config as conf
from art.test_handler.tools import polarion
from art.unittest_lib import attr, testflow, NetworkTest
from rhevmtests.networking import helper as network_helper
from rhevmtests.networking.fixtures import (
    setup_networks_fixture, clean_host_interfaces, NetworkFixtures
)  # flake8: noqa


@pytest.fixture(scope="module", autouse=True)
def prepare_setup(request):
    """
    Create networks on engine
    """
    custom_properties = NetworkFixtures()

    def fin():
        """
        Remove networks from engine
        """
        assert network_helper.remove_networks_from_setup(
            hosts=custom_properties.host_0_name
        )
    request.addfinalizer(fin)

    network_helper.prepare_networks_on_setup(
        networks_dict=custom_prop_conf.NETS_DICT, dc=custom_properties.dc_0,
        cluster=custom_properties.cluster_0
    )


@attr(tier=2)
@pytest.mark.usefixtures(setup_networks_fixture.__name__)
class TestNetworkCustomPropertiesCase01(NetworkTest):
    """
    Verify bridge_opts exists for VM network
    Verify bridge_opts doesn't exist for the non-VM network
    Verify bridge_opts exists for VM VLAN network over BOND
    Verify bridge_opts doesn't exist for the non-VM VLAN network over BOND
    """
    __test__ = True
    net_1 = custom_prop_conf.NETS[1][0]
    net_2 = custom_prop_conf.NETS[1][1]
    net_3 = custom_prop_conf.NETS[1][2]
    net_4 = custom_prop_conf.NETS[1][3]
    bond_1 = "bond10"
    hosts_nets_nic_dict = {
        0: {
            net_1: {
                "nic": 1,
                "network": net_1,
            },
            net_2: {
                "nic": 2,
                "network": net_2,
            },
            net_3: {
                "nic": bond_1,
                "network": net_3,
                "slaves": [-1, -2]
            },
            net_4: {
                "nic": bond_1,
                "network": net_4,
            }
        }
    }

    @polarion("RHEVM3-4178")
    def test_check_bridge_opts_exist(self):
        """
        Verify bridge_opts exists for VM network
        Verify bridge_opts doesn't exist for the non-VM network
        """
        testflow.step(
            "Check that bridge_opts exists for VM network %s", self.net_1
        )
        assert ll_networks.check_bridge_file_exist(
            positive=True, vds_resource=conf.VDS_0_HOST, bridge_name=self.net_1
        )
        testflow.step(
            "Check that bridge_opts doesn't exists for non-VM network %s",
            self.net_2
            )
        assert ll_networks.check_bridge_file_exist(
            positive=False, vds_resource=conf.VDS_0_HOST,
            bridge_name=self.net_2
        )

    @polarion("RHEVM3-4179")
    def test_check_bridge_opts_exist_bond(self):
        """
        Verify bridge_opts exists for VM VLAN network over BOND
        Verify bridge_opts doesn't exist for the non-VM VLAN network over BOND
        """
        testflow.step(
            "Check that bridge_opts exists for VLAN VM network %s over BOND",
            self.net_3
        )
        assert ll_networks.check_bridge_file_exist(
            positive=True, vds_resource=conf.VDS_0_HOST, bridge_name=self.net_3
        )
        testflow.step(
            "Check that bridge_opts doesn't exists for non-VM VLAN network "
            "%s over BOND",
            self.net_4
        )
        assert ll_networks.check_bridge_file_exist(
            positive=False, vds_resource=conf.VDS_0_HOST,
            bridge_name=self.net_4
        )


@attr(tier=2)
@pytest.mark.usefixtures(setup_networks_fixture.__name__)
class TestNetworkCustomPropertiesCase02(NetworkTest):
    """
    Configure bridge_opts with non-default value
    Verify bridge_opts were updated
    Update bridge_opts with default value
    Verify bridge_opts were updated with the default value
    """
    __test__ = True
    net_1 = custom_prop_conf.NETS[2][0]
    priority_opts = custom_prop_conf.KEY1
    priority_value = custom_prop_conf.BRIDGE_OPTS.get(priority_opts)[1]
    priority_default = custom_prop_conf.DEFAULT_PRIORITY
    priority_default_value = custom_prop_conf.BRIDGE_OPTS.get(
        custom_prop_conf.KEY1
    )[0]
    properties_dict = {
        "bridge_opts": custom_prop_conf.PRIORITY
    }
    hosts_nets_nic_dict = {
        0: {
            net_1: {
                "nic": 1,
                "network": net_1,
                "properties": properties_dict
            }
        }
    }

    @polarion("RHEVM3-4180")
    def test_update_bridge_opts(self):
        """
        1) Verify bridge_opts have updated value for priority opts
        2) Update bridge_opts with the default value
        3) Verify bridge_opts have updated default value for priority opts
        """
        testflow.step(
            "Check that bridge_opts parameter %s have been updated "
            "to %s", self.priority_opts, self.priority_value
        )
        assert ll_networks.check_bridge_opts(
            vds_resource=conf.VDS_0_HOST, bridge_name=self.net_1,
            opts=self.priority_opts, value=self.priority_value
        )
        testflow.step(
            "Update bridge_opts %s with %s", self.priority_opts,
            self.priority_default
        )
        network_host_api_dict = {
            "update": {
                "1": {
                    "network": self.net_1,
                    "properties": {
                        "bridge_opts": self.priority_default
                    }
                }
            }
        }
        assert hl_host_network.setup_networks(
            host_name=conf.HOST_0_NAME, **network_host_api_dict
        )
        testflow.step(
            "Check that bridge_opts %s has beed updated to %s",
            self.priority_opts, self.priority_default
        )
        assert ll_networks.check_bridge_opts(
            vds_resource=conf.VDS_0_HOST, bridge_name=self.net_1,
            opts=self.priority_opts, value=self.priority_default_value
        )


@attr(tier=2)
@pytest.mark.usefixtures(setup_networks_fixture.__name__)
class TestNetworkCustomPropertiesCase03(NetworkTest):
    """
    Configure bridge_opts with non-default value
    Verify bridge_opts was updated
    Update the network with additional bridge_opts key: value pair
    Verify bridge_opts were updated with both values
    Update both values of bridge_opts with the default values
    Verify bridge_opts were updated accordingly
    """
    __test__ = True
    bond_1 = "bond30"
    net_1 = custom_prop_conf.NETS[3][0]
    net_2 = custom_prop_conf.NETS[3][1]
    bridge_opts_items = custom_prop_conf.BRIDGE_OPTS.iteritems()
    querier_opts = custom_prop_conf.KEY2
    default_bridge_opts = " ".join(
        [
            custom_prop_conf.DEFAULT_PRIORITY,
            custom_prop_conf.DEFAULT_MULT_QUERIER
        ]
    )
    non_default_bridge_opts = " ".join(
        [custom_prop_conf.PRIORITY, custom_prop_conf.MULT_QUERIER]
    )
    properties_dict = {
        "bridge_opts": custom_prop_conf.PRIORITY
    }
    hosts_nets_nic_dict = {
        0: {
            net_1: {
                "nic": 1,
                "network": net_1,
                "properties": properties_dict
            },
            net_2: {
                "nic": bond_1,
                "network": net_2,
                "slaves": [-1, -2],
                "properties": properties_dict
            }
        }
    }

    @polarion("RHEVM3-4181")
    def test_check_several_bridge_opts_exist_nic(self):
        """
        1) Update bridge_opts with additional parameter (multicast_querier)
        2) Verify bridge_opts have updated value for Priority and
            multicast_querier
        3) Update bridge_opts with the default value for both keys
        4) Verify bridge_opts have updated default value
        """
        testflow.step(
            "Update bridge_opts %s with %s", self.querier_opts,
            self.non_default_bridge_opts
        )
        network_host_api_dict = {
            "update": {
                "1": {
                    "network": self.net_1,
                    "properties": {
                        "bridge_opts": self.non_default_bridge_opts
                    }
                }
            }
        }
        assert hl_host_network.setup_networks(
            host_name=conf.HOST_0_NAME, **network_host_api_dict
        )
        testflow.step(
            "Check that bridge_opts parameter %s have been updated "
            "to %s", self.querier_opts, self.non_default_bridge_opts
        )
        for key, value in self.bridge_opts_items:
            assert ll_networks.check_bridge_opts(
                vds_resource=conf.VDS_0_HOST, bridge_name=self.net_1,
                opts=key, value=value[1]
            )
        testflow.step(
            "Update bridge_opts %s with %s", self.querier_opts,
            self.default_bridge_opts
        )
        network_host_api_dict = {
            "update": {
                "1": {
                    "network": self.net_1,
                    "properties": {
                        "bridge_opts": self.default_bridge_opts
                    }
                }
            }
        }
        assert hl_host_network.setup_networks(
            host_name=conf.HOST_0_NAME, **network_host_api_dict
        )
        testflow.step(
            "Check that bridge_opts parameter %s have been updated "
            "to %s", self.querier_opts, self.default_bridge_opts
        )
        for key, value in self.bridge_opts_items:
            assert ll_networks.check_bridge_opts(
                vds_resource=conf.VDS_0_HOST, bridge_name=self.net_1,
                opts=key, value=value[0]
            )

    @polarion("RHEVM3-4182")
    def test_check_several_bridge_opts_exist_bond(self):
        """
        1) Update bridge_opts with additional parameter (multicast_querier)
        2) Veify bridge_opts have updated value for Priority and
        multicast_querier
        3) Update bridge_opts with the default value for both keys
        4) Verify bridge_opts have updated default value
        """
        testflow.step(
            "Update bridge_opts %s with %s over BOND", self.querier_opts,
            self.non_default_bridge_opts
        )
        network_host_api_dict = {
            "update": {
                "1": {
                    "network": self.net_2,
                    "properties": {
                        "bridge_opts": self.non_default_bridge_opts
                    }
                }
            }
        }
        assert hl_host_network.setup_networks(
            host_name=conf.HOST_0_NAME, **network_host_api_dict
        )
        testflow.step(
            "Check that bridge_opts parameter %s have been updated "
            "to %s over BOND", self.querier_opts, self.non_default_bridge_opts
        )
        for key, value in self.bridge_opts_items:
            assert ll_networks.check_bridge_opts(
                vds_resource=conf.VDS_0_HOST, bridge_name=self.net_2,
                opts=key, value=value[1]
            )
        testflow.step(
            "Update bridge_opts %s with %s over BOND", self.querier_opts,
            self.default_bridge_opts
        )
        network_host_api_dict = {
            "update": {
                "1": {
                    "network": self.net_2,
                    "properties": {
                        "bridge_opts": self.default_bridge_opts
                    }
                }
            }
        }
        assert hl_host_network.setup_networks(
            host_name=conf.HOST_0_NAME, **network_host_api_dict
        )
        testflow.step(
            "Check that bridge_opts parameter %s have been updated "
            "to %s over BOND", self.querier_opts, self.default_bridge_opts
        )
        for key, value in self.bridge_opts_items:
            assert ll_networks.check_bridge_opts(
                vds_resource=conf.VDS_0_HOST, bridge_name=self.net_2,
                opts=key, value=value[0]
            )


@attr(tier=2)
@pytest.mark.usefixtures(setup_networks_fixture.__name__)
class TestNetworkCustomPropertiesCase04(NetworkTest):
    """
    Configure bridge_opts with non-default value for VLAN network over NIC
    Configure bridge_opts with non-default value for network over bond
    Verify bridge_opts were updated for both networks
    Detach both networks from Host
    Reattach both networks to the appropriate NIC and bond interfaces
    Verify bridge_opts have the default values when reattached (not updated
    values)
    """
    __test__ = True
    bond_1 = "bond40"
    priority_opts = custom_prop_conf.KEY1
    priority_value = custom_prop_conf.BRIDGE_OPTS.get(priority_opts)[1]
    priority_default = custom_prop_conf.DEFAULT_PRIORITY
    priority_default_value = custom_prop_conf.BRIDGE_OPTS.get(priority_opts)[0]
    net_1 = custom_prop_conf.NETS[4][0]
    net_2 = custom_prop_conf.NETS[4][1]
    properties_dict = {
        "bridge_opts": custom_prop_conf.PRIORITY
    }
    hosts_nets_nic_dict = {
        0: {
            net_1: {
                "nic": bond_1,
                "slaves": [2, 3],
                "network": net_1,
                "properties": properties_dict
            },
            net_2: {
                "nic": 1,
                "network": net_2,
                "properties": properties_dict
            }
        }
    }

    @polarion("RHEVM3-4183")
    def test_check_reattach_network(self):
        """
        1) Verify bridge_opts have updated values for both networks
        2) Detach networks from the Host
        3) Reattach networks to the Host again
        4) Verify bridge_opts have updated default value
        """
        testflow.step(
            "Check that bridge_opts parameter %s have been updated "
            "to %s", self.priority_opts, self.priority_value
        )
        for network in self.net_1, self.net_2:
            assert ll_networks.check_bridge_opts(
                vds_resource=conf.VDS_0_HOST, bridge_name=network,
                opts=self.priority_opts, value=self.priority_value
            )
        testflow.step(
            "Detach networks %s and %s from Host", self.net_1, self.net_2
        )
        assert hl_host_network.clean_host_interfaces(
            host_name=conf.HOST_0_NAME
        )
        testflow.step(
            "Reattach networks %s and %s to Host", self.net_1, self.net_2
        )
        network_host_api_dict = {
            "add": {
                "1": {
                    "slaves": conf.VDS_0_HOST.nics[2:4],
                    "network": self.net_1,
                    "nic": self.bond_1
                },
                "2": {
                    "network": self.net_2,
                    "nic": conf.VDS_0_HOST.nics[1]
                },

            }
        }
        assert hl_host_network.setup_networks(
            host_name=conf.HOST_0_NAME, **network_host_api_dict
        )
        testflow.step(
            "Check that bridge_opts %s has been updated to %s",
            self.priority_opts, self.priority_default
        )
        for network in self.net_1, self.net_2:
            assert ll_networks.check_bridge_opts(
                vds_resource=conf.VDS_0_HOST, bridge_name=network,
                opts=self.priority_opts, value=self.priority_default_value
            )


@attr(tier=2)
@pytest.mark.incremental
@pytest.mark.usefixtures(setup_networks_fixture.__name__)
class TestNetworkCustomPropertiesCase05(NetworkTest):
    """
    Configure ethtool with non-default value
    Verify ethtool_opts were updated
    Update ethtool_opts with default value
    Verify ethtool_opts were updated with the default value
    """
    __test__ = True
    ethtool_checksums = [custom_prop_conf.TX_CHECKSUM]
    net_1 = custom_prop_conf.NETS[5][0]
    net_2 = custom_prop_conf.NETS[5][1]
    properties_dict_1 = {
        "ethtool_opts": custom_prop_conf.TX_CHECKSUM.format(
            nic=1, state="off"
        )
    }
    properties_dict_2 = {
        "ethtool_opts": custom_prop_conf.TX_CHECKSUM.format(
            nic=2, state="off"
        )
    }
    hosts_nets_nic_dict = {
        0: {
            net_1: {
                "nic": 1,
                "network": net_1,
                "properties": properties_dict_1
            },
            net_2: {
                "nic": 2,
                "network": net_2,
                "properties": properties_dict_2
            }
        }
    }

    @polarion("RHEVM3-4187")
    def test_01_update_ethtool_opts(self):
        """
        1) Verify ethtool_opts have updated value for tx_checksum opts
        2) Update ethtool_opts with the default value
        3) Verify ethtool_opts have updated default value for tx_checksum opts
        """
        testflow.step(
            "Check that ethtool_opts parameter for tx_checksum have "
            "been updated to off"
        )
        assert ll_networks.check_ethtool_opts(
            vds_resource=conf.VDS_0_HOST, nic=conf.HOST_0_NICS[1],
            opts="tx-checksumming", value="off"
        )

        testflow.step(
            "Update ethtool_opts for tx_checksum with the default parameter"
        )
        network_host_api_dict = {
            "update": {
                "1": {
                    "network": self.net_1,
                    "properties": {
                        "ethtool_opts": custom_prop_conf.TX_CHECKSUM.format(
                            nic=conf.HOST_0_NICS[1], state="on"
                        )
                    }
                }
            }
        }
        assert hl_host_network.setup_networks(
            host_name=conf.HOST_0_NAME, **network_host_api_dict
        )
        testflow.step(
            "Check that ethtool_opts parameter has an updated default value"
        )
        assert ll_networks.check_ethtool_opts(
            vds_resource=conf.VDS_0_HOST, nic=conf.HOST_0_NICS[1],
            opts="tx-checksumming", value="on"
        )

    @polarion("RHEVM3-4188")
    def test_02_check_several_ethtool_opts_exist_nic_vlan(self):
        """
        1) Update ethtool_opts with additional parameter (rx checksum)
        2) Verify ethtool_opts have updated value for tx and rx checksum
        3) Update ethtool_opts with the default value for both keys
        4) Verify ethtool_opts have updated default value
        """
        default_ethtool_opts = " ".join(
            [
                custom_prop_conf.TX_CHECKSUM.format(
                    nic=conf.HOST_0_NICS[1], state="on"
                ), custom_prop_conf.RX_CHECKSUM.format(
                    nic=conf.HOST_0_NICS[1], state="on"
                )
            ]
        )
        non_default_ethtool_opts = " ".join(
            [
                custom_prop_conf.TX_CHECKSUM.format(
                    nic=conf.HOST_0_NICS[1], state="off"
                ), custom_prop_conf.RX_CHECKSUM.format(
                    nic=conf.HOST_0_NICS[1], state="off"
                )
            ]
        )
        testflow.step(
            "Update ethtool_opts with additional parameters"
        )
        network_host_api_dict = {
            "update": {
                "1": {
                    "network": self.net_1,
                    "properties": {
                        "ethtool_opts": non_default_ethtool_opts
                    }
                }
            }
        }
        assert hl_host_network.setup_networks(
            host_name=conf.HOST_0_NAME, **network_host_api_dict
        )
        testflow.step("Check that ethtool_opts parameter has an updated value")
        for prop in "rx-checksumming", "tx-checksumming":
            assert ll_networks.check_ethtool_opts(
                vds_resource=conf.VDS_0_HOST, nic=conf.HOST_0_NICS[1],
                opts=prop, value="off"
            )
        testflow.step(
            "Update ethtool_opts with the default parameters for both "
            "rx and tx checksum values"
        )
        network_host_api_dict = {
            "update": {
                "1": {
                    "network": self.net_1,
                    "properties": {
                        "ethtool_opts": default_ethtool_opts
                    }
                }
            }
        }
        assert hl_host_network.setup_networks(
            host_name=conf.HOST_0_NAME, **network_host_api_dict
        )
        testflow.step(
            "Check that ethtool_opts parameters have an updated default value"
            " for rx and tx checksum"
        )
        for prop in "rx-checksumming", "tx-checksumming":
            assert ll_networks.check_ethtool_opts(
                vds_resource=conf.VDS_0_HOST, nic=conf.HOST_0_NICS[1],
                opts=prop, value="on"
            )

    @polarion("RHEVM3-4188")
    def test_03_check_several_ethtool_opts_exist_nic_non_vm(self):
        """
        1) Update ethtool_opts with additional parameter (rx checksum)
        2) Verify ethtool_opts have updated value for tx and rx checksum
        3) Update ethtool_opts with the default value for both keys
        4) Verify ethtool_opts have updated default value
        """
        default_ethtool_opts = " ".join(
            [
                custom_prop_conf.TX_CHECKSUM.format(
                    nic=conf.HOST_0_NICS[2], state="on"
                ), custom_prop_conf.RX_CHECKSUM.format(
                    nic=conf.HOST_0_NICS[2], state="on"
                )
            ]
        )
        non_default_ethtool_opts = " ".join(
            [
                custom_prop_conf.TX_CHECKSUM.format(
                    nic=conf.HOST_0_NICS[2], state="off"
                ), custom_prop_conf.RX_CHECKSUM.format(
                    nic=conf.HOST_0_NICS[2], state="off"
                )
            ]
        )

        testflow.step(
            "Update ethtool_opts with additional parameters"
        )
        network_host_api_dict = {
            "update": {
                "1": {
                    "network": self.net_2,
                    "properties": {
                        "ethtool_opts": non_default_ethtool_opts
                    }
                }
            }
        }
        assert hl_host_network.setup_networks(
            host_name=conf.HOST_0_NAME, **network_host_api_dict
        )
        testflow.step(
            "Check that ethtool_opts parameter has an updated value "
        )
        for prop in "rx-checksumming", "tx-checksumming":
            assert ll_networks.check_ethtool_opts(
                vds_resource=conf.VDS_0_HOST, nic=conf.HOST_0_NICS[2],
                opts=prop, value="off"
            )
        testflow.step(
            "Update ethtool_opts with the default parameters for both "
            "rx and tx checksum values"
        )
        network_host_api_dict = {
            "update": {
                "1": {
                    "network": self.net_2,
                    "properties": {
                        "ethtool_opts": default_ethtool_opts
                    }
                }
            }
        }
        assert hl_host_network.setup_networks(
            host_name=conf.HOST_0_NAME, **network_host_api_dict
        )
        testflow.step(
            "Check that ethtool_opts parameters have an updated default value"
            " for rx and tx checksum"
        )
        for prop in "rx-checksumming", "tx-checksumming":
            assert ll_networks.check_ethtool_opts(
                vds_resource=conf.VDS_HOSTS[0], nic=conf.HOST_0_NICS[2],
                opts=prop, value="on"
            )

    @polarion("RHEVM3-4191")
    def test_04_reattach_network(self):
        """
        1) Detach the network from the Host NIC
        2) Verify ethtool_opts has non default value on the NIC
        3) Reattach network to the same NIC
        3) Verify ethtool_opts has non default value on the NIC
        """
        testflow.step("Remove network %s from the Host NIC", self.net_2)
        network_host_api_dict = {
            "remove": {
                "networks": [self.net_2],
            }
        }
        assert hl_host_network.setup_networks(
            host_name=conf.HOST_0_NAME, **network_host_api_dict
        )
        testflow.step(
            "Check that ethtool_opts parameter has an updated non-default "
            "value after removing network"
        )
        assert ll_networks.check_ethtool_opts(
            vds_resource=conf.VDS_0_HOST, nic=conf.HOST_0_NICS[2],
            opts="tx-checksumming", value="on"
        )
        testflow.step(
            "Reattach the network %s to the same Host NIC", self.net_2
        )
        network_host_api_dict = {
            "add": {
                "1": {
                    "network": self.net_2,
                    "nic": conf.HOST_0_NICS[2]
                }
            }
        }
        assert hl_host_network.setup_networks(
            host_name=conf.HOST_0_NAME, **network_host_api_dict
        )
        testflow.step(
            "Check that ethtool_opts parameter has non-default value after "
            "reattaching new network"
        )
        assert ll_networks.check_ethtool_opts(
            vds_resource=conf.VDS_0_HOST, nic=conf.HOST_0_NICS[2],
            opts="tx-checksumming", value="on"
        )


@attr(tier=2)
@pytest.mark.usefixtures(setup_networks_fixture.__name__)
class TestNetworkCustomPropertiesCase06(NetworkTest):
    """
    Configure ethtool and bridge opts with non-default value
    Verify ethtool and bridge_opts were updated with non-default values
    Update ethtool_and bridge opts with default value
    Verify ethtool and bridge_opts were updated with the default value
    """
    __test__ = True
    ethtool_checksums = [custom_prop_conf.TX_CHECKSUM]
    net_1 = custom_prop_conf.NETS[6][0]
    properties_dict = {
        "ethtool_opts": custom_prop_conf.TX_CHECKSUM.format(
            nic=1, state="off"
        ),
        "bridge_opts": custom_prop_conf.PRIORITY
    }
    hosts_nets_nic_dict = {
        0: {
            net_1: {
                "nic": 1,
                "network": net_1,
                "properties": properties_dict
            }
        }
    }

    @polarion("RHEVM3-4192")
    def test_update_ethtool_bridge_opts(self):
        """
        1) Verify ethtool_and bridge opts have updated values
        2) Update ethtool and bridge_opts with the default value
        3) Verify ethtool_and bridge opts have been updated with default values
        """
        testflow.step(
            "Check that ethtool_opts parameter for tx_checksum have an "
            "updated non-default value "
        )
        assert ll_networks.check_ethtool_opts(
            vds_resource=conf.VDS_0_HOST, nic=conf.HOST_0_NICS[1],
            opts="tx-checksumming", value="off"
        )

        testflow.step(
            "Check that bridge_opts parameter for priority have an updated "
            "non-default value "
        )
        assert ll_networks.check_bridge_opts(
            vds_resource=conf.VDS_0_HOST, bridge_name=self.net_1,
            opts=custom_prop_conf.KEY1,
            value=custom_prop_conf.BRIDGE_OPTS.get(custom_prop_conf.KEY1)[1]
        )

        testflow.step(
            "Update ethtool_opts for tx_checksum and bridge_opts for "
            "priority with the default parameters "
        )
        network_host_api_dict = {
            "update": {
                "1": {
                    "network": self.net_1,
                    "properties": {
                        "ethtool_opts": custom_prop_conf.TX_CHECKSUM.format(
                            nic=conf.HOST_0_NICS[1], state="on"
                        ),
                        "bridge_opts": custom_prop_conf.DEFAULT_PRIORITY
                    }
                }
            }
        }
        assert hl_host_network.setup_networks(
            host_name=conf.HOSTS[0], **network_host_api_dict
        )
        testflow.step(
            "Check that ethtool_opts parameter has an updated default value"
        )
        assert ll_networks.check_ethtool_opts(
            vds_resource=conf.VDS_0_HOST, nic=conf.HOST_0_NICS[1],
            opts="tx-checksumming", value="on"
        )
        testflow.step(
            "Check that bridge_opts parameter has an updated default value"
        )
        assert ll_networks.check_bridge_opts(
            vds_resource=conf.VDS_0_HOST, bridge_name=self.net_1,
            opts=custom_prop_conf.KEY1,
            value=custom_prop_conf.BRIDGE_OPTS.get(custom_prop_conf.KEY1)[0]
        )


@attr(tier=2)
@pytest.mark.usefixtures(setup_networks_fixture.__name__)
class TestNetworkCustomPropertiesCase07(NetworkTest):
    """
    Create a network without ethtool or bridge opts configured
    Configure ethtool and bridge opts with non-default value
    Verify ethtool and bridge_opts were updated with non-default values
    Update ethtool_and bridge opts with default value
    Verify ethtool and bridge_opts were updated with the default value
    """
    __test__ = True
    net_1 = custom_prop_conf.NETS[7][0]
    hosts_nets_nic_dict = {
        0: {
            net_1: {
                "nic": 1,
                "network": net_1,
            }
        }
    }

    @polarion("RHEVM3-4193")
    def test_update_bridge_ethtool_opts(self):
        """
        1) Update existing network with non-default values for bridge and
        ethtool opts
        2) Verify ethtool_and bridge opts have updated non-default values
        3) Update ethtool and bridge_opts with the default value
        4) Verify ethtool_and bridge opts have been updated with default values
        """
        testflow.step(
            "Update ethtool and bridge opts for tx_checksum and priority "
            "appropriately with the default parameters"
        )
        network_host_api_dict = {
            "update": {
                "1": {
                    "network": self.net_1,
                    "properties": {
                        "ethtool_opts": custom_prop_conf.TX_CHECKSUM.format(
                            nic=conf.HOST_0_NICS[1], state="off"
                        ),
                        "bridge_opts": custom_prop_conf.PRIORITY
                    }
                }
            }
        }
        assert hl_host_network.setup_networks(
            host_name=conf.HOST_0_NAME, **network_host_api_dict
        )

        testflow.step(
            "Check that ethtool_opts parameter for tx_checksum have an "
            "updated non-default value "
        )
        assert ll_networks.check_ethtool_opts(
            vds_resource=conf.VDS_0_HOST, nic=conf.HOST_0_NICS[1],
            opts="tx-checksumming", value="off"
        )
        testflow.step(
            "Check that bridge_opts parameter for priority  have an updated "
            "non-default value"
        )
        assert ll_networks.check_bridge_opts(
            vds_resource=conf.VDS_0_HOST, bridge_name=self.net_1,
            opts=custom_prop_conf.KEY1,
            value=custom_prop_conf.BRIDGE_OPTS.get(custom_prop_conf.KEY1)[1]
        )
        testflow.step(
            "Update ethtool and bridge opts for tx_checksum and priority "
            "appropriately with the default parameters"
        )
        network_host_api_dict = {
            "update": {
                "1": {
                    "network": self.net_1,
                    "properties": {
                        "ethtool_opts": custom_prop_conf.TX_CHECKSUM.format(
                            nic=conf.HOST_0_NICS[1], state="on"
                        ),
                        "bridge_opts": custom_prop_conf.DEFAULT_PRIORITY
                    }
                }
            }
        }
        assert hl_host_network.setup_networks(
            host_name=conf.HOSTS[0], **network_host_api_dict
        )
        testflow.step(
            "Check that ethtool_opts parameter has an updated default value"
        )
        assert ll_networks.check_ethtool_opts(
            vds_resource=conf.VDS_0_HOST, nic=conf.HOST_0_NICS[1],
            opts="tx-checksumming", value="on"
        )
        testflow.step(
            "Check that bridge_opts parameter has an updated default value"
        )
        assert ll_networks.check_bridge_opts(
            vds_resource=conf.VDS_0_HOST, bridge_name=self.net_1,
            opts=custom_prop_conf.KEY1,
            value=custom_prop_conf.BRIDGE_OPTS.get(custom_prop_conf.KEY1)[0]
        )


@attr(tier=2)
@pytest.mark.usefixtures(setup_networks_fixture.__name__)
class TestNetworkCustomPropertiesCase08(NetworkTest):
    """
    Configure several ethtool_opts  with non-default value for the NIC with
     attached Network (different key:value)
    Configure several bridge_opts with non-default value for the same network
     attached to the NIC (different key:value)
    Test on the Host that the ethtool values were updated correctly
    Test on the Host that bridge_opts values were updated correctly
    """
    __test__ = True
    net_1 = custom_prop_conf.NETS[7][0]
    hosts_nets_nic_dict = {
        0: {
            net_1: {
                "nic": 1,
                "network": net_1,
            }
        }
    }

    @polarion("RHEVM3-4194")
    def test_check_several_bridge_ethtool_opts_exist(self):
        """
        1) Configure several ethtool_opts  with non-default value for the
        NIC with attached Network (different key:value)
        2) Configure several bridge_opts with non-default value for the same
        network attached to the NIC (different key:value)
        3) Test on the Host that the ethtool values were updated correctly
        4) Test on the Host that bridge_opts values were updated correctly
        """
        host_nic = conf.HOST_0_NICS[1]
        default_ethtool_opts = " ".join(
            [
                custom_prop_conf.TX_CHECKSUM.format(nic=host_nic, state="on"),
                custom_prop_conf.RX_CHECKSUM.format(nic=host_nic, state="on")
            ]
        )
        non_default_ethtool_opts = " ".join(
            [
                custom_prop_conf.TX_CHECKSUM.format(nic=host_nic, state="off"),
                custom_prop_conf.RX_CHECKSUM.format(nic=host_nic, state="off")
            ]
        )
        default_bridge_opts = " ".join(
            [
                custom_prop_conf.DEFAULT_PRIORITY,
                custom_prop_conf.DEFAULT_MULT_QUERIER
            ]
        )
        non_default_bridge_opts = " ".join(
            [custom_prop_conf.PRIORITY, custom_prop_conf.MULT_QUERIER]
        )
        testflow.step(
            "Update ethtool_opts with non-default parameters for tx checksum "
            "and rx checksum and priority and querier of bridge opts"
        )
        network_host_api_dict = {
            "update": {
                "1": {
                    "network": self.net_1,
                    "properties": {
                        "ethtool_opts": non_default_ethtool_opts,
                        "bridge_opts": non_default_bridge_opts
                    }
                }
            }
        }
        assert hl_host_network.setup_networks(
            host_name=conf.HOSTS[0], **network_host_api_dict
        )
        testflow.step("Check that ethtool_opts parameter has an updated value")
        for prop in "rx-checksumming", "tx-checksumming":
            assert ll_networks.check_ethtool_opts(
                vds_resource=conf.VDS_0_HOST, nic=host_nic,
                opts=prop, value="off"
            )
        testflow.step("Check that bridge_opts parameter has an updated value ")
        for key, value in custom_prop_conf.BRIDGE_OPTS.iteritems():
            assert ll_networks.check_bridge_opts(
                vds_resource=conf.VDS_0_HOST, bridge_name=self.net_1,
                opts=key, value=value[1]
            )
        testflow.step(
            "Update ethtool_opts with default parameters for tx checksum and "
            "rx checksum and priority and querier of bridge opts"
        )
        network_host_api_dict = {
            "update": {
                "1": {
                    "network": self.net_1,
                    "properties": {
                        "ethtool_opts": default_ethtool_opts,
                        "bridge_opts": default_bridge_opts
                    }
                }
            }
        }
        assert hl_host_network.setup_networks(
            host_name=conf.HOSTS[0], **network_host_api_dict
        )
        testflow.step(
            "Check that ethtool_opts parameters have an updated default "
            "value for rx and tx checksum"
        )
        for prop in "tx-checksumming", "rx-checksumming":
            assert ll_networks.check_ethtool_opts(
                vds_resource=conf.VDS_0_HOST, nic=host_nic,
                opts=prop, value="on"
            )
        testflow.step(
            "Check that bridge_opts parameter has an updated default value"
        )
        for key, value in custom_prop_conf.BRIDGE_OPTS.items():
            assert ll_networks.check_bridge_opts(
                vds_resource=conf.VDS_0_HOST, bridge_name=self.net_1, opts=key,
                value=value[0]
            )


@attr(tier=2)
@pytest.mark.usefixtures(setup_networks_fixture.__name__)
class TestNetworkCustomPropertiesCase09(NetworkTest):
    """
    Create several ethtool and bridge opts while adding network to the Host
    Configure several ethtool_opts  with non-default value for the NIC with
     attached Network (different key:value)
    Configure several bridge_opts with non-default value for the same network
     attached to the NIC (different key:value)
    Test on the Host that the ethtool values were updated correctly
    Test on the Host that bridge_opts values were updated correctly
    """
    __test__ = True
    default_bridge_opts = " ".join(
        [
            custom_prop_conf.DEFAULT_PRIORITY,
            custom_prop_conf.DEFAULT_MULT_QUERIER
        ]
    )
    bridge_opts_properties = {"bridge_opts": default_bridge_opts}
    ethtool_checksums = " ".join(
        [
            custom_prop_conf.TX_CHECKSUM.format(
                nic=1, state="off"
            ),
            custom_prop_conf.RX_CHECKSUM.format(
                nic=1, state="off"
            )
        ]
    )
    net_1 = custom_prop_conf.NETS[9][0]
    net_nic_list = [(net_1, 1)]
    properties_dict = {
        "ethtool_opts": custom_prop_conf.TX_CHECKSUM.format(
            nic=1, state="on"
        ),
        "bridge_opts": default_bridge_opts
    }
    hosts_nets_nic_dict = {
        0: {
            net_1: {
                "nic": 1,
                "network": net_1,
                "properties": properties_dict
            }
        }
    }

    @polarion("RHEVM3-4195")
    def test_check_several_bridge_ethtool_opts_exist(self):
        """
        1) Update several ethtool_opts for the NIC with attached Network
        with additional parameter and non-default value (different key:value)
        2) Update several bridge_opts for Network, attached to the NIC with
        additional parameter and non-default value (different key:value)
        3) Test on the Host that the ethtool values were updated correctly
        for the ethtool_opts
        4) Test for the network on the the Host that the bridge values were
        updated correctlydefault_bridge_opts = " ".join(
            [conf.DEFAULT_PRIORITY, conf.DEFAULT_MULT_QUERIER]
        )
        5) Update  ethtool_opts with the default values for configured values.
        6) Update  bridge_opts with the default values for configured values.
        7) Test on the Host that the ethtool values were updated correctly
        8) Test for the network on the the Host that the bridge values were
        updated correctly
        """
        host_nic = conf.HOST_0_NICS[1]
        default_ethtool_opts = " ".join(
            [
                custom_prop_conf.TX_CHECKSUM.format(nic=host_nic, state="on"),
                custom_prop_conf.RX_CHECKSUM.format(nic=host_nic, state="on")
            ]
        )
        non_default_ethtool_opts = " ".join(
            [
                custom_prop_conf.TX_CHECKSUM.format(nic=host_nic, state="off"),
                custom_prop_conf.RX_CHECKSUM.format(nic=host_nic, state="off")
            ]
        )
        default_bridge_opts = " ".join(
            [
                custom_prop_conf.DEFAULT_PRIORITY,
                custom_prop_conf.DEFAULT_MULT_QUERIER
            ]
        )
        non_default_bridge_opts = " ".join(
            [custom_prop_conf.PRIORITY, custom_prop_conf.MULT_QUERIER]
        )
        testflow.step(
            "Update ethtool_opts with non-default parameters for tx, "
            "rx checksum and priority and querier of bridge opts"
        )
        network_host_api_dict = {
            "update": {
                "1": {
                    "network": self.net_1,
                    "properties": {
                        "ethtool_opts": non_default_ethtool_opts,
                        "bridge_opts": non_default_bridge_opts
                    }
                }
            }
        }
        assert hl_host_network.setup_networks(
            host_name=conf.HOST_0_NAME, **network_host_api_dict
        )
        testflow.step(
            "Check that ethtool_opts parameter has an updated value "
        )
        for prop in ("rx-checksumming", "tx-checksumming"):
            assert ll_networks.check_ethtool_opts(
                vds_resource=conf.VDS_0_HOST, nic=host_nic, opts=prop,
                value="off"
            )
        testflow.step(
            "Check that bridge_opts parameter has an updated value "
        )
        for key, value in custom_prop_conf.BRIDGE_OPTS.iteritems():
            assert ll_networks.check_bridge_opts(
                vds_resource=conf.VDS_0_HOST, bridge_name=self.net_1, opts=key,
                value=value[1]
            )
        testflow.step(
            "Update ethtool_opts with default parameters for tx, rx checksum "
            "and priority and querier of bridge opts"
        )
        network_host_api_dict = {
            "update": {
                "1": {
                    "network": self.net_1,
                    "properties": {
                        "ethtool_opts": default_ethtool_opts,
                        "bridge_opts": default_bridge_opts
                    }
                }
            }
        }
        assert hl_host_network.setup_networks(
            host_name=conf.HOST_0_NAME, **network_host_api_dict
        )
        testflow.step(
            "Check that ethtool_opts parameters have an updated default "
            "value for rx and tx checksum"
        )
        for prop in "rx-checksumming", "tx-checksumming":
            assert ll_networks.check_ethtool_opts(
                vds_resource=conf.VDS_0_HOST, nic=host_nic, opts=prop,
                value="on"
            )
        testflow.step(
            "Check that bridge_opts parameter has an updated default value"
        )
        for key, value in custom_prop_conf.BRIDGE_OPTS.items():
            assert ll_networks.check_bridge_opts(
                vds_resource=conf.VDS_0_HOST, bridge_name=self.net_1, opts=key,
                value=value[0]
            )


@attr(tier=2)
@pytest.mark.usefixtures(setup_networks_fixture.__name__)
class TestNetworkCustomPropertiesCase10(NetworkTest):
    """
    Configure ethtool with non-default value over bond
    Verify ethtool_opts were updated for each slave of the bond
    Update ethtool_opts with default value over bond
    Verify ethtool_opts were updated with the default value for each slave
    of the bond
    """
    __test__ = True
    bond = "bond100"
    net_1 = custom_prop_conf.NETS[10][0]
    hosts_nets_nic_dict = {
        0: {
            net_1: {
                "nic": bond,
                "network": net_1,
                "slaves": [2, 3]
            }
        }
    }

    @polarion("RHEVM3-4190")
    def test_update_ethtool_opts_bond(self):
        """
        1) Configure ethtool_opts tx_checksum value to be non-default on Bond
        1) Verify ethtool_opts have updated value for tx_checksum opts for
        each slave of the bond
        2) Update ethtool_opts with the default value for the bond
        3) Verify ethtool_opts have updated default value for tx_checksum
        opts for each slave of the bond
        """
        bond_nics = conf.HOST_0_NICS[2:4]
        eth_tool_off = ""
        eth_tool_on = ""
        for nic in bond_nics:
            val_off = custom_prop_conf.TX_CHECKSUM.format(nic=nic, state="off")
            eth_tool_off += "{val} ".format(val=val_off)
            val_on = custom_prop_conf.TX_CHECKSUM.format(nic=nic, state="on")
            eth_tool_on += "{val} ".format(val=val_on)

        testflow.step(
            "Update ethtool_opts for tx_checksum with the non-default "
            "parameter "
        )
        network_host_api_dict = {
            "update": {
                "1": {
                    "network": self.net_1,
                    "properties": {
                        "ethtool_opts": eth_tool_off
                    }
                }
            }
        }
        assert hl_host_network.setup_networks(
            host_name=conf.HOST_0_NAME, **network_host_api_dict
        )
        testflow.step(
            "Check that ethtool_opts parameter for tx_checksum have an "
            "updated non-default value for both slaves"
        )
        for interface in bond_nics:
            assert ll_networks.check_ethtool_opts(
                vds_resource=conf.VDS_0_HOST, nic=interface,
                opts="tx-checksumming", value="off"
            )
        testflow.step(
            "Update ethtool_opts for tx_checksum with the default parameter"
        )
        network_host_api_dict = {
            "update": {
                "1": {
                    "network": self.net_1,
                    "properties": {
                        "ethtool_opts": eth_tool_on
                    }
                }
            }
        }
        assert hl_host_network.setup_networks(
            host_name=conf.HOST_0_NAME, **network_host_api_dict
        )
        testflow.step(
            "Check that ethtool_opts parameter has an updated default "
            "value for both slaves of the bond "
        )
        for interface in bond_nics:
            assert ll_networks.check_ethtool_opts(
                vds_resource=conf.VDS_0_HOST, nic=interface,
                opts="tx-checksumming", value="on"
            )


@attr(tier=2)
@pytest.mark.usefixtures(setup_networks_fixture.__name__)
class TestNetworkCustomPropertiesCase11(NetworkTest):
    """
    Configure ethtool_opts with non-default value
    Verify ethtool_opts was updated
    Update the NIC with additional ethtool_opts value
    Verify ethtool_opts were updated with both values
    Update both values of ethtool_opts with the default values
    Verify ethtool_opts were updated accordingly
    """
    __test__ = True
    bond = "bond110"
    net_1 = custom_prop_conf.NETS[11][0]
    hosts_nets_nic_dict = {
        0: {
            net_1: {
                "nic": bond,
                "network": net_1,
                "slaves": [2, 3]
            }
        }
    }

    @polarion("RHEVM3-4189")
    def test_check_several_ethtool_opts_exist_bond(self):
        """
        1) Update ethtool_opts with non-default parameter (tx_checksum)
        2) Verify ethtool_opts have updated value for tx_checksum
        1) Update ethtool_opts with additional parameter (rx_checksum)
        2) Verify ethtool_opts have updated value for tx and rx checksum
        3) Update ethtool_opts with the default value for both keys
        4) Verify ethtool_opts have updated default value
        """
        bond_nics = conf.HOST_0_NICS[2:4]
        tx_checksum = custom_prop_conf.TX_CHECKSUM
        rx_checksum = custom_prop_conf.RX_CHECKSUM
        rx_eth_tool_off = ""
        rx_eth_tool_on = ""
        tx_eth_tool_off = ""
        tx_eth_tool_on = ""
        for nic in bond_nics:
            tx_val_off = tx_checksum.format(nic=nic, state="off")
            tx_val_on = tx_checksum.format(nic=nic, state="on")
            rx_val_off = rx_checksum.format(nic=nic, state="off")
            rx_val_on = rx_checksum.format(nic=nic, state="on")
            rx_eth_tool_off += "{val} ".format(val=tx_val_off)
            rx_eth_tool_on += "{val} ".format(val=tx_val_on)
            tx_eth_tool_off += "{val} ".format(val=rx_val_off)
            tx_eth_tool_on += "{val} ".format(val=rx_val_on)

        testflow.step(
            "Update ethtool_opts for tx_checksum with the non-default "
            "parameter"
        )
        network_host_api_dict = {
            "update": {
                "1": {
                    "network": self.net_1,
                    "properties": {
                        "ethtool_opts": rx_eth_tool_off
                    }
                }
            }
        }
        assert hl_host_network.setup_networks(
            host_name=conf.HOST_0_NAME, **network_host_api_dict
        )
        testflow.step(
            "Check that ethtool_opts parameter for tx_checksum have an "
            "updated non-default value for both slaves"
        )
        for interface in bond_nics:
            assert ll_networks.check_ethtool_opts(
                vds_resource=conf.VDS_0_HOST, nic=interface,
                opts="tx-checksumming", value="off"
            )

        testflow.step(
            "Update ethtool_opts with additional parameter for rx checksum"
        )

        network_host_api_dict = {
            "update": {
                "1": {
                    "network": self.net_1,
                    "properties": {
                        "ethtool_opts": tx_eth_tool_off
                    }
                }
            }
        }
        assert hl_host_network.setup_networks(
            host_name=conf.HOST_0_NAME, **network_host_api_dict
        )
        testflow.step(
            "Check that ethtool_opts parameter has an updated value "
            "for rx_checksum and tx_checksum for both slaves of the bond"
        )
        for prop in "rx-checksumming", "tx-checksumming":
            for interface in bond_nics:
                assert ll_networks.check_ethtool_opts(
                    vds_resource=conf.VDS_0_HOST, nic=interface, opts=prop,
                    value="off"
                )
        testflow.step(
            "Update ethtool_opts with the default parameters for both "
            "rx and tx checksum values for Bond "
        )

        network_host_api_dict = {
            "update": {
                "1": {
                    "network": self.net_1,
                    "properties": {
                        "ethtool_opts": "{rx} {tx}".format(
                            rx=rx_eth_tool_on, tx=tx_eth_tool_on
                        )
                    }
                }
            }
        }
        assert hl_host_network.setup_networks(
            host_name=conf.HOST_0_NAME, **network_host_api_dict
        )
        testflow.step(
            "Check that ethtool_opts parameters have an updated default value "
            "for rx and tx checksum"
        )
        for prop in "rx-checksumming", "tx-checksumming":
            for interface in bond_nics:
                assert ll_networks.check_ethtool_opts(
                    vds_resource=conf.VDS_0_HOST, nic=interface, opts=prop,
                    value="on"
                )


@attr(tier=2)
@pytest.mark.usefixtures(setup_networks_fixture.__name__)
class TestNetworkCustomPropertiesCase12(NetworkTest):
    """
    Configure ethtool and bridge opts with non-default value over Bond
    Verify ethtool and bridge_opts were updated with non-default values
    Update ethtool_and bridge opts with default value over Bond
    Verify ethtool and bridge_opts were updated with the default value
    """
    __test__ = True
    bridge_opts_properties = {"bridge_opts": custom_prop_conf.PRIORITY}
    ethtool_properties = {"ethtool_opts": "off"}
    ethtool_checksums = [custom_prop_conf.TX_CHECKSUM]
    bond = "bond110"
    net_1 = custom_prop_conf.NETS[11][0]
    properties_dict = {
        "ethtool_opts": custom_prop_conf.TX_CHECKSUM.format(
            nic="*", state="off"
        ),
        "bridge_opts": custom_prop_conf.PRIORITY
    }
    hosts_nets_nic_dict = {
        0: {
            net_1: {
                "nic": bond,
                "network": net_1,
                "slaves": [2, 3],
                "properties": properties_dict
            }
        }
    }

    @polarion("RHEVM3-4196")
    def test_update_ethtool_bridge_opts_bond(self):
        """
        1) Verify ethtool_and bridge opts have updated values over Bond
        2) Update ethtool and bridge_opts with the default value over Bond
        3) Verify ethtool_and bridge opts have been updated with default values
        """
        bond_nics = conf.HOST_0_NICS[2:4]
        testflow.step(
            "Check that ethtool_opts parameter for tx_checksum have an "
            "updated non-default value for every slave of the Bond"
        )
        for interface in bond_nics:
            assert ll_networks.check_ethtool_opts(
                vds_resource=conf.VDS_0_HOST, nic=interface,
                opts="tx-checksumming", value="off"
            )
        testflow.step(
            "Check that bridge_opts parameter for priority  have an updated "
            "non-default value "
        )
        assert ll_networks.check_bridge_opts(
            vds_resource=conf.VDS_0_HOST, bridge_name=self.net_1,
            opts=custom_prop_conf.KEY1,
            value=custom_prop_conf.BRIDGE_OPTS.get(custom_prop_conf.KEY1)[1]
        )
        testflow.step(
            "Update ethtool_opts for tx_checksum and bridge_opts for "
            "priority with the default parameters ")

        network_host_api_dict = {
            "update": {
                "1": {
                    "network": self.net_1,
                    "properties": {
                        "ethtool_opts": custom_prop_conf.TX_CHECKSUM.format(
                            nic="*", state="on"
                        ),
                        "bridge_opts": custom_prop_conf.DEFAULT_PRIORITY
                    }
                }
            }
        }
        assert hl_host_network.setup_networks(
            host_name=conf.HOST_0_NAME, **network_host_api_dict
        )
        testflow.step(
            "Check that ethtool_opts parameter has an updated default value "
            "for both slaves of the Bond"
        )
        for interface in bond_nics:
            assert ll_networks.check_ethtool_opts(
                vds_resource=conf.VDS_0_HOST, nic=interface,
                opts="tx-checksumming", value="on"
            )

        testflow.step(
            "Check that bridge_opts parameter has an updated default value"
        )
        assert ll_networks.check_bridge_opts(
            vds_resource=conf.VDS_0_HOST, bridge_name=self.net_1,
            opts=custom_prop_conf.KEY1,
            value=custom_prop_conf.BRIDGE_OPTS.get(custom_prop_conf.KEY1)[0]
        )
