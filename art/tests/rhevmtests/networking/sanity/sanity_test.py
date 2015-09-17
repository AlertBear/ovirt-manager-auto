"""
Testing Sanity for the network features.
Sanity will test untagged, tagged, bond scenarios.
It will cover scenarios for VM/non-VM networks.
"""

import helper
import logging
import config as conf
from art.unittest_lib import attr
from art.unittest_lib import NetworkTest
from art.test_handler.tools import polarion  # pylint: disable=E0611
import art.core_api.apis_utils as apis_utils
import art.test_handler.exceptions as exceptions
import art.rhevm_api.utils.test_utils as test_utils
import art.core_api.apis_exceptions as apis_exceptions
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import art.rhevm_api.tests_lib.low_level.hosts as ll_hosts
import rhevmtests.networking.network_qos.helper as nq_helper
import art.rhevm_api.tests_lib.low_level.networks as ll_networks
import art.rhevm_api.tests_lib.high_level.networks as hl_networks
import rhevmtests.networking.multiple_queue_nics.helper as mqn_helper
import art.rhevm_api.tests_lib.low_level.datacenters as ll_datacenters
import art.rhevm_api.tests_lib.high_level.host_network as hl_host_network

logger = logging.getLogger("Sanity_Cases")


@attr(tier=0)
class TestSanityCase01(NetworkTest):
    """
    Validate that management network is required by default
    """
    __test__ = True

    @polarion("RHEVM3-12267")
    def test_validate_mgmt(self):
        """
        Check that management is a required network
        """
        mgmt_net = ll_networks.get_management_network(conf.CLUSTER).get_name()
        logger.info(
            "Check that management network %s is required by default",
            mgmt_net
        )
        if not ll_networks.isNetworkRequired(
                network=mgmt_net, cluster=conf.CLUSTER
        ):
            raise conf.NET_EXCEPTION(
                "Management network %s is not required by default" % mgmt_net
            )


@attr(tier=0)
class TestSanityCase02(NetworkTest):
    """
    Attach network with static IP to host.
    Remove the network.
    """
    __test__ = True

    @polarion("RHEVM3-12244")
    def test_check_static_ip(self):
        """
        Attach vlan with static ip (1.1.1.1) to host
        """
        logger.info("Attach %s to the %s", conf.NET_2, conf.HOST_0)
        local_dict = {
            conf.NET_2: {
                "vlan_id": conf.VLAN_IDS[0],
                "nic": 1,
                "bootproto": "static",
                "address": ["1.1.1.1"],
                "netmask": ["255.255.255.0"]
            }
        }
        if not hl_networks.createAndAttachNetworkSN(
            host=conf.VDS_HOST_0, network_dict=local_dict, auto_nics=[0, 1]
        ):
            raise conf.NET_EXCEPTION(
                "Cannot attach %s to %s" % (conf.NET_2, conf.HOST_0)
            )

    @classmethod
    def teardown_class(cls):
        """
        Clean host interfaces
        """
        if not hl_host_network.clean_host_interfaces(conf.HOST_NAME_0):
            logger.error("Failed to clean host interfaces")


@attr(tier=0)
class TestSanityCase03(NetworkTest):
    """
    Check VM & non_VM networks
    Attach the networks to host
    Check the proper creation
    """
    __test__ = True

    @polarion("RHEVM3-12245")
    def test_check_networks_usages(self):
        """
        Check for vm network and non-vm network
        """
        logger.info("Check VM network %s", conf.NET_3)
        if not ll_networks.isVMNetwork(
            network=conf.NET_3, cluster=conf.CLUSTER
        ):
            raise conf.NET_EXCEPTION("%s is not VM Network" % conf.NET_3)

        logger.info("Check non-VM network %s", conf.NET_3_1)
        if ll_networks.isVMNetwork(
            network=conf.NET_3_1, cluster=conf.CLUSTER
        ):
            raise conf.NET_EXCEPTION(
                "%s is not NON_VM network" % conf.NET_3_1
            )


@attr(tier=0)
class TestSanityCase04(NetworkTest):
    """
    Attach network to host
    Create VNIC profile with port mirroring and attach it to VM
    Start VM
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Create VNIC profile with port mirroring and attach it to VM
        """
        logger.info("Attach %s to the host", conf.NET_4)
        local_dict = {
            conf.NET_4: {
                "vlan_id": conf.VLAN_IDS[3],
                "nic": 1,
            }
        }
        if not hl_networks.createAndAttachNetworkSN(
            host=conf.VDS_HOST_0, network_dict=local_dict, auto_nics=[0, 1]
        ):
            raise conf.NET_EXCEPTION(
                "Cannot attach %s to the host" % conf.NET_4
            )
        logger.info(
            "Create %s with %s network and port mirroring enabled",
            conf.VPROFILE_0, conf.NET_4
        )
        if not ll_networks.addVnicProfile(
            positive=True, name=conf.VPROFILE_0, cluster=conf.CLUSTER,
            network=conf.NET_4, port_mirroring=True
        ):
            raise conf.NET_EXCEPTION(
                "Failed to add %s profile for %s network" %
                (conf.VPROFILE_0, conf.NET_4)
            )
        helper.run_vm_on_host()

    @polarion("RHEVM3-12251")
    def test_attach_vnic_to_vm(self):
        """
        Attach vNIC to VM
        """
        logger.info("Add vNIC %s to %s", conf.NIC_1, conf.VM_0)
        if not ll_vms.addNic(
            positive=True, vm=conf.VM_0, name=conf.NIC_1, network=conf.NET_4
        ):
            raise conf.NET_EXCEPTION("Add %s failed" % conf.NIC_1)

    @classmethod
    def teardown_class(cls):
        """
        Remove vNIC and network from the setup
        Remove vNIC profile
        Stop VM
        """
        logger.info("Unplug NIC %s", conf.NIC_1)
        if not ll_vms.updateNic(
            positive=True, vm=conf.VM_0, nic=conf.NIC_1, plugged=False
        ):
            logger.error("Unplug %s failed", conf.NIC_1)

        if not ll_vms.removeNic(positive=True, vm=conf.VM_0, nic=conf.NIC_1):
            logger.error("Remove %s failed", conf.NIC_1)

        if not ll_networks.removeVnicProfile(
            positive=True, vnic_profile_name=conf.VPROFILE_0,
            network=conf.NET_4
        ):
            logger.error("Failed to remove %s profile", conf.VPROFILE_0)

        if not hl_host_network.clean_host_interfaces(conf.HOST_NAME_0):
            logger.error("Failed to clean host interfaces")

        helper.stop_vm()


@attr(tier=0)
class TestSanityCase05(NetworkTest):
    """
    1. Verify that the network is required
    2. Update network to be non-required
    3. Check that the network is non-required
    """
    __test__ = True

    @polarion("RHEVM3-12252")
    def test_check_required(self):
        """
        Verify that the network is required,
        update network to be not required and checking
        that the network is non-required
        """
        logger.info("Checking that Network % s is required", conf.NET_5)
        if not ll_networks.isNetworkRequired(
            network=conf.NET_5, cluster=conf.CLUSTER
        ):
            raise conf.NET_EXCEPTION(
                "Network %s is non-required, Should be required" % conf.NET_5
            )
        logger.info("Update %s to be non-required", conf.NET_5)
        if not ll_networks.updateClusterNetwork(
            positive=True, cluster=conf.CLUSTER, network=conf.NET_5,
            required=False
        ):
            raise conf.NET_EXCEPTION(
                "Update %s to non-required failed" % conf.NET_5
            )
        logger.info("Check that Network %s is non-required", conf.NET_5)
        if ll_networks.isNetworkRequired(
                network=conf.NET_5, cluster=conf.CLUSTER
        ):
            raise conf.NET_EXCEPTION(
                "Network %s is required, Should be non-required" % conf.NET_5
            )


@attr(tier=0)
class TestSanityCase06(NetworkTest):
    """
    Check Jumbo Frame - VLAN over Bond:
    Create and adding network (MTU 2000) to the host Bond, then check that
    MTU on the network is really 2000
    Finally, remove the network from the setup
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Create and adding network (MTU 2000) to the host Bond
        """
        logger.info(
            "Create %s and attach it to the host Bond", conf.NET_6)
        local_dict = {
            None: {
                "nic": conf.BOND[0],
                "mode": 1,
                "slaves": [2, 3]
            },
            conf.NET_6: {
                "nic": conf.BOND[0],
                "vlan_id": conf.VLAN_IDS[4]
            }
        }
        if not hl_networks.createAndAttachNetworkSN(
            host=conf.VDS_HOST_0, network_dict=local_dict, auto_nics=[0]
        ):
            raise exceptions.NetworkException(
                "Cannot create and attach network"
            )

    @polarion("RHEVM3-12255")
    def test_check_mtu(self):
        """
        Check that MTU on the network is really 2000
        """
        logger.info(
            "Check that %s was created with mtu = %s", conf.NET_6,
            conf.MTU[2]
        )
        if not test_utils.checkMTU(
            host=conf.HOSTS_IP[0], user=conf.HOSTS_USER,
            password=conf.HOSTS_PW, mtu=conf.MTU[2],
            physical_layer=False, network=conf.NET_6,
            nic=conf.BOND[0], vlan=conf.VLAN_IDS[4]
        ):
            raise conf.NET_EXCEPTION(
                "%s is not configured with mtu = %s" %
                (conf.NET_6, conf.MTU[2])
            )

    @classmethod
    def teardown_class(cls):
        """
        Remove network from the setup
        """
        logger.info("Clean %s interfaces", conf.HOST_NAME_0)
        if not hl_host_network.clean_host_interfaces(conf.HOST_NAME_0):
            logger.error(
                "Failed to clean %s interface" % conf.HOST_NAME_0
            )


@attr(tier=0)
class TestSanityCase07(NetworkTest):
    """
    Check that network filter is enabled for hot-plug NIC on VM
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Adding nic2 to VM
        Start VM
        """
        logger.info("Add %s to %s", conf.NIC_1, conf.VM_0)
        if not ll_vms.addNic(
            positive=True, vm=conf.VM_0, name=conf.NIC_1,
            interface=conf.NIC_TYPE_RTL8139, network=conf.MGMT_BRIDGE
        ):
            raise exceptions.NetworkException(
                "Failed to add NIC %s to %s" % (conf.NIC_1, conf.VM_0)
            )
        helper.run_vm_on_host()

    @polarion("RHEVM3-4329")
    def test_check_network_filter_on_nic(self):
        """
        Check that the new NIC has network filter
        """
        logger.info(
            "Check that Network Filter is enabled for %s via dumpxml",
            conf.NIC_1
        )
        if not ll_hosts.checkNetworkFilteringDumpxml(
            positive=True, host=conf.HOST_0_IP, user=conf.HOSTS_USER,
            passwd=conf.HOSTS_PW, vm=conf.VM_0, nics="2"
        ):
            raise exceptions.NetworkException(
                "Network Filter is disabled for %s via dumpxml" % conf.NIC_1
            )

    @classmethod
    def teardown_class(cls):
        """
        Un-plug and remove nic2 from VM
        Stop VM
        """
        helper.stop_vm()
        logger.info("Unplug %s", conf.NIC_1)
        if not ll_vms.updateNic(True, conf.VM_0, conf.NIC_1, plugged=False):
            logger.error("Failed to upplug %s from %s", conf.NIC_1, conf.VM_0)

        logger.info("Remove %s from %s", conf.NIC_1, conf.VM_0)
        if not ll_vms.removeNic(positive=True, vm=conf.VM_0, nic=conf.NIC_1):
            logger.error("Failed to remove %s", conf.NIC_1)


@attr(tier=0)
class TestSanityCase08(NetworkTest):
    """
    Check Linking:
    Attach 4 VLAN networks to host
    Create vNICs (with all permutations of plugged & linked)
    and attach them to the vm.
    Check that all the permutations of plugged & linked are correct
    Remove the vNICs and networks.
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Attach 4 VLAN networks to host
        Create vNICs (with all permutations of plugged & linked)
        and attach them to the vm.
        Start VM
        """
        logger.info("Create networks and attach them to the host")
        local_dict = {
            conf.NET_8: {
                "nic": 1,
                "vlan_id": conf.VLAN_IDS[5],
            },
            conf.NET_8_1: {
                "nic": 1,
                "vlan_id": conf.VLAN_IDS[6],
            },
            conf.NET_8_2: {
                "nic": 1,
                "vlan_id": conf.VLAN_IDS[7],
            },
            conf.NET_8_3: {
                "nic": 1,
                "vlan_id": conf.VLAN_IDS[8],
            }
        }

        if not hl_networks.createAndAttachNetworkSN(
            host=conf.VDS_HOST_0, network_dict=local_dict, auto_nics=[0, 1]
        ):
            raise exceptions.NetworkException(
                "Cannot create and attach networks"
            )

        logger.info("Create VNICs with different plugged/linked permutations")
        plug_link_param_list = [("true", "true"), ("true", "false"),
                                ("false", "true"), ("false", "false")]
        nets = [conf.NET_8, conf.NET_8_1, conf.NET_8_2, conf.NET_8_3]
        for nic, plug_link, net in zip(
            conf.NIC_NAME[1:], plug_link_param_list, nets
        ):
            if not ll_vms.addNic(
                True, conf.VM_0, name=nic, network=net,
                plugged=plug_link[0], linked=plug_link[1]
            ):
                raise exceptions.NetworkException(
                    "Cannot add nic %s to %s" % (nic, conf.VM_0)
                )
        helper.run_vm_on_host()

    @polarion("RHEVM3-12256")
    def test_check_combination_plugged_linked_values(self):
        """
        Check all permutation for the Plugged/Linked options on vNIC
        """
        logger.info(
            "Check Linked on %s, %s is True", conf.NIC_1, conf.NIC_NAME[3]
        )
        for nic_name in (conf.NIC_1, conf.NIC_NAME[3]):
            if not ll_vms.getVmNicLinked(conf.VM_0, nic=nic_name):
                raise conf.NET_EXCEPTION("%s is not linked" % nic_name)

        logger.info(
            "Check Plugged on %s, %s is True", conf.NIC_1, conf.NIC_NAME[2]
        )
        for nic_name in (conf.NIC_1, conf.NIC_NAME[2]):
            if not ll_vms.getVmNicPlugged(conf.VM_0, nic=nic_name):
                raise conf.NET_EXCEPTION("%s is not pluged" % nic_name)

        logger.info(
            "Check Linked on %s, %s is False", conf.NIC_NAME[2],
            conf.NIC_NAME[4]
        )
        for nic_name in (conf.NIC_NAME[2], conf.NIC_NAME[4]):
            if ll_vms.getVmNicLinked(conf.VM_0, nic=nic_name):
                raise conf.NET_EXCEPTION("%s is linked" % nic_name)

        logger.info(
            "Check Plugged on %s, %s is False", conf.NIC_NAME[3],
            conf.NIC_NAME[4]
        )
        for nic_name in (conf.NIC_NAME[3], conf.NIC_NAME[4]):
            if ll_vms.getVmNicPlugged(conf.VM_0, nic=nic_name):
                raise conf.NET_EXCEPTION("%s is pluged" % nic_name)

    @classmethod
    def teardown_class(cls):
        """
        Removing the vNICs and networks.
        Stop VM
        """
        helper.stop_vm()
        logger.info(
            "Update all the networks beside mgmt network to be unplugged"
        )
        for nic_name in (conf.NIC_1, conf.NIC_NAME[2]):
            if not ll_vms.updateNic(True, conf.VM_0, nic_name, plugged=False):
                logger.error("Couldn't unplug %s", nic_name)

        logger.info("Remove all the VNICs besides mgmt network")
        for nic in conf.NIC_NAME[1:5]:
            if not ll_vms.removeNic(True, conf.VM_0, nic):
                logger.error("Cannot remove %s from setup", nic)

        logger.info("Clean %s interfaces", conf.HOST_NAME_0)
        if not hl_host_network.clean_host_interfaces(conf.HOST_NAME_0):
            logger.error(
                "Failed to clean %s interface" % conf.HOST_NAME_0
            )


@attr(tier=0)
class TestSanityCase09(NetworkTest):
    """
    Negative: Try to create Bond with exceeded name length (more than 15 chars)
    """

    __test__ = True

    @polarion("RHEVM3-4340")
    def test_bond_max_length(self):
        """
        Create BOND: exceed allowed length (max 15 chars)
        """
        logger.info("Generate bond012345678901 object with 2 NIC")
        net_obj = []
        rc, out = ll_hosts.genSNNic(
            nic="bond012345678901", slaves=[
                conf.VDS_HOST_0.nics[2], conf.VDS_HOST_0.nics[3]
            ]
        )
        if not rc:
            raise exceptions.NetworkException("Cannot generate SNNIC object")

        net_obj.append(out["host_nic"])

        logger.info("send SNRequest for bond012345678901")
        if not ll_hosts.sendSNRequest(
            False, host=conf.HOST_NAME_0, nics=net_obj,
            auto_nics=[conf.VDS_HOST_0.nics[0]],
            check_connectivity="true", connectivity_timeout=conf.TIMEOUT,
            force="false"
        ):
            raise conf.NET_EXCEPTION(
                "Can create BOND with name length of > 15"
            )

    @polarion("RHEVM3-4340")
    def test_bond_prefix1(self):
        """
        Create BOND: use wrong prefix (eg. NET1515)
        """
        logger.info("Generate NET1515 object with 2 NIC bond")
        net_obj = []
        rc, out = ll_hosts.genSNNic(
            nic="NET1515", slaves=[
                conf.VDS_HOST_0.nics[2], conf.VDS_HOST_0.nics[3]
            ]
        )
        if not rc:
            raise exceptions.NetworkException("Cannot generate NIC object")

        net_obj.append(out["host_nic"])

        logger.info("send SNRequest: NET1515")
        if not ll_hosts.sendSNRequest(
            False, host=conf.HOST_NAME_0, nics=net_obj,
            auto_nics=[conf.VDS_HOST_0.nics[0]],
            check_connectivity="true", connectivity_timeout=conf.TIMEOUT,
            force="false"
        ):
            raise conf.NET_EXCEPTION(
                "Can create BOND with wrong prefix (eg. NET1515)"
            )

    @polarion("RHEVM3-4340")
    def test_bond_empty(self):
        """
        Create BOND: leave name field empty
        """
        logger.info("Generate bond object with 2 NIC bond and empty name")
        net_obj = []
        rc, out = ll_hosts.genSNNic(
            nic="", slaves=[conf.VDS_HOST_0.nics[2], conf.VDS_HOST_0.nics[3]]
        )
        if not rc:
            raise exceptions.NetworkException("Cannot generate NIC object")
        net_obj.append(out["host_nic"])

        logger.info("send SNRequest: empty bond name")
        if not ll_hosts.sendSNRequest(
            False, host=conf.HOST_NAME_0, nics=net_obj,
            auto_nics=[conf.VDS_HOST_0.nics[0]],
            check_connectivity="true", connectivity_timeout=conf.TIMEOUT,
            force="false"
        ):
            raise conf.NET_EXCEPTION("Can create BOND without name")

    @polarion("RHEVM3-4340")
    def test_bond_suffix2(self):
        """
        Create BOND: use wrong suffix (e.g. bond1!)
        """
        logger.info("Generate bond1! object with 2 NIC bond")
        net_obj = []
        rc, out = ll_hosts.genSNNic(
            nic="bond1!",  slaves=[
                conf.VDS_HOST_0.nics[2], conf.VDS_HOST_0.nics[3]
            ]
        )
        if not rc:
            raise exceptions.NetworkException("Cannot generate NIC object")

        net_obj.append(out["host_nic"])

        logger.info("send SNRequest: bond1!")
        if not ll_hosts.sendSNRequest(
            False, host=conf.HOST_NAME_0, nics=net_obj,
            auto_nics=[conf.VDS_HOST_0.nics[0]],
            check_connectivity="true", connectivity_timeout=conf.TIMEOUT,
            force="false"
        ):
            raise conf.NET_EXCEPTION(
                "Can create BOND with wrong suffix (e.g. bond1!)"
            )


@attr(tier=0)
class TestSanityCase10(NetworkTest):
    """
    Configure ethtool and bridge opts with non-default value
    Verify ethtool and bridge_opts were updated with non-default values
    Update ethtool_and bridge opts with default value
    Verify ethtool and bridge_opts were updated with the default value
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Create logical VM network on DC/Cluster/Host with ethtool_opts
        and bridge_opts having non-default values
        """
        prop_dict = {
            "ethtool_opts": conf.TX_CHECKSUM.format(
                nic=conf.HOST_NICS[1], state="off"
            ), "bridge_opts": conf.PRIORITY
        }
        local_dict = {
            conf.NET_10: {
                "nic": 1,
                "properties": prop_dict
            }
        }
        logger.info(
            "Create logical VM network %s on DC/Cluster/Host with ethtool_opts"
            " and bridge_opts having non-default values", conf.NET_10
        )
        if not hl_networks.createAndAttachNetworkSN(
            host=conf.VDS_HOST_0, network_dict=local_dict, auto_nics=[0]
        ):
            raise exceptions.NetworkException(
                "Cannot attach %s to %s" % (conf.NET_10, conf.HOST_0)
            )

    @polarion("RHEVM3-4337")
    def test_update_ethtool_bridge_opts(self):
        """
        1) Verify ethtool_and bridge opts have updated values
        2) Update ethtool and bridge_opts with the default value
        3) Verify ethtool_and bridge opts have been updated with default values
        """
        logger.info(
            "Check that ethtool_opts parameter for tx_checksum have an updated"
            " non-default value"
        )
        if not ll_networks.check_ethtool_opts(
            conf.HOSTS_IP[0], conf.HOSTS_USER, conf.HOSTS_PW,
            conf.HOST_NICS[1], "tx-checksumming", "off"
        ):
            raise exceptions.NetworkException(
                "tx-checksum value of ethtool_opts was not updated correctly "
                "with non-default value"
            )

        logger.info(
            "Check that bridge_opts parameter for priority have an updated "
            "non-default value"
        )
        if not ll_networks.check_bridge_opts(
            conf.HOSTS_IP[0], conf.HOSTS_USER, conf.HOSTS_PW,
            conf.NET_10, conf.KEY1, conf.BRIDGE_OPTS.get(conf.KEY1)[1]
        ):
            raise exceptions.NetworkException(
                "Priority value of bridge_opts was not updated correctly "
                "with non-default value"
            )

        logger.info(
            "Update ethtool_opts for tx_checksum and bridge_opts for priority "
            "with the default parameters"
        )
        kwargs = {
            "properties": {"ethtool_opts": conf.TX_CHECKSUM.format(
                nic=conf.HOST_NICS[1], state="on"
            ), "bridge_opts": conf.DEFAULT_PRIORITY}
        }
        if not hl_networks.update_network_host(
            conf.HOST_NAME_0, conf.HOST_NICS[1],
            auto_nics=[conf.HOST_NICS[0]], **kwargs
        ):
            raise exceptions.NetworkException(
                "Couldn't update ethtool and bridge_opts with default "
                "parameters for tx_checksum and priority opts"
            )

        logger.info(
            "Check that ethtool_opts parameter has an updated default value"
        )
        if not ll_networks.check_ethtool_opts(
            conf.HOSTS_IP[0], conf.HOSTS_USER, conf.HOSTS_PW,
            conf.HOST_NICS[1], "tx-checksumming", "on"
        ):
            raise exceptions.NetworkException(
                "tx-checksum value of ethtool_opts was not updated correctly "
                "with default value"
            )

        logger.info(
            "Check that bridge_opts parameter has an updated default value"
        )
        if not ll_networks.check_bridge_opts(
            conf.HOSTS_IP[0], conf.HOSTS_USER, conf.HOSTS_PW,
            conf.NET_10, conf.KEY1, conf.BRIDGE_OPTS.get(conf.KEY1)[0]
        ):
            raise exceptions.NetworkException(
                "Priority value of bridge opts was not updated correctly with "
                "default value"
            )

    @classmethod
    def teardown_class(cls):
        """
        Clean host interfaces
        """
        if not hl_host_network.clean_host_interfaces(conf.HOST_NAME_0):
            logger.error("Failed to clean host interfaces")


@attr(tier=0, extra_reqs={'rhel': 7})
class TestSanityCase11(NetworkTest):
    """
    Configure queue for existing network
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Configure and update queue value on vNIC profile for exiting network
        (vNIC CustomProperties) and start vm
        """
        logger.info(
            "Update custom properties on %s to %s", conf.MGMT_BRIDGE,
            conf.PROP_QUEUES[0]
        )
        if not ll_networks.updateVnicProfile(
            name=conf.MGMT_BRIDGE, network=conf.MGMT_BRIDGE,
            data_center=conf.DC_NAME,
            custom_properties=conf.PROP_QUEUES[0]
        ):
            raise exceptions.NetworkException(
                "Failed to set custom properties on %s" % conf.MGMT_BRIDGE
            )
        helper.run_vm_on_host()

    @polarion("RHEVM3-4336")
    def test_multiple_queue_nics(self):
        """
        Check that qemu has correct number of queues
        """
        logger.info("Check that qemu have %s queues", conf.NUM_QUEUES[0])
        if not mqn_helper.check_queues_from_qemu(
            vm=conf.VM_0,
            host_obj=conf.VDS_HOST_0,
            num_queues=conf.NUM_QUEUES[0]
        ):
            raise exceptions.NetworkException(
                "qemu did not return the expected number of queues"
            )

    @classmethod
    def teardown_class(cls):
        """
        Remove custom properties for mgmt network
        """
        logger.info(
            "Remove custom properties on %s", conf.MGMT_BRIDGE
        )
        if not ll_networks.updateVnicProfile(
            name=conf.MGMT_BRIDGE, network=conf.MGMT_BRIDGE,
            data_center=conf.DC_NAME, custom_properties="clear"
        ):
            logger.error(
                "Failed to set custom properties on %s", conf.MGMT_BRIDGE
            )
        helper.stop_vm()


@attr(tier=0)
class TestSanityCase12(NetworkTest):
    """
    List all networks under datacenter.
    """
    __test__ = True
    dc1_net_list = ["_".join(["dc1_net", str(i)]) for i in xrange(10)]

    @classmethod
    def setup_class(cls):
        """
        Create networks under 2 datacenters.
        """
        if not ll_datacenters.addDataCenter(
            positive=True, name=conf.EXTRA_DC,
            storage_type=conf.STORAGE_TYPE, version=conf.COMP_VERSION
        ):
            raise exceptions.NetworkException(
                "Failed to add DC %s" % conf.EXTRA_DC
            )

        logger.info("Create 10 networks under %s", conf.DC_NAME)
        if not ll_networks.create_networks_in_datacenter(
            conf.DC_NAME, 10, "dc1_net"
        ):
            raise exceptions.NetworkException(
                "Fail to create 10 network on %s" % conf.DC_NAME
            )
        logger.info("Create 5 networks under %s", conf.EXTRA_DC)
        if not ll_networks.create_networks_in_datacenter(
            conf.EXTRA_DC, 5, "dc2_net"
        ):
            raise exceptions.NetworkException(
                "Fail to create 5 network on %s" % conf.EXTRA_DC
            )

    @polarion("RHEVM3-4335")
    def test_get_networks_list(self):
        """
        Get all networks under the datacenter.
        """
        logger.info("Check that all networks exist in the datacenters")

        engine_dc_net_list = ll_networks.get_networks_in_datacenter(
            conf.DC_NAME
        )
        for net in self.dc1_net_list:
            if net not in [i.name for i in engine_dc_net_list]:
                raise exceptions.NetworkException(
                    "%s was expected to be in %s" % (net, conf.DC_NAME)
                )
        dc2_net_list = ["_".join(["dc2_net", str(i)]) for i in xrange(5)]
        engine_extra_dc_net_list = ll_networks.get_networks_in_datacenter(
            conf.EXTRA_DC
        )
        for net in dc2_net_list:
            if net not in [i.name for i in engine_extra_dc_net_list]:
                raise exceptions.NetworkException(
                    "%s was expected to be in %s" % (net, conf.EXTRA_DC)
                )

    @classmethod
    def teardown_class(cls):
        """
        Remove extra DC from setup
        Remove networks from the setup.
        """
        if not ll_datacenters.removeDataCenter(
            positive=True, datacenter=conf.EXTRA_DC
        ):
            logger.error("Cannot remove DC")

        logger.info("Remove all networks from %s", conf.DC_NAME)
        if not ll_networks.delete_networks_in_datacenter(
            conf.DC_NAME, conf.MGMT_BRIDGE, cls.dc1_net_list
        ):
            logger.error(
                "Fail to delete all networks from %s", conf.DC_NAME
            )


@attr(tier=0)
class TestSanityCase13(NetworkTest):
    """
    Update VM network to be non-VM network
    Update non-VM network to be VM network
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Attach network to host
        """
        dict_dc1 = {
            conf.NET_13: {"nic": 1}
        }

        logger.info("Attach %s to %s", conf.NET_13, conf.HOST_0)
        if not hl_networks.createAndAttachNetworkSN(
            host=conf.VDS_HOST_0, network_dict=dict_dc1, auto_nics=[0]
        ):
            raise exceptions.NetworkException(
                "Cannot attach %s to %s" % (conf.NET_13, conf.HOST_0)
            )

    @polarion("RHEVM3-4332")
    def test_update_with_non_vm_nonvm(self):
        """
        1) Update network to be non-VM network
        2) Check that the Host was updated accordingly
        3) Update network to be VM network
        4) Check that the Host was updated accordingly
        """
        bridge_dict1 = {"bridge": False}
        bridge_dict2 = {"bridge": True}

        logger.info("Update network %s to be non-VM network", conf.NET_13)
        if not ll_networks.updateNetwork(
            True, network=conf.NET_13, data_center=conf.DC_NAME,
            usages=""
        ):
            raise exceptions.NetworkException(
                "Cannot update network to be non-VM network"
            )

        logger.info("Wait till the Host is updated with the change")
        sample1 = apis_utils.TimeoutingSampler(
            timeout=conf.SAMPLER_TIMEOUT, sleep=1,
            func=hl_networks.checkHostNicParameters, host=conf.HOST_NAME_0,
            nic=conf.HOST_NICS[1], **bridge_dict1
        )
        if not sample1.waitForFuncStatus(result=True):
            raise exceptions.NetworkException(
                "%s is VM network and should be Non-VM" % conf.NET_13
            )

        logger.info("Check that the change is reflected to Host")
        if ll_networks.isVmHostNetwork(
            host=conf.HOSTS_IP[0], user=conf.HOSTS_USER,
            password=conf.HOSTS_PW, net_name=conf.NET_13,
            conn_timeout=45
        ):
            raise exceptions.NetworkException(
                "%s on host %s was not updated to be non-VM network" %
                (conf.NET_13, conf.HOST_NAME_0)
            )

        logger.info("Update network %s to be VM network", conf.NET_13)
        if not ll_networks.updateNetwork(
            True, network=conf.NET_13, data_center=conf.DC_NAME,
            usages="vm"
        ):
            raise exceptions.NetworkException(
                "Cannot update network to be VM network"
            )

        logger.info("Wait till the Host is updated with the change")
        sample2 = apis_utils.TimeoutingSampler(
            timeout=conf.SAMPLER_TIMEOUT, sleep=1,
            func=hl_networks.checkHostNicParameters, host=conf.HOST_NAME_0,
            nic=conf.HOST_NICS[1], **bridge_dict2
        )
        if not sample2.waitForFuncStatus(result=True):
            raise exceptions.NetworkException(
                "%s is not a VM network but should be" % conf.NET_13
            )

        logger.info("Check that the change is reflected to Host")
        if not ll_networks.isVmHostNetwork(
            host=conf.HOSTS_IP[0], user=conf.HOSTS_USER,
            password=conf.HOSTS_PW, net_name=conf.NET_13
        ):
            raise exceptions.NetworkException(
                "%s on host %s was not updated to be VM network" %
                (conf.NET_13, conf.HOST_NAME_0)
            )

    @classmethod
    def teardown_class(cls):
        """
        Clean host interfaces
        """
        if not hl_host_network.clean_host_interfaces(conf.HOST_NAME_0):
            logger.error("Failed to clean host interfaces")


@attr(tier=0)
class TestSanityCase14(NetworkTest):
    """
    Verify you can configure additional VLAN network with static IP and gateway
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Create logical tagged network on DC/Cluster/Hosts.
        Configure it with static IP configuration.
        """
        local_dict = {
            conf.NET_14: {
                "nic": 1,
                "bootproto": "static",
                "address": [conf.MG_IP_ADDR],
                "netmask": [conf.NETMASK],
                "gateway": [conf.MG_GATEWAY]
            }
        }

        if not hl_networks.createAndAttachNetworkSN(
            host=conf.VDS_HOST_0, network_dict=local_dict,
            auto_nics=[0]
        ):
            raise exceptions.NetworkException(
                "Cannot attach network %s" % conf.NET_14
            )

    @polarion("RHEVM3-4331")
    def test_check_ip_rule(self):
        """
        Check correct configuration with ip rule function
        """
        if not ll_networks.checkIPRule(
            conf.HOSTS_IP[0], user=conf.HOSTS_USER,
            password=conf.HOSTS_PW, subnet=conf.SUBNET
        ):
            raise conf.NET_EXCEPTION(
                "%s have wrong IP configuration" % conf.NET_14
            )

    @classmethod
    def teardown_class(cls):
        """
        Clean host interfaces
        """
        if not hl_host_network.clean_host_interfaces(conf.HOST_NAME_0):
            logger.error("Failed to clean host interfaces")


@attr(tier=0)
class TestSanityCase15(NetworkTest):
    """
    1) Put label on Host NIC of one Host
    2) Check network is attached to Host
    """
    __test__ = True

    @polarion("RHEVM3-4330")
    def test_label_several_interfaces(self):
        """
        1) Put label on Host NIC
        2) Put label on the network
        3) Check network is attached to Host
        """
        logger.info(
            "Attach label %s to Host NIC %s and to the network %s",
            conf.LABEL_LIST[0], conf.HOST_NICS[1], conf.NET_15
        )

        if not ll_networks.add_label(
            label=conf.LABEL_LIST[0], host_nic_dict={
                conf.HOST_NAME_0: [conf.HOST_NICS[1]]
            }, networks=[conf.NET_15]
        ):
            raise exceptions.NetworkException(
                "Couldn't attach label %s " % conf.LABEL_LIST[0]
            )

        logger.info(
            "Check network %s is attached to interface %s on Host %s",
            conf.NET_15, conf.HOST_NICS[1], conf.HOST_NAME_0
        )
        if not ll_networks.check_network_on_nic(
            conf.NET_15, conf.HOST_NAME_0, conf.HOST_NICS[1]
        ):
            raise exceptions.NetworkException(
                "Network %s is not attached to NIC %s " %
                (conf.NET_15, conf.HOST_NICS[1])
            )

    @classmethod
    def teardown_class(cls):
        """
        Remove label from the NIC
        Remove network from setup
        """
        logger.info("Remove label from %s", conf.HOST_NICS[1])
        if not ll_networks.remove_label(
            host_nic_dict={conf.HOST_NAME_0: [conf.HOST_NICS[1]]}
        ):
            logger.error("Couldn't remove labels from %s", conf.HOST_NICS[1])


@attr(tier=0)
class TestSanityCase16(NetworkTest):
    """
    Add new network QOS
    """
    __test__ = True
    BW_PARAMS = (10, 10, 100)
    QOS_NAME = "QoSProfile1"
    QOS_TYPE = "network"

    @polarion("RHEVM3-4342")
    def test_add_network_qos(self):
        """
        1) Create new Network QoS profile under DC
        2) Provide Inbound and Outbound parameters for this QOS
        3) Create VNIC profile with configured QoS and add it to the NIC of
        the VM
        4) Check that provided bw values are the same as the values
        configured on libvirt
        """
        logger.info("Create new Network QoS profile under DC")
        if not ll_datacenters.add_qos_to_datacenter(
            datacenter=conf.DC_NAME,
            qos_name=self.QOS_NAME,
            qos_type=self.QOS_TYPE,
            inbound_average=self.BW_PARAMS[0],
            inbound_peak=self.BW_PARAMS[1],
            inbound_burst=self.BW_PARAMS[2],
            outbound_average=self.BW_PARAMS[0],
            outbound_peak=self.BW_PARAMS[1],
            outbound_burst=self.BW_PARAMS[2]
        ):
            raise exceptions.NetworkException(
                "Couldn't create Network QOS under DC"
            )
        logger.info(
            "Create VNIC profile with QoS and add it to the VNIC"
        )
        nq_helper.add_qos_profile_to_nic()
        helper.run_vm_on_host()
        inbound_dict = {
            "average": self.BW_PARAMS[0],
            "peak": self.BW_PARAMS[1],
            "burst": self.BW_PARAMS[2]
        }
        outbound_dict = {
            "average": self.BW_PARAMS[0],
            "peak": self.BW_PARAMS[1],
            "burst": self.BW_PARAMS[2]
        }
        dict_compare = nq_helper.build_dict(
            inbound_dict=inbound_dict, outbound_dict=outbound_dict,
            vm=conf.VM_0, nic=conf.NIC_1
        )

        logger.info(
            "Compare provided QoS %s and %s exists with libvirt values",
            inbound_dict, outbound_dict
        )
        if not nq_helper.compare_qos(
            host_obj=conf.VDS_HOST_0, vm_name=conf.VM_0,
            **dict_compare
        ):
            raise exceptions.NetworkException(
                "Provided QoS values %s and %s are not equal to what was "
                "found on libvirt" % (inbound_dict, outbound_dict)
            )

    @classmethod
    def teardown_class(cls):
        """
        1) Remove VNIC from VM.
        2) Remove VNIC profile
        3) Remove Network QoS
        4) Stop VM
        """
        try:
            logger.info(
                "Remove VNIC from VM %s", conf.VM_NAME[0]
            )
            if not ll_vms.updateNic(
                True, conf.VM_NAME[0], conf.NIC_NAME[1], plugged='false'
            ):
                logger.error("Couldn't unplug NIC %s", conf.NIC_NAME[1])

            if not ll_vms.removeNic(
                True, conf.VM_NAME[0], conf.NIC_NAME[1]
            ):
                logger.error(
                    "Couldn't remove VNIC from VM %s", conf.VM_NAME[0]
                )
        except apis_exceptions.EntityNotFound:
            logger.error(
                "Couldn't remove %s from %s", conf.NIC_NAME[1],
                conf.VM_NAME[0]
            )
        logger.info(
            "Remove VNIC profile %s", conf.VNIC_PROFILE[0]
        )
        if not ll_networks.removeVnicProfile(
            positive=True, vnic_profile_name=conf.VNIC_PROFILE[0],
            network=conf.MGMT_BRIDGE, data_center=conf.DC_NAME
        ):
            logger.error(
                "Couldn't remove VNIC profile %s", conf.VNIC_PROFILE[0]
            )
        if not ll_datacenters.delete_qos_from_datacenter(
            conf.DC_NAME, cls.QOS_NAME
        ):
            logger.error(
                "Couldn't delete the QoS %s from DC %s",
                cls.QOS_NAME, conf.DC_NAME
            )
        helper.stop_vm()


@attr(tier=0)
class TestSanityCase17(NetworkTest):
    """
    Negative: Create more than 5 BONDS using dummy interfaces
    """
    apis = set(["rest"])

    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Create dummy interface for BONDS
        """
        logger.info("Create 20 dummy interfaces")
        if not hl_networks.create_dummy_interfaces(
            host=conf.VDS_HOST_0, num_dummy=20
        ):
            raise exceptions.NetworkException(
                "Failed to create dummy interfaces"
            )

        logger.info("Refresh host capabilities")
        host_obj = ll_hosts.HOST_API.find(conf.HOSTS[0])
        refresh_href = "{0};force".format(host_obj.get_href())
        ll_hosts.HOST_API.get(href=refresh_href)

        logger.info("Check if dummy_0 exist on host via engine")
        sample = apis_utils.TimeoutingSampler(
            timeout=conf.SAMPLER_TIMEOUT, sleep=1,
            func=helper.check_dummy_on_host_interfaces, dummy_name="dummy_0"
        )
        if not sample.waitForFuncStatus(result=True):
            raise exceptions.NetworkException(
                "Dummy interface not exists on engine"
            )

    @polarion("RHEVM3-4339")
    def test_dummy_bonds(self):
        """
        Create 10 BONDS using dummy interfaces
        """
        logger.info("Generate bond object with 2 dummy interfaces")
        net_obj = []
        idx = 0
        while idx < 20:
            rc, out = ll_hosts.genSNNic(
                nic="bond%s" % idx, slaves=[
                    "dummy_%s" % idx, "dummy_%s" % (idx + 1)
                ]
            )
            if not rc:
                raise exceptions.NetworkException("Cannot generate NIC object")

            net_obj.append(out["host_nic"])
            idx += 2

        logger.info("send SNRequest: 10 bonds on dummy interfaces")
        if not ll_hosts.sendSNRequest(
            True, host=conf.HOST_NAME_0, nics=net_obj,
            auto_nics=[conf.VDS_HOST_0.nics[0]],
            check_connectivity="true", connectivity_timeout=conf.TIMEOUT,
            force="false"
        ):
            raise exceptions.NetworkException("Failed to SNRequest")

    @classmethod
    def teardown_class(cls):
        """
        Delete all bonds and dummy interfaces
        """
        logger.info("Delete all dummy interfaces")
        if not hl_networks.delete_dummy_interfaces(host=conf.VDS_HOST_0):
            logger.error("Failed to delete dummy interfaces")

        logger.info("Refresh host capabilities")
        host_obj = ll_hosts.HOST_API.find(conf.HOSTS[0])
        refresh_href = "{0};force".format(host_obj.get_href())
        ll_hosts.HOST_API.get(href=refresh_href)

        logger.info("Check if dummy_0 not exist on host via engine")
        sample = apis_utils.TimeoutingSampler(
            timeout=conf.SAMPLER_TIMEOUT, sleep=1,
            func=helper.check_dummy_on_host_interfaces, dummy_name="dummy_0"
        )
        if not sample.waitForFuncStatus(result=False):
            logger.error("Dummy interface exists on engine")
