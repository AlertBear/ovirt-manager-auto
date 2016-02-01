#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Testing Jumbo frames feature.
1 DC, 1 Cluster, 2 Hosts and 2 VMs will be created for testing.
jumbo frames will be tested for untagged, tagged, bond scenarios.
It will cover scenarios for VM/non-VM networks.
"""

import helper
import logging
from art.unittest_lib import attr
from rhevmtests.networking import config
import rhevmtests.helpers as global_helper
from art.test_handler.tools import polarion  # pylint: disable=E0611
import art.rhevm_api.utils.test_utils as utils
from art.unittest_lib import NetworkTest as TestCase
import rhevmtests.networking.helper as network_helper
from art.test_handler.exceptions import NetworkException
import art.rhevm_api.tests_lib.low_level.hosts as ll_hosts
import art.rhevm_api.tests_lib.high_level.host_network as hl_host_network
import art.rhevm_api.tests_lib.high_level.networks as hl_networks

HOST_API = utils.get_api("host", "hosts")
VM_API = utils.get_api("vm", "vms")
HOST_NICS0 = None  # filled in setup module
HOST_NICS1 = None  # filled in setup module
HOST_NAME0 = None  # Fill in setup_module
HOST_NAME1 = None  # Fill in setup_module

logger = logging.getLogger("Jumbo_Frames_Cases")

########################################################################
#                             Test Cases                               #
########################################################################


def setup_module():
    """
    obtain host NICs for the first Network Host
    """
    global HOST_NICS0, HOST_NICS1, HOST_NAME0, HOST_NAME1
    HOST_NICS0 = config.VDS_HOSTS[0].nics
    HOST_NICS1 = config.VDS_HOSTS[1].nics
    HOST_NAME0 = ll_hosts.get_host_name_from_engine(config.VDS_HOSTS[0].ip)
    HOST_NAME1 = ll_hosts.get_host_name_from_engine(config.VDS_HOSTS[1].ip)


class TestJumboFramesTestCaseBase(TestCase):
    """
    base class which provides teardown class method for each test case
    """

    @classmethod
    def teardown_class(cls):
        """
        Remove networks from the setup and update MTU to be default on all
        Hosts NICs
        """
        logger.info("Starting the teardown_class")
        logger.info("Updating MTU to default on all Hosts NICs")
        for host in config.VDS_HOSTS[:2]:
            for nic in host.nics:
                if not utils.configure_temp_mtu(
                    vds_resource=host, mtu=str(config.MTU[3]), nic=nic
                ):
                    logger.error(
                        "Unable to configure host's %s %s with MTU %s",
                        host.ip, nic, config.MTU[3]
                    )
        logger.info("Removing all networks from setup")
        if not hl_networks.remove_net_from_setup(
            host=config.HOSTS[:2], data_center=config.DC_NAME[0], all_net=True,
            mgmt_network=config.MGMT_BRIDGE
        ):
            logger.error("Cannot remove all networks from setup")


@attr(tier=2)
class TestJumboFramesCase01(TestJumboFramesTestCaseBase):
    """
    Test the bridged VM network with MTU 5000
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Create logical vm network with MTU 5000 on DC/Cluster/Hosts
        """
        local_dict = {
            config.NETWORKS[0]: {
                "mtu": config.MTU[1],
                "nic": 1,
                "required": "false"
            }
        }
        logger.info("Sending SN request to %s", HOST_NAME0)
        if not hl_networks.createAndAttachNetworkSN(
            data_center=config.DC_NAME[0], cluster=config.CLUSTER_NAME[0],
            host=config.VDS_HOSTS[0], network_dict=local_dict, auto_nics=[0]
        ):
            raise NetworkException(
                "Cannot create and attach network %s" % config.NETWORKS[0]
            )

    @polarion("RHEVM3-3718")
    def test_check_mtu(self):
        """
        Check physical and logical levels for network sw1 with Jumbo frames
        """
        # Checking physical and logical
        helper.check_logical_physical_layer(
            nic=HOST_NICS0[1], network=config.NETWORKS[0], mtu=config.MTU[1]
        )


@attr(tier=2)
class TestJumboFramesCase02(TestJumboFramesTestCaseBase):
    """
    Positive: 1) Creates 2 Non_VM networks with Jumbo Frames
              2) Checks the correct MTU values in the sys/config and
                 sys/class/net files
              3) Removes one of the networks
              4) Check the correct values for the MTU in files
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Create bridgeless tagged networks with MTU on DC/Cluster/Hosts
        """
        local_dict = {
            config.VLAN_NETWORKS[0]: {
                "vlan_id": config.VLAN_ID[0],
                "usages": "",
                "mtu": config.MTU[1],
                "nic": 1,
                "required": False},
            config.VLAN_NETWORKS[1]: {
                "vlan_id": config.VLAN_ID[1],
                "usages": "",
                "mtu": config.MTU[0],
                "nic": 1,
                "required": False
            }
        }
        logger.info("Sending SN request to %s", HOST_NAME0)
        if not hl_networks.createAndAttachNetworkSN(
            data_center=config.DC_NAME[0], cluster=config.CLUSTER_NAME[0],
            host=config.VDS_HOSTS[0], network_dict=local_dict,
            auto_nics=[0, 1]
        ):
            raise NetworkException("Cannot create and attach network")

    @polarion("RHEVM3-3721")
    def test_check_mtu_after_network_removal(self):
        """
        Check physical and logical levels for networks with Jumbo frames
        """
        # Checking logical
        helper.check_logical_physical_layer(
            nic=HOST_NICS0[1], network=config.VLAN_NETWORKS[0],
            mtu=config.MTU[1], vlan=config.VLAN_ID[0], bridge=False,
            physical=False
        )
        # Checking logical and physical
        helper.check_logical_physical_layer(
            nic=HOST_NICS0[1], network=config.VLAN_NETWORKS[1],
            mtu=config.MTU[0], vlan=config.VLAN_ID[1], bridge=False
        )

        logger.info(
            "Removing %s, Sending SN request to %s",
            config.VLAN_NETWORKS[0], HOST_NAME0)
        hl_host_network.remove_networks_from_host(
            host_name=HOST_NAME0, networks=[config.VLAN_NETWORKS[1]])
        # Checking logical and physical
        helper.check_logical_physical_layer(
            nic=HOST_NICS0[1], network=config.VLAN_NETWORKS[0],
            mtu=config.MTU[1], vlan=config.VLAN_ID[0], bridge=False
        )


@attr(tier=2)
class TestJumboFramesCase03(TestJumboFramesTestCaseBase):
    """
    Positive: Test BOND mode change
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Create bridged VLAN network with MTU on DC/Cluster/Host over bond
        """

        local_dict = {
            None: {
                "nic": config.BOND[0], "mode": "1",
                "slaves": [-2, -1]},
            config.VLAN_NETWORKS[0]: {
                "nic": config.BOND[0],
                "mtu": config.MTU[1],
                "vlan_id": config.VLAN_ID[0],
                "required": False
            }
        }
        logger.info("Sending SN request to %s", HOST_NAME0)
        if not hl_networks.createAndAttachNetworkSN(
            data_center=config.DC_NAME[0], cluster=config.CLUSTER_NAME[0],
            host=config.VDS_HOSTS[0], network_dict=local_dict,
            auto_nics=[0]
        ):
            raise NetworkException(
                "Cannot create and attach network %s" %
                config.VLAN_NETWORKS[0]
            )

    @polarion("RHEVM3-3713")
    def test_bond_mode_change(self):
        """
        Check physical and logical levels for networks with Jumbo frames
        """
        # Checking logical and physical
        helper.check_logical_physical_layer(
            network=config.VLAN_NETWORKS[0], mtu=config.MTU[1],
            bond=config.BOND[0], bond_nic1=HOST_NICS0[-2],
            bond_nic2=HOST_NICS0[-1]
        )
        logger.info("Changing the bond mode to mode4")

        local_dict = {
            config.VLAN_NETWORKS[0]: {
                "nic": config.BOND[0],
                "slaves": [-2, -1],
                "mode": "4",
                "required": "false",
            }
        }

        if not hl_networks.createAndAttachNetworkSN(
            host=config.VDS_HOSTS[0], network_dict=local_dict,
            auto_nics=[0]
        ):
            raise NetworkException()

        # Checking logical and physical
        helper.check_logical_physical_layer(
            network=config.VLAN_NETWORKS[0],
            mtu=config.MTU[1], bond=config.BOND[0], bond_nic1=HOST_NICS0[-2],
            bond_nic2=HOST_NICS0[-1]
        )


@attr(tier=2)
class TestJumboFramesCase04(TestJumboFramesTestCaseBase):
    """
    Positive: Creates 2 bridged VLAN network and check the network files.
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Create bridged VLAN networks with MTU on DC/Cluster/Host
        """
        local_dict = {
            config.VLAN_NETWORKS[0]: {
                "vlan_id": config.VLAN_ID[0],
                "mtu": config.MTU[1],
                "nic": 1,
                "required": False
            },
            config.VLAN_NETWORKS[1]: {
                "vlan_id": config.VLAN_ID[1],
                "mtu": config.MTU[0],
                "nic": 1,
                "required": False
            }
        }
        logger.info("Sending SN request to %s", HOST_NAME0)
        if not hl_networks.createAndAttachNetworkSN(
            data_center=config.DC_NAME[0], cluster=config.CLUSTER_NAME[0],
            host=config.VDS_HOSTS[0], network_dict=local_dict,
            auto_nics=[0, 1]
        ):
            raise NetworkException(
                "Cannot create and attach networks %s and %s " % (
                    config.VLAN_NETWORKS[0], config.VLAN_NETWORKS[1]
                )
            )

    @polarion("RHEVM3-3717")
    def test_check_mtu_values_in_files(self):
        """
        Check physical and logical levels for bridged VLAN networks
        """
        # Checking logical
        helper.check_logical_physical_layer(
            nic=HOST_NICS0[1], network=config.VLAN_NETWORKS[0],
            mtu=config.MTU[1], vlan=config.VLAN_ID[0], physical=False
        )
        # Checking logical and physical
        helper.check_logical_physical_layer(
            nic=HOST_NICS0[1], network=config.VLAN_NETWORKS[1],
            mtu=config.MTU[0], vlan=config.VLAN_ID[1]
        )


@attr(tier=2)
class TestJumboFramesCase05(TestJumboFramesTestCaseBase):
    """
    Positive: Creates bridged VLAN network over bond on host
              Checks that increasing bond size doesn't effect
              the parameters in ifcfg- and sys files
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Create bridged networks with MTU on DC/Cluster/Hosts over bond
        """
        local_dict = {
            None: {
                "nic": config.BOND[0],
                "mode": "1",
                "slaves": [-2, -1]},
            config.VLAN_NETWORKS[0]: {
                "nic": config.BOND[0],
                "mtu": config.MTU[1],
                "vlan_id": config.VLAN_ID[0],
                "required": False
            }
        }
        logger.info("Sending SN request to %s", HOST_NAME0)
        if not hl_networks.createAndAttachNetworkSN(
            data_center=config.DC_NAME[0], cluster=config.CLUSTER_NAME[0],
            host=config.VDS_HOSTS[0], network_dict=local_dict,
            auto_nics=[0]
        ):
            raise NetworkException(
                "Cannot create and attach network %s" % config.VLAN_NETWORKS[0]
            )

    @polarion("RHEVM3-3716")
    def test_increasing_bond_nics(self):
        """
        Check physical and logical levels for networks with Jumbo frames
        """
        # Checking logical and physical
        helper.check_logical_physical_layer(
            bond=config.BOND[0], network=config.VLAN_NETWORKS[0],
            mtu=config.MTU[1], bond_nic1=HOST_NICS0[-2],
            bond_nic2=HOST_NICS0[-1]
        )

        logger.info("Changing the bond to consist of 3 NICs")

        local_dict = {
            config.VLAN_NETWORKS[0]: {
                "nic": config.BOND[0],
                "slaves": [-3, -2, -1],
                "required": "false",
            },
        }

        if not hl_networks.createAndAttachNetworkSN(
            host=config.VDS_HOSTS[0], network_dict=local_dict,
            auto_nics=[0]
        ):
            raise NetworkException()

        # Checking logical and physical
        helper.check_logical_physical_layer(
            bond=config.BOND[0], network=config.VLAN_NETWORKS[0],
            mtu=config.MTU[1], bond_nic1=HOST_NICS0[-2],
            bond_nic2=HOST_NICS0[-1]
        )


@attr(tier=2)
class TestJumboFramesCase06(TestJumboFramesTestCaseBase):
    """
    Negative: 1. creates bond0 and attach VLAN network with MTU 9000 to it.
              2. attaches non_vm network with MTU 5000 to bond0.
    """
    __test__ = True

    @polarion("RHEVM3-3719")
    def test_neg_add_networks_with_different_mtu(self):
        """
        Trying to add two networks with different MTU to the
        same interface when one is vm network and the other
        is non_vm - should fail
        """
        local_dict = {
            None: {
                "nic": config.BOND[0], "mode": "1",
                "slaves": [2, 3]},
            config.VLAN_NETWORKS[0]: {
                "nic": config.BOND[0],
                "mtu": config.MTU[0],
                "vlan_id": config.VLAN_ID[0],
                "required": False},
            config.NETWORKS[0]: {
                "nic": config.BOND[0],
                "mtu": config.MTU[1],
                "usages": "",
                "required": False
            }
        }
        logger.info(
            "Negative: Trying to add two networks with different MTU to the "
            "same interface when one is vm network and the other is non_vm"
        )
        logger.info("Sending SN request to %s", HOST_NAME0)
        if hl_networks.createAndAttachNetworkSN(
            data_center=config.DC_NAME[0], cluster=config.CLUSTER_NAME[0],
            network_dict=local_dict, host=config.VDS_HOSTS[0], auto_nics=[0]

        ):
            raise NetworkException(
                "Adding two networks with different MTU when one is vm network"
                "and the other is non_vm was successful - Should have failed"
            )


@attr(tier=2, extra_reqs={'network_hosts': True})
class TestJumboFramesCase07(TestJumboFramesTestCaseBase):
    """
    Positive: Creates 2 bridged VLAN networks and check traffic between VMs
    over those networks
    """
    __test__ = True
    ips = network_helper.create_random_ips(mask=24)

    @classmethod
    def setup_class(cls):
        """
        Create bridged networks with MTU on DC/Cluster/Hosts
        """
        local_dict = {
            config.VLAN_NETWORKS[0]: {
                "vlan_id": config.VLAN_ID[0],
                "mtu": config.MTU[1],
                "nic": 1,
                "required": False},
            config.VLAN_NETWORKS[1]: {
                "vlan_id": config.VLAN_ID[1],
                "mtu": config.MTU[0],
                "nic": 1,
                "required": False
            }
        }
        logger.info("Sending SN request to %s, %s", HOST_NAME0, HOST_NAME1)
        if not hl_networks.createAndAttachNetworkSN(
                data_center=config.DC_NAME[0], cluster=config.CLUSTER_NAME[0],
                host=config.VDS_HOSTS[:2], network_dict=local_dict,
                auto_nics=[0, 1]
        ):
            raise NetworkException(
                "Cannot create and attach networks %s and %s" % (
                    config.VLAN_NETWORKS[0], config.VLAN_NETWORKS[1]
                    )

                )
        # Adding vnics to vms
        helper.add_vnics_to_vms(ips=cls.ips, mtu=str(config.MTU[1]))

    @polarion("RHEVM3-3720")
    def test_check_traffic_on_vms(self):
        """
        Send ping between 2 VMs
        """
        vm_resource = global_helper.get_host_resource(
            ip=config.VM_IP_LIST[0], password=config.VMS_LINUX_PW
        )
        network_helper.send_icmp_sampler(
            host_resource=vm_resource, dst=self.ips[1],
            size=str(config.SEND_MTU[0])
        )
        logger.info(
            "Removing network %s from the hosts", config.VLAN_NETWORKS[1]
        )

        for host_name in HOST_NAME0, HOST_NAME1:
            hl_host_network.remove_networks_from_host(
                host_name=host_name, networks=[config.VLAN_NETWORKS[1]])

        vm_resource = global_helper.get_host_resource(
            ip=config.VM_IP_LIST[0], password=config.VMS_LINUX_PW
        )
        network_helper.send_icmp_sampler(
            host_resource=vm_resource, dst=self.ips[1],
            size=str(config.SEND_MTU[0])
        )
        for host in config.VDS_HOSTS[:2]:
            host_nics = eval("HOST_NICS%d" % config.VDS_HOSTS[:2].index(host))
            # Checking logical and physical
            helper.check_logical_physical_layer(
                nic=host_nics[1], network=config.VLAN_NETWORKS[0],
                mtu=config.MTU[1]
            )

    @classmethod
    def teardown_class(cls):
        """
        Remove networks from the setup
        """
        logger.info("Starting the teardown")
        # Removing vnics from vms
        helper.remove_vnics_from_vms()
        logger.info("Call TestJumboFramesTestCaseBase teardown")
        super(TestJumboFramesCase07, cls).teardown_class()


@attr(tier=2)
class TestJumboFramesCase08(TestJumboFramesTestCaseBase):
    """
    Positive: Creates bridged VLAN network over bond on Host with MTU
    5000, then, add another network with MTU 1500 and checking that
    MTU on NICs are configured correctly on the logical and physical layers.
    """
    # TODO: modify the test for RHEV 3.6 according to
    # https://bugzilla.redhat.com/show_bug.cgi?id=1193544

    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Create bridged VLAN network with MTU on DC/Cluster/Host over bond
        """
        local_dict = {
            None: {
                "nic": config.BOND[1], "mode": "1",
                "slaves": [2, 3]},
            config.VLAN_NETWORKS[0]: {
                "nic": config.BOND[1],
                "mtu": config.MTU[1],
                "vlan_id": config.VLAN_ID[0],
                "required": False
            }
        }
        logger.info("Sending SN request to %s", HOST_NAME0)
        if not hl_networks.createAndAttachNetworkSN(
            data_center=config.DC_NAME[0], cluster=config.CLUSTER_NAME[0],
            host=config.VDS_HOSTS[0], network_dict=local_dict,
            auto_nics=[0]
        ):
            raise NetworkException(
                "Cannot create and attach network %s" %
                config.VLAN_NETWORKS[0],
            )

    @polarion("RHEVM3-3716")
    def test_check_mtu_with_two_different_mtu_networks(self):
        """
        Check physical and logical levels for networks with Jumbo frames
        """
        # Checking logical and physical
        helper.check_logical_physical_layer(
            bond=config.BOND[1], network=config.VLAN_NETWORKS[0],
            mtu=config.MTU[1], bond_nic1=HOST_NICS0[2], bond_nic2=HOST_NICS0[3]
        )
        new_network = {
            config.VLAN_NETWORKS[1]: {
                "nic": config.BOND[1],
                "required": False,
                "vlan_id": config.VLAN_ID[1]
            }
        }

        logger.info(
            "Adding %s to DC, Cluster and Host", config.VLAN_NETWORKS[1]
        )
        config.VDS_HOSTS[0].nics.append(config.BOND[1])
        if not hl_networks.createAndAttachNetworkSN(
            data_center=config.DC_NAME[0], cluster=config.CLUSTER_NAME[0],
            host=config.VDS_HOSTS[0], network_dict=new_network,
            auto_nics=[0, -1], vlan_auto_nics={config.VLAN_ID[0]: -1}
        ):
            raise NetworkException(
                "Cannot create & add the following %s" % new_network
            )
        config.VDS_HOSTS[0].nics.pop(-1)

        # Checking logical and physical
        helper.check_logical_physical_layer(
            bond=config.BOND[1], network=config.VLAN_NETWORKS[0],
            mtu=config.MTU[1], bond_nic1=HOST_NICS0[2], bond_nic2=HOST_NICS0[3]
        )
        # Checking logical
        helper.check_logical_physical_layer(
            bond=config.BOND[1], network=config.VLAN_NETWORKS[1],
            mtu=config.MTU[3], physical=False
        )


@attr(tier=2)
class TestJumboFramesCase09(TestJumboFramesTestCaseBase):
    """
    In the host, changing eth1 MTU to 2000 (using linux command), then adding
    logical network without MTU on eth1, and finally, checking that eth1 MTU is
    changed to 1500
    """
    # TODO: modify the test for RHEV 3.6 according to
    # https://bugzilla.redhat.com/show_bug.cgi?id=1193544

    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        For the host, changing eth1"s MTU to 2000, then adding logical network
        without MTU on eth1, expected MTU is 1500
        """
        if not utils.configure_temp_mtu(
            vds_resource=config.VDS_HOSTS[0], mtu=str(config.MTU[2]),
            nic=HOST_NICS0[1]
        ):
            raise NetworkException(
                "Unable to configure host's %s NIC with MTU %s" % (
                    config.VDS_HOSTS[0].ip, config.MTU[2],
                )
            )
        local_dict = {
            config.VLAN_NETWORKS[0]: {
                "vlan_id": config.VLAN_ID[0],
                "nic": 1,
                "required": False
            }
        }
        logger.info("Sending SN request to %s", HOST_NAME0)
        if not hl_networks.createAndAttachNetworkSN(
            data_center=config.DC_NAME[0], cluster=config.CLUSTER_NAME[0],
            host=config.VDS_HOSTS[0], network_dict=local_dict,
            auto_nics=[0, 1]
        ):
            raise NetworkException(
                "Cannot create and attach network %s on host %s" % (
                    config.VLAN_NETWORKS[0], config.VDS_HOSTS[0].ip
                )
            )

    @polarion("RHEVM3-3734")
    def test_check_mtu_pre_configured(self):
        """
        checking that eth1"s MTU is changed to 1500
        """

        logger.info(
            "Checking if %s is configured correctly with MTU %s",
            HOST_NICS0[1], config.MTU[3]
        )
        if not utils.check_configured_mtu(
            vds_resource=config.VDS_HOSTS[0], mtu=str(config.MTU[3]),
            inter_or_net=HOST_NICS0[1]
        ):
            raise NetworkException(
                "Interface %s does not have MTU %s configured" % (
                    HOST_NICS0[1], config.MTU[3],
                )
            )


@attr(tier=2, extra_reqs={'network_hosts': True})
class TestJumboFramesCase10(TestJumboFramesTestCaseBase):
    """
    Attach a network with MTU 9000 to bond on two hosts, checking that
    mtu is configured correctly and checking traffic between the hosts with
    configured MTU.
    """
    __test__ = True
    ips = network_helper.create_random_ips(mask=24)

    @classmethod
    def setup_class(cls):
        """
        Adding a VLAN network sw162 with MTU 9000 to two hosts
        """
        local_dict = {
            None: {
                "nic": config.BOND[0], "mode": "1",
                "slaves": [2, 3]},
            config.VLAN_NETWORKS[0]: {
                "nic": config.BOND[0],
                "mtu": config.MTU[0],
                "bootproto": "static",
                "address": [cls.ips[0],
                            cls.ips[1]],
                "netmask": [config.NETMASK,
                            config.NETMASK],
                "gateway": [config.GATEWAY],
                "vlan_id": config.VLAN_ID[0],
                "required": False
            }
        }
        logger.info("Sending SN request to %s %s", HOST_NAME0, HOST_NAME1)
        if not hl_networks.createAndAttachNetworkSN(
            data_center=config.DC_NAME[0], cluster=config.CLUSTER_NAME[0],
            host=config.VDS_HOSTS[:2], network_dict=local_dict, auto_nics=[0]
        ):
            raise NetworkException(
                "Cannot create and attach network %s" % config.VLAN_NETWORKS[0]
            )

    @polarion("RHEVM3-3732")
    def test_check_configurations_and_traffic(self):
        """
        Checking configuration of the network on the first host, adding
        the network to the second host, finally, checking traffic between
        the two hosts.
        """
        # Checking logical and physical
        helper.check_logical_physical_layer(
            bond=config.BOND[0], network=config.VLAN_NETWORKS[0],
            mtu=config.MTU[0], bond_nic1=HOST_NICS0[2], bond_nic2=HOST_NICS0[3]
        )
        network_helper.send_icmp_sampler(
            host_resource=config.VDS_HOSTS[0], dst=self.ips[1],
            size=str(config.SEND_MTU[1])
        )


@attr(tier=2, extra_reqs={'network_hosts': True})
class TestJumboFramesCase11(TestJumboFramesTestCaseBase):
    """
    Positive: Checking connectivity between two VMs over bond with the
    MTU configured
    """
    __test__ = True
    ips = network_helper.create_random_ips(mask=24)

    @classmethod
    def setup_class(cls):
        """
        Create a network over bond with MTU 9000 over DC/Cluster/Hosts
        """
        local_dict = {
            None: {
                "nic": config.BOND[0], "mode": "1",
                "slaves": [2, 3]},
            config.VLAN_NETWORKS[0]: {
                "nic": config.BOND[0],
                "mtu": config.MTU[0],
                "vlan_id": config.VLAN_ID[0],
                "required": False
            }
        }
        logger.info("Sending SN request to %s %s", HOST_NAME0, HOST_NAME1)
        if not hl_networks.createAndAttachNetworkSN(
            data_center=config.DC_NAME[0],
            cluster=config.CLUSTER_NAME[0],
            host=config.VDS_HOSTS[:2],
            network_dict=local_dict,
            auto_nics=[0]
        ):
            raise NetworkException(
                "Cannot create and attach network %s" %
                config.VLAN_NETWORKS[0]
            )
        # Adding vnics to vms
        helper.add_vnics_to_vms(ips=cls.ips, mtu=str(config.MTU[0]))

    @polarion("RHEVM3-3722")
    def test_check_traffic_on_vm_over_bond(self):
        """
        Send ping with MTU 8500 between the two VMS
        """
        vm_resource = global_helper.get_host_resource(
            ip=config.VM_IP_LIST[0], password=config.VMS_LINUX_PW
        )
        network_helper.send_icmp_sampler(
            host_resource=vm_resource, dst=self.ips[1],
            size=str(config.SEND_MTU[1])
        )

    @classmethod
    def teardown_class(cls):
        """
        Remove networks from the setup
        """
        logger.info("Starting the teardown")
        # Removing vnics from vms
        helper.remove_vnics_from_vms()
        logger.info("Call TestJumboFramesTestCaseBase teardown")
        super(TestJumboFramesCase11, cls).teardown_class()


@attr(tier=2, extra_reqs={'network_hosts': True})
class TestJumboFramesCase12(TestJumboFramesTestCaseBase):
    """
    Adding multiple VLANs over bond, configuring different MTU
    on each VLAN, checking configuration directly on the host and checking
    connectivity between the hosts with the MTU configured
    """
    __test__ = True
    ips = network_helper.create_random_ips(mask=24)

    @classmethod
    def setup_class(cls):
        """
        Create networks over bond with different MTUs over DC/Cluster/Host
        Setting those networks on one host only
        """
        local_dict = {
            None: {
                "nic": config.BOND[0], "mode": "1",
                "slaves": [2, 3]},
            config.VLAN_NETWORKS[0]: {
                "nic": config.BOND[0],
                "mtu": config.MTU[1],
                "vlan_id": config.VLAN_ID[0],
                "required": False},
            config.VLAN_NETWORKS[1]: {
                "nic": config.BOND[0],
                "mtu": config.MTU[0],
                "bootproto": "static",
                "address": [cls.ips[0],
                            cls.ips[1]],
                "netmask": [config.NETMASK,
                            config.NETMASK],
                "vlan_id": config.VLAN_ID[1],
                "required": False},
            config.VLAN_NETWORKS[2]: {
                "nic": config.BOND[0],
                "mtu": config.MTU[2],
                "vlan_id": config.VLAN_ID[2],
                "required": False},
            config.VLAN_NETWORKS[3]: {
                "nic": config.BOND[0],
                "mtu": config.MTU[3],
                "vlan_id": config.VLAN_ID[3],
                "required": False
            }
        }
        logger.info("Sending SN request to %s %s", HOST_NAME0, HOST_NAME1)
        if not hl_networks.createAndAttachNetworkSN(
            data_center=config.DC_NAME[0], cluster=config.CLUSTER_NAME[0],
            host=config.VDS_HOSTS[:2], network_dict=local_dict,
            auto_nics=[0]
        ):
            raise NetworkException(
                "Cannot create and attach networks: %s, %s, %s, %s" % (
                    config.VLAN_NETWORKS[0], config.VLAN_NETWORKS[1],
                    config.VLAN_NETWORKS[2], config.VLAN_NETWORKS[3]
                )
            )

    @polarion("RHEVM3-3736")
    def test_check_traffic_on_hosts_when_there_are_many_networks(self):
        """
        Checking that the highest MTU is configured on eth2, eth3 and bond0.
        also, checking that connectivity with MTU 8500 succeed between the
        hosts.
        """
        list_check_networks = [HOST_NICS0[2], HOST_NICS0[3], config.BOND[0]]
        logger.info(
            "Checking that networks and interfaces are configured correctly"
        )

        for element in list_check_networks:
            logger.info(
                "Checking ifconfig for %s on the host %s",
                element, config.VDS_HOSTS[0].ip
            )
            if not utils.check_configured_mtu(
                vds_resource=config.VDS_HOSTS[0], mtu=str(config.MTU[0]),
                inter_or_net=element
            ):
                raise NetworkException(
                    "Interface %s on host %s does not have MTU %s configured"
                    % (element, config.VDS_HOSTS[0].ip, config.MTU[0])
                )

        # Checking physical
        helper.check_logical_physical_layer(
            mtu=config.MTU[0], bond=config.BOND[0],
            bond_nic1=HOST_NICS0[2], bond_nic2=HOST_NICS0[3], logical=False
        )
        network_helper.send_icmp_sampler(
            host_resource=config.VDS_HOSTS[0], dst=self.ips[1],
            size=str(config.SEND_MTU[1])
        )


@attr(tier=2, extra_reqs={'network_hosts': True})
class TestJumboFramesCase13(TestJumboFramesTestCaseBase):
    """
    Adding multiple VLANs over bond, configuring different MTU
    on each VLAN and checking connectivity between the VMs with
    the MTU configured
    """
    __test__ = True
    ips = network_helper.create_random_ips(mask=24)

    @classmethod
    def setup_class(cls):
        """
        Create networks over bond with different MTUs over DC/Cluster/Hosts
        """
        local_dict = {
            None: {
                "nic": config.BOND[0], "mode": "1",
                "slaves": [2, 3]},
            config.VLAN_NETWORKS[0]: {
                "nic": config.BOND[0],
                "mtu": config.MTU[0],
                "vlan_id": config.VLAN_ID[0],
                "required": False},
            config.VLAN_NETWORKS[1]: {
                "nic": config.BOND[0],
                "mtu": config.MTU[1],
                "vlan_id": config.VLAN_ID[1],
                "required": False
            }
        }
        logger.info("Sending SN request to %s %s", HOST_NAME0, HOST_NAME1)
        if not hl_networks.createAndAttachNetworkSN(
            data_center=config.DC_NAME[0], cluster=config.CLUSTER_NAME[0],
            host=config.VDS_HOSTS[:2], network_dict=local_dict, auto_nics=[0]
        ):
            raise NetworkException(
                "Cannot create and attach networks %s and %s" % (
                    config.VLAN_NETWORKS[0], config.VLAN_NETWORKS[1],
                )
            )
        # Adding vnics to vms
        helper.add_vnics_to_vms(ips=cls.ips, mtu=str(config.MTU[0]))
        helper.add_vnics_to_vms(
            ips=cls.ips, mtu=str(config.MTU[1]), nic_name=config.NIC_NAME[2],
            network=config.VLAN_NETWORKS[1], set_ip=False
        )

    @polarion("RHEVM3-3731")
    def test_check_traffic_on_vms_when_host_has_many_networks(self):
        """
        Send ping with MTU 8500 between the two VMs
        """
        vm_resource = global_helper.get_host_resource(
            ip=config.VM_IP_LIST[0], password=config.VMS_LINUX_PW
        )
        network_helper.send_icmp_sampler(
            host_resource=vm_resource, dst=self.ips[1],
            size=str(config.SEND_MTU[1])
        )

    @classmethod
    def teardown_class(cls):
        """
        Remove networks from the setup
        """
        logger.info("Starting the teardown")
        # Removing vnics from vms
        helper.remove_vnics_from_vms()
        helper.remove_vnics_from_vms(nic_name=config.NIC_NAME[2])
        logger.info("Call TestJumboFramesTestCaseBase teardown")
        super(TestJumboFramesCase13, cls).teardown_class()


@attr(tier=2, extra_reqs={'network_hosts': True})
class TestJumboFramesCase14(TestJumboFramesTestCaseBase):
    """
    Positive: Creates bridged VLAN network with 5000 MTU values
    and as display, Attaching the network to VMs and checking the traffic
    between them
    """
    __test__ = True
    ips = network_helper.create_random_ips(mask=24)

    @classmethod
    def setup_class(cls):
        """
        Create bridged networks with MTU on DC/Cluster/Hosts
        """

        local_dict = {
            config.VLAN_NETWORKS[0]: {
                "vlan_id": config.VLAN_ID[0],
                "mtu": config.MTU[1],
                "nic": 1,
                "cluster_usages": "display",
                "required": False
            }
        }
        logger.info("Sending SN request to %s %s", HOST_NAME0, HOST_NAME1)
        if not hl_networks.createAndAttachNetworkSN(
            data_center=config.DC_NAME[0], cluster=config.CLUSTER_NAME[0],
            host=config.VDS_HOSTS[:2], network_dict=local_dict,
            auto_nics=[0, 1]
        ):
            raise NetworkException(
                "Cannot create and attach network %s" % (
                    config.VLAN_NETWORKS[0],
                )
            )
        # Adding vnics to vms
        helper.add_vnics_to_vms(ips=cls.ips, mtu=str(config.MTU[1]))

    @polarion("RHEVM3-3724")
    def test_check_traffic_on_vm_when_network_is_display(self):
        """
        Send ping between 2 VMS
        """
        vm_resource = global_helper.get_host_resource(
            ip=config.VM_IP_LIST[0], password=config.VMS_LINUX_PW
        )
        network_helper.send_icmp_sampler(
            host_resource=vm_resource, dst=self.ips[1],
            size=str(config.SEND_MTU[0])
        )

    @classmethod
    def teardown_class(cls):
        """
        Remove networks from the setup
        """
        logger.info("Starting the teardown")
        # Removing vnics from vms
        helper.remove_vnics_from_vms()
        logger.info("Call TestJumboFramesTestCaseBase teardown")
        super(TestJumboFramesCase14, cls).teardown_class()
