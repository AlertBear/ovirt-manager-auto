#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Testing Network labels feature.
1 DC, 2 Clusters, 2 Hosts will be created for testing.
Network Labels feature will be tested for untagged, tagged,
bond scenarios and for VM and non-VM networks
"""

import pytest

import art.rhevm_api.tests_lib.high_level.host_network as hl_host_network
import art.rhevm_api.tests_lib.high_level.networks as hl_networks
import art.rhevm_api.tests_lib.low_level.hosts as ll_hosts
import art.rhevm_api.tests_lib.low_level.networks as ll_networks
import config as label_conf
import rhevmtests.networking.config as conf
import rhevmtests.networking.helper as network_helper
from art.core_api import apis_utils
from art.test_handler.tools import polarion
from art.unittest_lib import NetworkTest, testflow, attr
from fixtures import (
    add_label_nic_and_network, create_network_on_dc,
    move_host_to_another_cluster, create_datacenter,
    create_clusters_and_networks
)
from rhevmtests.networking.fixtures import (
    setup_networks_fixture, clean_host_interfaces, NetworkFixtures
)


@pytest.fixture(scope="module", autouse=True)
def labels_prepare_setup(request):
    """
    Prepare setup
    """
    labels = NetworkFixtures()

    def fin():
        """
        Remove networks from setup
        """
        network_helper.remove_networks_from_setup(
            hosts=[labels.host_0_name, labels.host_1_name]
        )
    request.addfinalizer(fin)

    network_helper.prepare_networks_on_setup(
        networks_dict=label_conf.NET_DICT, dc=labels.dc_0,
        cluster=labels.cluster_0
    )


@attr(tier=2)
@pytest.mark.incremental
@pytest.mark.usefixtures(
    setup_networks_fixture.__name__,
    add_label_nic_and_network.__name__
)
class TestNetLabels01(NetworkTest):

    """
    Check network label:
    1) Check that the label cannot be attached to the Bond when it is used by
        another Host NIC
    2) Check that the label can attach to several interface.
    3) check that the label can attach to several interface with several
        networks on label.
    """
    __test__ = True
    bond = "bond01"
    net_1 = label_conf.NETS[1][0]
    net_2 = label_conf.NETS[1][1]
    net_3 = label_conf.NETS[1][2]
    net_4 = label_conf.NETS[1][3]
    label_1 = label_conf.LABEL_NAME[1][0]
    label_2 = label_conf.LABEL_NAME[1][1]
    label_3 = label_conf.LABEL_NAME[1][2]
    hosts_nets_nic_dict = {
        0: {
            bond: {
                "nic": bond,
                "slaves": [-1, -2],
            }
        },
        1: {}
    }
    labels_list = [
        {
            "label": label_1,
            "host": 0,
            "networks": [net_1],
            "nic": 1
        }
    ]

    @polarion("RHEVM3-4104")
    def test_01_same_label_on_host(self):
        """
        1) Try to attach already attached label to bond and fail
        2) Remove label from interface
        3) Attach label to the bond and succeed
        """
        testflow.step(
            "Try to attach label %s to the bond %s when that label "
            "is already attached to the interface %s ",
            self.label_1, self.bond, conf.HOST_0_NICS[1]
        )
        label_dict = {
            self.label_1: {
                "host": conf.HOST_0_NAME,
                "nic": self.bond
            }
        }
        assert not ll_networks.add_label(**label_dict)
        testflow.step(
            "Remove label %s from the host NIC %s and then try to attach label"
            "to the Bond interface %s", self.label_1, conf.HOST_0_NICS[1],
            self.bond
        )
        sn_label_dict = {
            "remove": {
                "labels": [self.label_1]
            }
        }
        assert hl_host_network.setup_networks(
            host_name=conf.HOST_0_NAME, **sn_label_dict
        )
        label_dict = {
            self.label_1: {
                "host": conf.HOST_0_NAME,
                "nic": self.bond
            }
        }
        assert ll_networks.add_label(**label_dict)
        assert hl_host_network.check_network_on_nic(
            network=self.net_1, host=conf.HOST_0_NAME, nic=self.bond
        )
        sn_label_dict = {
            "remove": {
                "labels": [self.label_1]
            }
        }
        assert hl_host_network.setup_networks(
            host_name=conf.HOST_0_NAME, **sn_label_dict
        )

    @polarion("RHEVM3-4106")
    def test_02_label_several_interfaces(self):
        """
        1) Put label on host NIC of one host
        2) Put the same label on bond of the second Host
        3) Put label on the network
        4) Check network is attached to both Host (appropriate interfaces)
        5) Remove label from interface
        """
        testflow.step(
            "Attach label %s to bond %s on the first host %s,"
            "and attach the same label %s to host NIC %s "
            "on the second host %s and attach label %s on the network %s and "
            "check if network %s is attached to both Host ",
            self.label_2, self.bond, conf.HOST_0_NAME, self.label_2,
            conf.HOST_1_NICS[1], conf.HOST_1_NAME, self.label_2, self.net_2,
            self.net_2
        )
        label_dict = {
            self.label_2: {
                "networks": [self.net_2]
            }
        }
        label_dict_1 = {
            self.label_2: {
                "host": conf.HOST_0_NAME,
                "nic": self.bond,
            }
        }
        label_dict_2 = {
            self.label_2: {
                "host": conf.HOST_1_NAME,
                "nic": conf.HOST_1_NICS[1]
            }
        }
        assert ll_networks.add_label(**label_dict)
        assert ll_networks.add_label(**label_dict_1)
        assert ll_networks.add_label(**label_dict_2)
        for host, nic in zip(conf.HOSTS[:2], [self.bond, conf.HOST_1_NICS[1]]):
                assert hl_host_network.check_network_on_nic(
                    network=self.net_2, host=host, nic=nic
                )
        testflow.step(
            "Remove label %s from the bond %s on the first host %s and from"
            "host NIC %s on the second host %s", self.label_2, self.bond,
            conf.HOST_0_NAME, conf.HOST_1_NICS[1], conf.HOST_1_NAME
        )
        sn_label_dict = {
            "remove": {
                "labels": [self.label_2]
            }
        }
        for host in conf.HOSTS[:2]:
            assert hl_host_network.setup_networks(
                host_name=host, **sn_label_dict
            )

    @polarion("RHEVM3-4107")
    def test_03_label_several_networks(self):
        """
        1) Put label on bond of the one host
        2) Put label on host NIC of the second host
        """
        testflow.step(
            "Attach label %s to bond %s and host NIC %s on both Hosts "
            "appropriately and check that network %s and %s are attached to "
            "bond %s on host %s and to host NIC %s on host %s",
            self.label_3, self.bond, conf.HOST_1_NICS[1], self.net_3,
            self.net_4, self.bond, conf.HOST_0_NAME, conf.HOST_1_NICS[1],
            conf.HOST_1_NAME
        )
        label_dict = {
            self.label_3: {
                "networks": [self.net_3, self.net_4]
            }
        }
        label_dict_1 = {
            self.label_3: {
                "host": conf.HOST_0_NAME,
                "nic": self.bond
            }
        }
        label_dict_2 = {
            self.label_3: {
                "host": conf.HOST_1_NAME,
                "nic": conf.HOST_1_NICS[1]
            }
        }
        assert ll_networks.add_label(**label_dict)
        assert ll_networks.add_label(**label_dict_1)
        assert ll_networks.add_label(**label_dict_2)
        for host, nic in zip(conf.HOSTS[:2], [self.bond, conf.HOST_1_NICS[1]]):
            for net in [self.net_3, self.net_4]:
                assert hl_host_network.check_network_on_nic(
                    network=net, host=host, nic=nic
                )


@attr(tier=2)
@pytest.mark.incremental
@pytest.mark.usefixtures(
    setup_networks_fixture.__name__,
    add_label_nic_and_network.__name__
)
class TestNetLabels02(NetworkTest):

    """
    1) Check that you can remove network from Host NIC on 2 Hosts by
    un-labeling that Network.
    2) Check that you can break bond which has network attached to it by
    Un-Labeling
    """
    __test__ = True
    bond = "bond02"
    net_1 = label_conf.NETS[2][0]
    net_2 = label_conf.NETS[2][1]
    label_1 = label_conf.LABEL_NAME[2][0]
    label_2 = label_conf.LABEL_NAME[2][1]
    hosts_nets_nic_dict = {
        0: {
            bond: {
                "nic": bond,
                "slaves": [-1, -2],
            }
        },
        1: {
            bond: {
                "nic": bond,
                "slaves": [-1, -2],
            }
        }
    }
    label_dict_1 = {
        "label": label_1,
        "networks": [net_1]
    }
    label_dict_2 = {
        "label": label_2,
        "networks": [net_2]
    }
    label_dict_3 = {
        "label": label_1,
        "host": 0,
        "nic": 1
    }
    label_dict_4 = {
        "label": label_2,
        "host": 0,
        "nic": bond
        }
    label_dict_5 = {
        "label": label_1,
        "host": 1,
        "nic": 1
    }
    label_dict_6 = {
        "label": label_2,
        "host": 1,
        "nic": bond
    }
    labels_list = [
        label_dict_1, label_dict_2, label_dict_3, label_dict_4, label_dict_5,
        label_dict_6
    ]

    @polarion("RHEVM3-4127")
    def test_01_un_label_network(self):
        """
        1) Remove label from the network
        2) Make sure the network was detached from host NIC on both hosts
        """
        testflow.step(
            "Remove label %s from the network %s", self.label_1, self.net_1
        )
        assert ll_networks.remove_label(
            networks=[self.net_1], labels=[self.label_1]
        )
        for host in conf.HOSTS[:2]:
            testflow.step(
                "Check that the network %s is not attached to host %s",
                self.net_1, host
            )
            sample = apis_utils.TimeoutingSampler(
                timeout=conf.SAMPLER_TIMEOUT, sleep=1,
                func=hl_host_network.check_network_on_nic,
                network=self.net_1, host=host, nic=conf.HOST_0_NICS[1]
            )
            assert sample.waitForFuncStatus(result=False)

    @polarion("RHEVM3-4122")
    def test_02_break_labeled_bond(self):
        """
        1) Break bond on both Hosts
        2) Make sure that the bond slave interfaces don't have label configured
        """
        kwargs = {
            "remove": {
                'networks': [self.net_2],
                'bonds': [self.bond],
                'labels': [self.label_2]
            }
        }
        testflow.step(
            "Break bond on both hosts (%s, %s)",
            conf.HOST_0_NAME, conf.HOST_1_NAME
        )
        for host_name in conf.HOSTS[:2]:
            assert hl_host_network.setup_networks(host_name, **kwargs)

        testflow.step(
            "Check that the label %s doesn't appear on slaves of both Hosts",
            self.label_2
        )
        assert not ll_networks.get_label_objects(
            host_nic_dict={
                conf.HOST_0_NAME: [
                    conf.HOST_0_NICS[-1], conf.HOST_0_NICS[-2]
                ],
                conf.HOST_1_NAME: [
                    conf.HOST_1_NICS[-1], conf.HOST_1_NICS[-2]
                ]
            }
        )


@attr(tier=2)
@pytest.mark.usefixtures(
    clean_host_interfaces.__name__,
    add_label_nic_and_network.__name__
)
class TestNetLabels03(NetworkTest):
    """
    1) Negative case: Try to remove labeled network NET1 from labeled
    interface on the first NIC by setupNetworks
    2) Remove label from interface and make sure the network is detached
    from it
    3) Attach another network to the same interface with setupNetworks
    """
    __test__ = True

    net_1 = label_conf.NETS[3][0]
    net_2 = label_conf.NETS[3][1]
    label_1 = label_conf.LABEL_NAME[3][0]
    vlan_id_1 = label_conf.VLAN_IDS[5]
    labels_list = [
        {
            "label": label_1,
            "host": 0,
            "networks": [net_1],
            "nic": 1
        }
    ]
    hosts_nets_nic_dict = {
        0: {}
    }

    @polarion("RHEVM3-4130")
    def test_remove_label_host_NIC(self):
        """
       1) Negative case: Try to remove labeled network NET1 from labeled
       interface with setupNetworks
       2) Remove label from interface and make sure the network is detached
       from it
       3) Attach another network to the same interface with setupNetworks
       """
        testflow.step(
            "Try to remove labeled network %s from Host NIC %s with "
            "setupNetwork", self.net_1, conf.HOST_0_NAME
        )
        assert not hl_host_network.remove_networks_from_host(
            host_name=conf.HOST_0_NAME, networks=[self.net_1]
        )
        testflow.step(
            "Remove label %s from interface %s and make sure the network "
            "is detached from it", self.label_1, conf.HOST_0_NICS[1]
        )
        remove_label = {
            "remove": {
                "labels": [self.label_1]
            }
        }
        assert hl_host_network.setup_networks(
            host_name=conf.HOST_0_NAME, **remove_label
        )
        assert not hl_host_network.check_network_on_nic(
            network=self.net_1, host=conf.HOST_0_NAME, nic=conf.HOST_0_NICS[1]
        )
        local_dict2 = {
            self.net_2: {
                "vlan_id": self.vlan_id_1,
                "required": "false",
                "usages": ""
            }
        }
        network_host_api_dict = {
            "add": {
                "1": {
                    "network": self.net_2,
                    "nic":  conf.HOST_0_NICS[1],
                }
            }
        }
        testflow.step(
            "Attach another network %s to the same interface %s "
            "with setupNetworks and check that the network %s "
            "is attached to host %s", self.net_2, conf.HOST_0_NICS[1],
            self.net_2, conf.HOST_0_NAME
        )
        assert hl_networks.createAndAttachNetworkSN(
            data_center=conf.DC_0, cluster=conf.CL_0,
            network_dict=local_dict2
        )
        assert hl_host_network.setup_networks(
            host_name=conf.HOST_0_NAME, **network_host_api_dict
        )
        assert hl_host_network.check_network_on_nic(
            network=self.net_2, host=conf.HOST_0_NAME, nic=conf.HOST_0_NICS[1]
        )


@attr(tier=2)
@pytest.mark.usefixtures(
    clean_host_interfaces.__name__,
    create_network_on_dc.__name__
)
class TestNetLabels04(NetworkTest):

    """
    Check that the labeled network created in the DC level only will not be
    attached to the labeled Host NIC
    """
    __test__ = True

    net_1 = label_conf.NETS[4][0]
    label_1 = label_conf.LABEL_NAME[4][0]
    network_dict = {
        net_1: {
            "required": "false"
        }
    }
    hosts_nets_nic_dict = {
        0: {}
    }

    @polarion("RHEVM3-4113")
    def test_network_on_host(self):
        """
        1) Attach label to the network
        2) Attach label to Host Nic
        3) Check the network with the same label as host NIC is not attached to
        Host when it is not attached to the cluster
        """
        testflow.step(
            "Attach label %s to the network %s and to host NIC %s and check "
            "that the network %s with the same label as host NIC isn't "
            "attached to host %s when it is not attached to the cluster %s",
            self.label_1, self.net_1, conf.HOST_0_NICS[1], self.net_1,
            conf.HOST_0_NAME, conf.CL_0
        )
        label_dict = {
            self.label_1: {
                "networks": [self.net_1],
                "host": conf.HOST_0_NAME,
                "nic": conf.HOST_0_NICS[1]
            }
        }
        assert ll_networks.add_label(**label_dict)
        assert not hl_host_network.check_network_on_nic(
            network=self.net_1, host=conf.HOST_0_NAME, nic=conf.HOST_0_NICS[1]
        )


@attr(tier=2)
@pytest.mark.usefixtures(
    clean_host_interfaces.__name__,
    add_label_nic_and_network.__name__
)
class TestNetLabels05(NetworkTest):
    """
    1) Create bond from labeled interfaces when those labels are attached to
    the VLAN networks appropriately.
    2) Create bond from labeled interfaces when those labels are attached to
    the non-VM and VLAN networks appropriately.
    3) Create bond from labeled interfaces when those labels are attached to
    the VM non-VLAN  network and non-VM network appropriately and fail.
    4)Create bond from labeled interfaces when those labels are attached to two
    VM non-VLAN network appropriately and fail.
    """
    __test__ = True
    bond_1 = "bond051"
    bond_2 = "bond052"
    bond_3 = "bond053"
    bond_4 = "bond054"
    nets = label_conf.NETS[5][:8]
    net_1 = nets[0]
    net_2 = nets[1]
    net_3 = nets[2]
    net_4 = nets[3]
    net_5 = nets[4]
    net_6 = nets[5]
    net_7 = nets[6]
    net_8 = nets[7]
    labels = label_conf.LABEL_NAME[5][:8]
    label_1 = labels[0]
    label_2 = labels[1]
    label_3 = labels[2]
    label_4 = labels[3]
    label_5 = labels[4]
    label_6 = labels[5]
    label_7 = labels[6]
    label_8 = labels[7]
    label_dict_1 = {
        "label": label_1,
        "networks": [net_1]
    }
    label_dict_2 = {
        "label": label_2,
        "networks": [net_2]
    }
    label_dict_3 = {
        "label": label_3,
        "networks": [net_3]
    }
    label_dict_4 = {
        "label": label_4,
        "networks": [net_4]
    }
    label_dict_5 = {
        "label": label_5,
        "networks": [net_5]
    }
    label_dict_6 = {
        "label": label_6,
        "networks": [net_6]
    }
    label_dict_7 = {
        "label": label_7,
        "networks": [net_7]
    }
    label_dict_8 = {
        "label": label_8,
        "networks": [net_8]
    }
    label_dict_9 = {
        "label": label_1,
        "host": 0,
        "nic": -1
    }
    label_dict_10 = {
        "label": label_2,
        "host": 0,
        "nic": -2
    }
    label_dict_11 = {
        "label": label_3,
        "host": 0,
        "nic": -3
    }
    label_dict_12 = {
        "label": label_4,
        "host": 0,
        "nic": -4
    }
    label_dict_13 = {
        "label": label_5,
        "host": 0,
        "nic": -5
    }
    label_dict_14 = {
        "label": label_6,
        "host": 0,
        "nic": -6
    }
    label_dict_15 = {
        "label": label_7,
        "host": 0,
        "nic": -7
    }
    label_dict_16 = {
        "label": label_8,
        "host": 0,
        "nic": -8
    }
    labels_list = [
        label_dict_1, label_dict_2, label_dict_3, label_dict_4,
        label_dict_5, label_dict_6, label_dict_7, label_dict_8,
        label_dict_9, label_dict_10, label_dict_11, label_dict_12,
        label_dict_13, label_dict_14, label_dict_15, label_dict_16
    ]
    hosts_nets_nic_dict = {
        0: {}
    }

    @polarion("RHEVM3-4116")
    def test_01_create_bond(self):
        """
        1) Remove labels from two interfaces.
        2) Create bond from labeled interfaces
        3) Attach label networks to the bond.
        2) Check that both networks reside now on bond
        3) Check that label doesn't reside on slaves of the bond
        """
        sn_remove_labels = {
            "remove": {
                "labels": self.labels[:2]
            }
        }
        assert hl_host_network.setup_networks(
            host_name=conf.HOST_0_NAME, **sn_remove_labels
        )
        network_host_api_dict = {
            "add": {
                "1": {
                    "slaves": conf.HOST_0_NICS[-2:],
                    "nic": self.bond_1,
                }
            }
        }
        testflow.step(
            "Create bond %s from labeled interfaces when those labels (%s, %s)"
            " are attached to the VLAN networks (%s, %s) appropriately",
            self.bond_1, self.label_1, self.label_2, self.net_1, self.net_2
        )
        assert hl_host_network.setup_networks(
            host_name=conf.HOST_0_NAME, **network_host_api_dict
        )
        labels_dict = {
            self.label_1: {
                "host": conf.HOST_0_NAME,
                "nic": self.bond_1
            },
            self.label_2: {
                "host": conf.HOST_0_NAME,
                "nic": self.bond_1
            }
        }
        assert ll_networks.add_label(**labels_dict)
        for network in [self.net_1, self.net_2]:
            assert hl_host_network.check_network_on_nic(
                network=network, host=conf.HOST_0_NAME, nic=self.bond_1
            )

    @polarion("RHEVM3-4100")
    def test_02_create_bond_with_non_vm_and_vlan_network(self):
        """
        1) Remove labels from both interfaces
        2) Create bond from labeled interfaces
        3) Attach label networks to the bond.
        2) Check that both networks reside now on bond
        3) Check that label doesn't reside on slaves of the bond
        """
        sn_remove_labels = {
            "remove": {
                "labels": self.labels[2:4]
            }
        }
        assert hl_host_network.setup_networks(
            host_name=conf.HOST_0_NAME, **sn_remove_labels
        )
        network_host_api_dict = {
            "add": {
                "1": {
                    "slaves": conf.HOST_0_NICS[-4:-2],
                    "nic": self.bond_2,
                }
            }
        }
        testflow.step(
            "Create bond %s from labeled interfaces when those labels (%s, %s)"
            " are attached to the non-VM and VLAN networks (%s, %s) "
            "appropriately ",
            self.bond_2, self.label_3, self.label_4, self.net_3, self.net_4
        )
        assert hl_host_network.setup_networks(
            host_name=conf.HOST_0_NAME, **network_host_api_dict
        )

        labels_dict = {
            self.label_3: {
                "host": conf.HOST_0_NAME,
                "nic": self.bond_2
            },
            self.label_4: {
                "host": conf.HOST_0_NAME,
                "nic": self.bond_2
            }
        }
        assert ll_networks.add_label(**labels_dict)
        for network in [self.net_3, self.net_4]:
            assert hl_host_network.check_network_on_nic(
                network=network, host=conf.HOST_0_NAME, nic=self.bond_2
            )

    @polarion("RHEVM3-4102")
    def test_03_create_bond_with_vm_and_non_vm(self):
        """
        1) Un-label both interfaces
        2) Negative: Try to create bond from labeled interfaces
        3) Check that both networks reside on appropriate interfaces after
        failure in second step
        """
        sn_remove_labels = {
            "remove": {
                "labels": self.labels[4:6]
            }
        }
        assert hl_host_network.setup_networks(
            host_name=conf.HOST_0_NAME, **sn_remove_labels
        )
        network_host_api_dict = {
            "add": {
                "1": {
                    "slaves": conf.HOST_0_NICS[-6:-4],
                    "nic": self.bond_3,
                }
            }
        }
        testflow.step(
            "Create bond %s from labeled interfaces when those "
            "labels (%s, %s) are attached to the VM non-VLAN network %s "
            "and non-VM network %s. Add the label to the BOND "
            "and fail since VM and non-VM networks cannot be on "
            "the same interface",
            self.bond_3, self.label_5, self.label_6, self.net_5, self.net_6
        )
        assert hl_host_network.setup_networks(
            host_name=conf.HOST_0_NAME, **network_host_api_dict
        )
        labels_dict = {
            self.label_5: {
                "host": conf.HOST_0_NAME,
                "nic": self.bond_3
            },
            self.label_6: {
                "host": conf.HOST_0_NAME,
                "nic": self.bond_3
            }
        }
        assert not ll_networks.add_label(**labels_dict)
        assert hl_host_network.check_network_on_nic(
            network=self.net_5, host=conf.HOST_0_NAME, nic=self.bond_3
        )
        assert not hl_host_network.check_network_on_nic(
            network=self.net_6, host=conf.HOST_0_NAME, nic=self.bond_3
        )

    @polarion("RHEVM3-4101")
    def test_04_create_bond_with_two_vm_non_vlan(self):
        """
        1) Negative: Create bond from labeled interfaces
        """
        network_host_api_dict = {
            "add": {
                "1": {
                    "slaves": conf.HOST_0_NICS[-8:-6],
                    "nic": self.bond_4,
                }
            }
        }
        testflow.step(
            "Try to create bond %s from labeled interfaces when those "
            "labels (%s, %s) are attached to two VM non-VLAN network "
            "(%s, %s) appropriately and fail",
            self.bond_4, self.label_7, self.label_8, self.net_7, self.net_8
        )
        assert not hl_host_network.setup_networks(
            host_name=conf.HOST_0_NAME, **network_host_api_dict
        )


@attr(tier=2)
@pytest.mark.usefixtures(
    clean_host_interfaces.__name__,
    add_label_nic_and_network.__name__
)
class TestNetLabels06(NetworkTest):

    """
    1)Check that when a labeled network is detached from a cluster,
    the network will be removed from any labeled interface within that cluster.
    2) The same will happen when the network is removed from the DC
    """
    __test__ = True
    net_1 = label_conf.NETS[6][0]
    label_1 = label_conf.LABEL_NAME[6][0]
    cl_1 = conf.CL_0
    dc_1 = conf.DC_0
    hosts_nets_nic_dict = {
        0: {}
    }
    labels_list = [
        {
            "label": label_1,
            "host": 0,
            "networks": [net_1],
            "nic": 1
        }
    ]

    @polarion("RHEVM3-4129")
    def test_remove_net_from_cluster_dc(self):
        """
        1) Remove network from the Cluster
        2) Check that the network is not attached to the Host interface
        anymore and not attached to the Cluster
        3) Reassign network to the Cluster
        4) Check that the network is attached to the interface after
        reattaching it to the Cluster
        5) Remove network from the DC
        6) Check that network is not attached to Host NIC
        7) Check that network doesn't exist in DC
        """
        testflow.step(
            "Remove labeled network %s from cluster %s",
            self.net_1, self.cl_1
        )
        assert ll_networks.remove_network_from_cluster(
            positive=True, network=self.net_1, cluster=self.cl_1
        )
        testflow.step(
            "Check that the network %s is not attached to host NIC %s",
            self.net_1, conf.HOST_0_NICS[1]
        )
        assert not hl_host_network.check_network_on_nic(
            network=self.net_1, host=conf.HOST_0_NAME, nic=conf.HOST_0_NICS[1]
        )
        testflow.step(
            "Reassign network %s to the Cluster %s", self.net_1, self.cl_1
        )
        assert ll_networks.add_network_to_cluster(
            positive=True, network=self.net_1, cluster=self.cl_1,
            required=False
        )
        testflow.step(
            "Check that the network %s is attached to the interface after"
            "reattaching it to the Cluster %s", self.net_1, self.cl_1
        )
        sample = apis_utils.TimeoutingSampler(
            timeout=conf.SAMPLER_TIMEOUT, sleep=1,
            func=hl_host_network.check_network_on_nic,
            network=self.net_1, host=conf.HOST_0_NAME, nic=conf.HOST_0_NICS[1]
        )
        assert sample.waitForFuncStatus(result=True)
        testflow.step(
            "Remove network %s from the DC %s", self.net_1, self.dc_1
        )
        assert ll_networks.remove_network(
            positive=True, network=self.net_1, data_center=self.dc_1
        )
        testflow.step(
            "Check that network %s is not attached to host NIC %s",
            self.net_1, conf.HOST_0_NICS[1]
        )
        assert not hl_host_network.check_network_on_nic(
            network=self.net_1, host=conf.HOST_0_NAME, nic=conf.HOST_0_NICS[1]
        )


@attr(tier=2)
@pytest.mark.usefixtures(
    create_datacenter.__name__,
    create_clusters_and_networks.__name__,
    move_host_to_another_cluster.__name__,
    add_label_nic_and_network.__name__
)
@pytest.mark.skipif(conf.PPC_ARCH, reason=conf.PPC_SKIP_MESSAGE)
class TestNetLabels07(NetworkTest):
    """
    Check that after moving a Host with labeled interface between all the
    Cluster versions for the 3.6 DC, the network label feature is functioning
    as expected
    """
    __test__ = True

    labels = label_conf.LABEL_NAME[7][:4]
    dc_name2 = "new_DC_3_6_case07"
    comp_cl_names = [
        "Cluster_%s_case07" % conf.COMP_VERSION_4_0[i]
        for i in range(len(conf.COMP_VERSION_4_0) - 1)
    ]
    nets = label_conf.NETS[7][:4]
    vlan_id_list = label_conf.VLAN_IDS[9:11]
    sleep_timeout = 30
    label_dict_1 = {
        "label": labels[0],
        "host": 1,
        "nic": -4
    }
    label_dict_2 = {
        "label": labels[1],
        "host": 1,
        "nic": -3
    }
    label_dict_3 = {
        "label": labels[2],
        "host": 1,
        "nic": -2
    }
    label_dict_4 = {
        "label": labels[3],
        "host": 1,
        "nic": -1
    }
    labels_list = [label_dict_1, label_dict_2, label_dict_3, label_dict_4]

    @polarion("RHEVM3-4124")
    def test_move_host_supported_cl(self):
        """
        1) Attach label to the network .
        2) Check that the network is attached to the host NIC
        3) Remove label from the network
        4) Repeat the 2 steps above when moving from 3.6 cluster up
        to all support cluster
        """
        for cluster in self.comp_cl_names:
            testflow.step(
                "Move the host %s to cluster %s", conf.HOST_1_NAME, cluster
            )
            assert ll_hosts.updateHost(
                positive=True, host=conf.HOST_1_NAME, cluster=cluster
            )
            dummies = conf.HOST_1_NICS[-4:]
            for lb, net, dummy in zip(self.labels, self.nets, dummies):
                label_dict = {
                    lb: {
                        "networks": [net]
                    }
                }
                testflow.step(
                    "Attach label %s to the network %s", lb, net
                )
                assert ll_networks.add_label(**label_dict)
                testflow.step(
                    "Check that the network %s is attach to the host NIC %s",
                    net, dummy
                )
                sample = apis_utils.TimeoutingSampler(
                    timeout=conf.SAMPLER_TIMEOUT, sleep=1,
                    func=hl_host_network.check_network_on_nic,
                    network=net, host=conf.HOST_1_NAME, nic=dummy
                )
                assert sample.waitForFuncStatus(result=True)
                remove_label = {
                    "remove": {
                        "labels": [lb]
                    }
                }
                assert hl_host_network.setup_networks(
                    host_name=conf.HOST_1_NAME, **remove_label
                )
                assert sample.waitForFuncStatus(result=False)


@attr(tier=2)
@pytest.mark.usefixtures(add_label_nic_and_network.__name__)
class TestNetLabels08(NetworkTest):
    """
    Negative test cases:
    1) Check it is not possible to have 2 bridged networks on the same host
    interface
    2) Check it is not possible to have 2 bridgeless networks on the same
    host interface
    3) Check it is not possible to have bridged + bridgeless network on the
    same host interface
    """
    __test__ = True
    label_1 = label_conf.LABEL_NAME[8][0]
    label_2 = label_conf.LABEL_NAME[8][1]
    label_3 = label_conf.LABEL_NAME[8][2]
    net_1 = label_conf.NETS[8][0]
    net_2 = label_conf.NETS[8][1]
    net_3 = label_conf.NETS[8][2]
    net_4 = label_conf.NETS[8][3]
    net_5 = label_conf.NETS[8][4]
    net_6 = label_conf.NETS[8][5]
    label_dict_1 = {
        "label": label_1,
        "networks": [net_1, net_2]
    }
    label_dict_2 = {
        "label": label_2,
        "networks": [net_3, net_4]
    }
    label_dict_3 = {
        "label": label_3,
        "networks": [net_5, net_6]
    }
    labels_list = [label_dict_1, label_dict_2, label_dict_3]

    @polarion("RHEVM3-4121")
    def test_label_restrictioin(self):
        """
        1) Put label_1 on Host NIC of the Host
        2) Check that the networks net_1 and net_2 are not attached to the Host
        3) Replace label_1 with label_2 on Host NIC of the Host
        4) Check that the networks net_3 and net_4 are not attached to the Host
        5) Replace label_2 with label_3 on Host NIC of the Host
        6) Check that the networks net_5 and net_6 are not attached to the Host
        7) Replace label_3 with label_4 on Host NIC of the Host
        """
        for label, net1, net2 in (
            (self.label_1, self.net_1, self.net_2),
            (self.label_2, self.net_3, self.net_4),
            (self.label_3, self.net_5, self.net_6)
        ):
            testflow.step(
                "Try to attach label %s to host NIC %s and attach "
                "both networks (%s, %s) to the label %s and check if that "
                "networks are not attached to the host %s",
                label, conf.HOST_0_NICS[1], net1, net2, label, conf.HOST_0_NAME
            )
            label_dict = {
                label: {
                    "nic": conf.HOST_0_NICS[1],
                    "host": conf.HOST_0_NAME
                }
            }
            assert not ll_networks.add_label(**label_dict)
            remove_label = {
                "remove": {
                    "labels": [label]
                }
            }
            assert hl_host_network.setup_networks(
                host_name=conf.HOST_0_NAME, **remove_label
            )


@attr(tier=2)
@pytest.mark.usefixtures(add_label_nic_and_network.__name__)
class TestNetLabels09(NetworkTest):
    """
    1) Check that when adding a new labeled VM network to the system which
    has another VM network with the same label attached to the Host, will not
    attach the new network to the Host
    2) Check that when adding a new labeled non-VM network to the system which
    has another non-VM network with the same label attached to the Host, will
    not attach the new network to the Host
    """
    __test__ = True

    net_1 = label_conf.NETS[9][0]
    net_2 = label_conf.NETS[9][1]
    net_3 = label_conf.NETS[9][2]
    net_4 = label_conf.NETS[9][3]
    label_1 = label_conf.LABEL_NAME[9][0]
    label_2 = label_conf.LABEL_NAME[9][1]
    label_dict_1 = {
        "label": label_1,
        "host": 0,
        "nic": 1,
        "networks": [net_1]
    }
    label_dict_2 = {
        "label": label_2,
        "host": 0,
        "nic": 2,
        "networks": [net_2]
    }
    labels_list = [label_dict_1, label_dict_2]

    @polarion("RHEVM3-4117")
    def test_01_label_restriction_vm(self):
        """
        1) Put the same label on the net_3 VM network as on network net_1
        2) Check that the new VM network net_3 is not attached to the Host NIC
        3) Check that net_1 is still attached to the Host NIC
        """
        testflow.step(
            "Check that when adding a new labeled VM network %s to the system "
            "which has another VM network %s with the same label %s attached "
            "to the host %s, will not attach the new network %s to the host",
            self.net_3, self.net_1, self.label_1, conf.HOST_0_NAME, self.net_3
        )
        label_dict = {
            self.label_1: {
                "networks": [self.net_3],
                "host": conf.HOST_0_NAME,
                "nic": conf.HOST_0_NICS[1]
            }
        }
        assert not ll_networks.add_label(**label_dict)

    @polarion("RHEVM3-4118")
    def test_02_label_restriction_non_vm(self):
        """
        1) Attach the same label on the net_4 VM network as on network net_2
        2) Check that the new non-VM network net_4 is not attached to the Host
            NIC
        3) Check that net_2 is still attached to the Host NIC
        """
        testflow.step(
            "Check that when adding a new labeled non-VM network %s to "
            "the system which has another non-VM network %s with the "
            "same label %s attached to the host %s, will not attach "
            "the new network to the host", self.net_4, self.net_2,
            self.label_2, conf.HOST_0_NAME
        )
        label_dict = {
            self.label_2: {
                "networks": [self.net_4],
                "host": conf.HOST_0_NAME,
                "nic": conf.HOST_0_NICS[1]
            }
        }
        assert not ll_networks.add_label(**label_dict)
