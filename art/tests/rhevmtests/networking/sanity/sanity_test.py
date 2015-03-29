"""
Testing Sanity for the network features.
1 DC, 1 Cluster, 1 Hosts and 1 VM will be created for testing.
Sanity will test untagged, tagged, bond scenarios.
It will cover scenarios for VM/non-VM networks.
"""

import logging
from art.unittest_lib import attr
from art.unittest_lib import NetworkTest as TestCase
from art.core_api.apis_exceptions import EntityNotFound

from art.rhevm_api.tests_lib.low_level.datacenters import(
    add_qos_to_datacenter, delete_qos_from_datacenter, addDataCenter,
    removeDataCenter
)
from art.test_handler.tools import tcms  # pylint: disable=E0611
from art.core_api.apis_utils import TimeoutingSampler
from art.rhevm_api.utils.test_utils import(
    set_engine_properties, get_engine_properties, get_api
)
from art.test_handler.exceptions import NetworkException
from art.rhevm_api.tests_lib.low_level import vms
from rhevmtests.networking import config
from art.rhevm_api.tests_lib.high_level.networks import(
    createAndAttachNetworkSN, remove_net_from_setup, create_dummy_interfaces,
    delete_dummy_interfaces, update_network_host, checkHostNicParameters
)
from art.rhevm_api.tests_lib.low_level.hosts import(
    checkNetworkFilteringDumpxml, genSNNic, sendSNRequest,
    get_host_name_from_engine
)
from art.rhevm_api.tests_lib.low_level.vms import(
    addNic, removeNic, getVmNicLinked, getVmNicPlugged, updateNic,
    stopVm, startVm
)
from art.rhevm_api.tests_lib.low_level.networks import(
    updateClusterNetwork, isVMNetwork, isNetworkRequired, updateNetwork,
    addVnicProfile, removeVnicProfile, removeNetwork, check_ethtool_opts,
    check_bridge_opts, updateVnicProfile, create_networks_in_datacenter,
    get_networks_in_datacenter, delete_networks_in_datacenter, isVmHostNetwork,
    checkIPRule, check_network_on_nic, add_label, remove_label
)
from art.rhevm_api.utils.test_utils import checkMTU

from rhevmtests.networking.multiple_queue_nics.helper import(
    check_queues_from_qemu
)
from rhevmtests.networking.network_qos.helper import(
    add_qos_profile_to_nic, build_dict, compare_qos
)
from rhevmtests.networking.sanity.helper import check_dummy_on_host_interfaces


HOST_API = get_api("host", "hosts")
HOST_NICS = None  # filled in setup module
HOST_NAME0 = None  # Fill in setup_module
DC_NAMES = [config.DC_NAME[0], config.EXTRA_DC]

logger = logging.getLogger("Sanity_Cases")


def setup_module():
    """
    Obtain host IP and host nics
    """
    global HOST_NICS
    global HOST_NAME0
    HOST_NICS = config.VDS_HOSTS[0].nics
    HOST_NAME0 = get_host_name_from_engine(config.VDS_HOSTS[0].ip)


@attr(tier=0)
class TestSanityCase01(TestCase):
    """
    Validate that MANAGEMENT is Required by default
    """
    __test__ = True

    def test_validate_mgmt(self):
        """
        Check that MGMT is a required network
        """
        logger.info(
            "Checking that mgmt network is required by default"
        )
        self.assertTrue(
            isNetworkRequired(
                network=config.MGMT_BRIDGE, cluster=config.CLUSTER_NAME[0]
            ), "mgmt network is not required by default"
        )

########################################################################

########################################################################


@attr(tier=0)
class TestSanityCase02(TestCase):
    """
    Check static ip:
    Creating network (sw162) with static ip, Attaching it to interface,
    and finally, remove the network.
    """
    __test__ = True
    vlan = config.VLAN_NETWORKS[0]

    def test_check_static_ip(self):
        """
        Create vlan sw162 with static ip (1.1.1.1) on first non-mgmt interface
        """

        logger.info("Create network and attach it to the host")
        local_dict = {
            self.vlan: {
                "vlan_id": config.VLAN_ID[0], "nic": 1, "required": "false",
                "bootproto": "static", "address": ["1.1.1.1"],
                "netmask": ["255.255.255.0"]
            }
        }

        if not createAndAttachNetworkSN(
            data_center=config.DC_NAME[0], cluster=config.CLUSTER_NAME[0],
            host=config.VDS_HOSTS[0], network_dict=local_dict, auto_nics=[0, 1]
        ):
            raise NetworkException("Cannot create and attach network")

    @classmethod
    def teardown_class(cls):
        """
        Remove network sw162 from the setup
        """
        logger.info("Starting the teardown_class")

        if not remove_net_from_setup(
            host=config.VDS_HOSTS[0], network=[cls.vlan],
            mgmt_network=config.MGMT_BRIDGE, data_center=config.DC_NAME[0]
        ):
            logger.error("Cannot remove network from setup")

########################################################################

########################################################################


@attr(tier=0)
class TestSanityCase03(TestCase):
    """
    Check VM network & non_VM network (vlan test):
    Creating two networks (sw162 & sw163) on eth1 while one is VM network
    and the other is non_VM network. Then, Check that the creation of the
    networks created a proper networks (VM & non_VM).
    Finally, removing the networks.
    """
    __test__ = True
    vlan1 = config.VLAN_NETWORKS[0]
    vlan2 = config.VLAN_NETWORKS[1]

    @classmethod
    def setup_class(cls):
        """
        Create vm network sw162 & non-vm network sw163
        Attach to the host on the first non-mgmgt network
        """

        logger.info("Create networks and attach them to the host")
        local_dict = {cls.vlan1: {"vlan_id": config.VLAN_ID[0],
                                  "nic": 1,
                                  "required": "false"},
                      cls.vlan2: {"vlan_id": config.VLAN_ID[1],
                                  "usages": "",
                                  "nic": 1,
                                  "required": "false"}}

        if not createAndAttachNetworkSN(
            data_center=config.DC_NAME[0], cluster=config.CLUSTER_NAME[0],
            host=config.VDS_HOSTS[0], network_dict=local_dict, auto_nics=[0, 1]
        ):
            raise NetworkException("Cannot create and attach network")

    def test_check_networks_usages(self):
        """
        Checking that sw162 is a vm network & sw163 is a non-vm network
        """
        logger.info("Checking VM network %s", self.vlan1)
        self.assertTrue(isVMNetwork(
            network=self.vlan1, cluster=config.CLUSTER_NAME[0]
        ), "%s is not VM Network" % self.vlan1)

        logger.info("Checking non-VM network %s", self.vlan2)
        self.assertFalse(isVMNetwork(
            network=self.vlan2, cluster=config.CLUSTER_NAME[0]
        ), "%s is not NON_VM network" % self.vlan2)

    @classmethod
    def teardown_class(cls):
        """
        Removing networks from the setup
        """
        logger.info("Starting the teardown_class")
        if not remove_net_from_setup(
            host=config.VDS_HOSTS[0], network=[cls.vlan1, cls.vlan2],
            mgmt_network=config.MGMT_BRIDGE, data_center=config.DC_NAME[0]
        ):
            logger.error("Cannot remove network from setup")

########################################################################

########################################################################


@attr(tier=0)
class TestSanityCase04(TestCase):
    """
    Check VM network & non_VM network:
    1. Check that the creation of the network created a proper network (VM).
    2. Update sw164 to be NON_VM
    3. Check that the update of the network is proper (NON_VM).
    Finally, removing the networks.
    """
    __test__ = True
    vlan = config.VLAN_NETWORKS[2]

    @classmethod
    def setup_class(cls):
        """
        Create vm network sw164
        """
        logger.info("Create network and attach it to the host")
        local_dict = {cls.vlan: {"vlan_id": config.VLAN_ID[2],
                                 "required": "false"}}

        if not createAndAttachNetworkSN(
            data_center=config.DC_NAME[0], cluster=config.CLUSTER_NAME[0],
            network_dict=local_dict
        ):
            raise NetworkException("Cannot create and attach network")

    def test_check_networks_usages(self):
        """
        Checking that sw164 is a vm network, Changing it to non_VM network
        and checking that it is not non_VM
        """
        logger.info("Checking bridged network %s", self.vlan)
        self.assertTrue(isVMNetwork(
            network=self.vlan, cluster=config.CLUSTER_NAME[0]
        ), "%s is NON_VM network but it should be VM" % self.vlan)

        logger.info("Updating %s to be non_VM network", self.vlan)
        if not updateNetwork(
            positive=True, network=self.vlan, usages="",
            cluster=config.CLUSTER_NAME[0]
        ):
            raise NetworkException(
                "Failed to update %s to be non_VM network" % self.vlan
            )

        logger.info("Checking non-VM network %s", self.vlan)
        self.assertFalse(
            isVMNetwork(network=self.vlan, cluster=config.CLUSTER_NAME[0]),
            "%s is VM network when it should be NON_VM" % self.vlan
        )

    @classmethod
    def teardown_class(cls):
        """
        Removing sw164 network from the setup
        """
        logger.info("Starting the teardown_class")
        if not removeNetwork(True, cls.vlan):
            logger.error("Cannot remove network from setup")

########################################################################

########################################################################


@attr(tier=0)
class TestSanityCase05(TestCase):
    """
    Checking Port Mirroring:
    Creating vnic profile with network sw162 and port mirroring enabled,
    attaching it to first non-mgmt interface.
    Finally, remove nic and network
    """
    __test__ = True
    vlan = config.VLAN_NETWORKS[0]
    nic = config.NIC_NAME[1]
    vnic_profile = config.VNIC_PROFILE[0]

    @classmethod
    def setup_class(cls):
        """
        Create
        """
        logger.info(
            "Create network sw162 on DC/Cluster/Host"
        )
        local_dict = {
            cls.vlan: {
                "vlan_id": config.VLAN_ID[0], "nic": 1, "required": "false"
            }
        }

        if not createAndAttachNetworkSN(
            data_center=config.DC_NAME[0], host=config.VDS_HOSTS[0],
            cluster=config.CLUSTER_NAME[0], network_dict=local_dict,
            auto_nics=[0, 1]
        ):
            raise NetworkException("Cannot create and attach network")

        logger.info(
            "Create profile with %s network and port mirroring enabled",
            cls.vlan
        )
        if not addVnicProfile(
            positive=True, name=cls.vnic_profile,
            cluster=config.CLUSTER_NAME[0], network=cls.vlan,
            port_mirroring=True
        ):
            raise NetworkException(
                "Failed to add %s profile with %s network to %s" %
                (config.VNIC_PROFILE[0], cls.vlan, config.CLUSTER_NAME[0]))

    def test_attach_vnic_to_vm(self):
        """
        Attaching vnic to VM
        """
        if not addNic(
            positive=True, vm=config.VM_NAME[0], name=self.nic,
            network=self.vlan
        ):
            raise NetworkException("Adding %s failed" % config.NIC_NAME[1])

    @classmethod
    def teardown_class(cls):
        """
        Remove nic and network from the setup
        """
        logger.info("Starting the teardown_class")
        logger.info("Unplug NIC %s", cls.nic)
        if not updateNic(
            positive=True, vm=config.VM_NAME[0], nic=cls.nic, plugged=False
        ):
            logger.error("Unplug %s failed", cls.nic)

        if not removeNic(positive=True, vm=config.VM_NAME[0], nic=cls.nic):
            logger.error("Removing %s failed", cls.nic)

        if not removeVnicProfile(
            positive=True, vnic_profile_name=cls.vnic_profile, network=cls.vlan
        ):
            logger.error(
                "Failed to remove %s profile", cls.vnic_profile
            )

        if not remove_net_from_setup(
            host=config.VDS_HOSTS[0], all_net=True,
            mgmt_network=config.MGMT_BRIDGE, data_center=config.DC_NAME[0]
        ):
            logger.error("Cannot remove network from setup")


########################################################################

########################################################################


@attr(tier=0)
class TestSanityCase06(TestCase):
    """
    Checking required network:
    Creating network sw162 as required and attaching it to the host NIC,
    then:
    1. Verifying that the network is required
    2. Updating network to be not required
    3. Checking that the network is non-required
    Finally, removing the network from the setup.
    """
    __test__ = True
    vlan = config.VLAN_NETWORKS[0]

    @classmethod
    def setup_class(cls):
        """
        Creating network sw162 as required and attaching it to the host NIC
        """
        logger.info("Create required network and attach it to the host NIC")
        local_dict = {
            cls.vlan: {
                "vlan_id": config.VLAN_ID[0], "nic": 1, "required": "true"
            }
        }

        if not createAndAttachNetworkSN(
            data_center=config.DC_NAME[0], cluster=config.CLUSTER_NAME[0],
            host=config.VDS_HOSTS[0], network_dict=local_dict, auto_nics=[0, 1]
        ):
            raise NetworkException("Cannot create and attach network")

    def test_check_required(self):
        """
        Verifying that the network is required,
        updating network to be not required and checking
        that the network is non-required
        """
        logger.info("Checking that Network % s is required", self.vlan)
        self.assertTrue(
            isNetworkRequired(
                network=self.vlan, cluster=config.CLUSTER_NAME[0]
            ), "Network %s is non-required, Should be required" % self.vlan
        )

        logger.info("Updating %s to be non-required", self.vlan)
        if not updateClusterNetwork(
            positive=True, cluster=config.CLUSTER_NAME[0],
            network=self.vlan, required=False
        ):
            raise NetworkException(
                "Updating %s to non-required failed" % self.vlan
            )

        logger.info("Checking that Network % s is non-required", self.vlan)
        self.assertFalse(
            isNetworkRequired(
                network=self.vlan, cluster=config.CLUSTER_NAME[0]
            ),
            "Network %s is required, Should be non-required" % self.vlan
        )

    @classmethod
    def teardown_class(cls):
        """
        Remove network from the setup
        """
        logger.info("Starting the teardown_class")
        if not remove_net_from_setup(
            host=config.VDS_HOSTS[0], network=[cls.vlan],
            mgmt_network=config.MGMT_BRIDGE, data_center=config.DC_NAME[0]
        ):
            logger.error("Cannot remove network from setup")


########################################################################

########################################################################


@attr(tier=0)
class TestSanityCase07(TestCase):
    """
    Checking required network over Bond:
    Creating network sw163 as required and attaching it to the host Bond
    (eth2 & eth3), then:
    1. Verifying that the network is required
    2. Updating network to be not required
    3. Checking that the network is non-required
    Finally, removing the network from the setup.
    """
    __test__ = True
    bond = config.BOND[0]
    vlan = config.VLAN_NETWORKS[1]

    @classmethod
    def setup_class(cls):
        logger.info("Create network and attach it to the host")
        local_dict = {
            None: {"nic": cls.bond, "mode": 1, "slaves": [2, 3]},
            config.VLAN_NETWORKS[1]: {
                "nic": cls.bond, "vlan_id": config.VLAN_ID[1],
                "required": "true"
            }
        }

        if not createAndAttachNetworkSN(
            data_center=config.DC_NAME[0], cluster=config.CLUSTER_NAME[0],
            host=config.VDS_HOSTS[0], network_dict=local_dict, auto_nics=[0]
        ):
            raise NetworkException("Cannot create and attach network")

    def test_check_required(self):
        """
        Verifying that the network is required, updating network to be
        not required and then checking that the network is non-required
        """
        logger.info("Check that network %s is required", self.vlan)
        self.assertTrue(
            isNetworkRequired(
                network=self.vlan, cluster=config.CLUSTER_NAME[0]
            ), "Network %s is non-required, Should be required" % self.vlan
        )

        logger.info("Update %s to be non-required", self.vlan)
        if not updateClusterNetwork(
            positive=True, cluster=config.CLUSTER_NAME[0],
            network=self.vlan, required=False
        ):
            raise NetworkException(
                "Updating %s to non-required failed" % self.vlan
            )

        logger.info("Check that network %s is non-required", self.vlan)
        self.assertFalse(
            isNetworkRequired(
                network=self.vlan, cluster=config.CLUSTER_NAME[0]
            ), "Network %s is required, Should be non-required" % self.vlan
        )

    @classmethod
    def teardown_class(cls):
        """
        Removing the network from the setup.
        """
        logger.info("Starting the teardown_class")
        if not remove_net_from_setup(
            host=config.VDS_HOSTS[0], network=[cls.vlan],
            mgmt_network=config.MGMT_BRIDGE, data_center=config.DC_NAME[0]
        ):
            logger.error("Cannot remove network from setup")


########################################################################

########################################################################

@attr(tier=0)
class TestSanityCase08(TestCase):
    """
    Checking Jumbo Frame (vlan test):
    Creating and adding sw162 (MTU 9000) & sw163 (MTU 5000) to the host
    on eth1, then:
    1. Check that MTU on sw162 is really 9000
    2. Check that MTU on interface with networks is 9000
    3. Updating sw162's MTU to 1500
    4. Check that MTU on sw162 is really 1500
    5. Check that MTU on interface with networks is 5000
    Finally, removing sw162 & sw163 from the setup
    """
    __test__ = True
    vlan_1 = config.VLAN_NETWORKS[0]
    vlan_2 = config.VLAN_NETWORKS[1]
    vlan_id_1 = config.VLAN_ID[0]
    vlan_id_2 = config.VLAN_ID[1]

    @classmethod
    def setup_class(cls):
        """
        Creating and adding sw162 (MTU 9000) & sw163 (MTU 5000)to the host
        on eth1
        """
        logger.info(
            "Create networks %s and %s on DC/Cluster/Host",
            cls.vlan_1, cls.vlan_2
        )
        local_dict = {
            cls.vlan_1: {
                "vlan_id": cls.vlan_id_1, "nic": 1, "required": "false",
                "mtu": config.MTU[0]
            },
            cls.vlan_2: {
                "vlan_id": cls.vlan_id_2, "nic": 1, "required": "false",
                "mtu": config.MTU[1]
            }
        }

        if not createAndAttachNetworkSN(data_center=config.DC_NAME[0],
                                        cluster=config.CLUSTER_NAME[0],
                                        host=config.VDS_HOSTS[0],
                                        network_dict=local_dict,
                                        auto_nics=[0, 1]):
            raise NetworkException(
                "Cannot create and attach networks %s and %s" %
                (cls.vlan_1, cls.vlan_2)
            )

    def test_check_mtu(self):
        """
        1. Check that MTU=9000 on sw162
        2. Check that MTU=9000 on interface with networks
        3. Check that MTU=1500 on sw162 after MTU update
        4. Check that MTU=5000 on interface with networks after update
        """
        logger.info("Check that MTU on network is %s", config.MTU[0])
        self.assertTrue(
            checkMTU(
                host=config.HOSTS_IP[0], user=config.HOSTS_USER,
                password=config.HOSTS_PW, mtu=config.MTU[0],
                physical_layer=False, network=self.vlan_1,
                nic=config.VDS_HOSTS[0].nics[1], vlan=self.vlan_id_1
            ), "%s is not configured logically with MTU 9000" % self.vlan_1
        )

        logger.info("Check that MTU on interface is %s", config.MTU[0])
        self.assertTrue(
            checkMTU(
                host=config.HOSTS_IP[0], user=config.HOSTS_USER,
                password=config.HOSTS_PW, mtu=config.MTU[0],
                nic=config.VDS_HOSTS[0].nics[1]
            ), "physical layer for %s is not configured with MTU 9000" %
            self.vlan_1
        )

        logger.info("Update MTU on %s to be %s", self.vlan_1, config.MTU[3])
        self.assertTrue(updateNetwork(positive=True, network=self.vlan_1,
                                      mtu=config.MTU[3]),
                        "%s was not updated with MTU %s" % (
                            self.vlan_1, config.MTU[3]))

        logger.info(
            "Check that MTU on network after update is %s", config.MTU[3]
        )
        sample = TimeoutingSampler(
            timeout=config.SAMPLER_TIMEOUT, sleep=1,
            func=checkMTU, host=config.HOSTS_IP[0], user=config.HOSTS_USER,
            password=config.HOSTS_PW, mtu=config.MTU[3], physical_layer=False,
            network=self.vlan_1, nic=config.VDS_HOSTS[0].nics[1],
            vlan=self.vlan_id_1
        )

        if not sample.waitForFuncStatus(result=True):
            raise NetworkException("Couldn't get correct MTU")

        logger.info("Check that MTU on interface is %s", config.MTU[1])
        self.assertTrue(checkMTU(host=config.HOSTS_IP[0],
                                 user=config.HOSTS_USER,
                                 password=config.HOSTS_PW,
                                 mtu=config.MTU[1],
                                 nic=config.VDS_HOSTS[0].nics[1]))

    @classmethod
    def teardown_class(cls):
        """
        Removing sw162 & sw163 from the setup
        """
        logger.info("Starting the teardown_class")
        if not remove_net_from_setup(
            host=config.VDS_HOSTS[0], network=[cls.vlan_1, cls.vlan_2],
            mgmt_network=config.MGMT_BRIDGE, data_center=config.DC_NAME[0]
        ):
            logger.error("Cannot remove network from setup")

        logger.info("Update MTU to default on Host NIC1")
        cmd = [
            "ip", "link", "set", "mtu", str(config.MTU[3]),
            config.VDS_HOSTS[0].nics[1]
        ]
        host_exec = config.VDS_HOSTS[0].executor()
        rc, out, error = host_exec.run_cmd(cmd)
        if rc:
            logger.error("Failed to run %s. ERR: %s", cmd, error)

########################################################################

########################################################################


@attr(tier=0)
class TestSanityCase09(TestCase):
    """
    Checking Jumbo Frame - VLAN over Bond:
    Creating and adding sw162 (MTU 2000) to the host Bond, then checking that
    MTU on sw162 is really 2000
    Finally, removing sw162 from the setup
    """
    __test__ = True
    bond = config.BOND[0]
    vlan = config.VLAN_NETWORKS[0]
    vlan_id = config.VLAN_ID[0]

    @classmethod
    def setup_class(cls):
        """
        Creating and adding sw162 (MTU 2000) to the host Bond
        """
        logger.info(
            "Create %s and attach it to the host Bond", cls.vlan)
        local_dict = {None: {"nic": cls.bond,
                             "mode": 1,
                             "slaves": [2, 3]},
                      config.VLAN_NETWORKS[0]: {"nic": cls.bond,
                                                "vlan_id": cls.vlan_id,
                                                "mtu": config.MTU[2],
                                                "required": "false"}}

        if not createAndAttachNetworkSN(data_center=config.DC_NAME[0],
                                        cluster=config.CLUSTER_NAME[0],
                                        host=config.VDS_HOSTS[0],
                                        network_dict=local_dict,
                                        auto_nics=[0]):
            raise NetworkException("Cannot create and attach network")

    def test_check_mtu(self):
        """
        Check that MTU on sw162 is really 2000
        """
        logger.info(
            "Checking that %s was created with mtu = %s", self.vlan,
            config.MTU[2]
        )
        self.assertTrue(
            checkMTU(
                host=config.HOSTS_IP[0], user=config.HOSTS_USER,
                password=config.HOSTS_PW, mtu=config.MTU[2],
                physical_layer=False, network=self.vlan,
                nic=self.bond, vlan=self.vlan_id
            ),
            "%s is not configured with mtu = %s" % (self.vlan, config.MTU[2])
        )

    @classmethod
    def teardown_class(cls):
        """
        Remove network from the setup
        """
        logger.info("Starting the teardown_class")
        if not remove_net_from_setup(
            host=config.VDS_HOSTS[0], network=[cls.vlan],
            mgmt_network=config.MGMT_BRIDGE, data_center=config.DC_NAME[0]
        ):
            logger.error("Cannot remove network from setup")

########################################################################

########################################################################


@attr(tier=0)
class TestSanityCase10(TestCase):
    """
    Check that network filter is enabled for hot-plug  NIC to on VM
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Adding nic2 to VM
        """
        logger.info("Adding %s to VM", config.NIC_NAME[1])
        if not addNic(
            positive=True, vm=config.VM_NAME[0], name=config.NIC_NAME[1],
            interface=config.NIC_TYPE_RTL8139, network=config.MGMT_BRIDGE
        ):
            raise NetworkException(
                "Failed to add NIC %s to VM", config.NIC_NAME[1]
            )

    @tcms(16421, 448114)
    def test_check_network_filter_on_nic(self):
        """
        Check that the new NIC has network filter
        """
        logger.info(
            "Check that Network Filter is enabled for %s via dumpxml",
            config.NIC_NAME[1]
        )
        if not checkNetworkFilteringDumpxml(
            positive=True, host=config.HOSTS_IP[0], user=config.HOSTS_USER,
            passwd=config.HOSTS_PW, vm=config.VM_NAME[0], nics="2"
        ):
            raise NetworkException(
                "Network Filter is disabled for %s via dumpxml" %
                config.NIC_NAME[1]
            )

    @classmethod
    def teardown_class(cls):
        """
        Un-plug and remove nic2 from VM
        """
        logger.info("Unplug %s", config.NIC_NAME[1])
        if not updateNic(
            True, config.VM_NAME[0], config.NIC_NAME[1], plugged=False
        ):
            logger.error("Failed to remove %s from VM", config.NIC_NAME[1])

        logger.info("Removing %s from VM", config.NIC_NAME[1])
        if not removeNic(
            positive=True, vm=config.VM_NAME[0], nic=config.NIC_NAME[1]
        ):
            logger.error("Failed to remove %s", config.NIC_NAME[1])


########################################################################

########################################################################


@attr(tier=0)
class TestSanityCase11(TestCase):
    """
    Checking Linking:
    Creating 4 networks (sw162, sw163, sw164 & sw165) and adding them to
    the host.
    Creating vnics (with all permutations of plugged & linked)
    and attaching them to the vm.
    Checking that all the permutations of plugged & linked are correct
    Finally, Removing the nics and networks.
    """
    __test__ = True
    vlan_1 = config.VLAN_NETWORKS[0]
    vlan_2 = config.VLAN_NETWORKS[1]
    vlan_3 = config.VLAN_NETWORKS[2]
    vlan_4 = config.VLAN_NETWORKS[3]
    vlan_id_1 = config.VLAN_ID[0]
    vlan_id_2 = config.VLAN_ID[1]
    vlan_id_3 = config.VLAN_ID[2]
    vlan_id_4 = config.VLAN_ID[3]

    @classmethod
    def setup_class(cls):
        """
        Creating 4 networks (sw162, sw163, sw164 & sw165) and adding them to
        the host. Then creating vnics (with all permutations of
        plugged & linked) and attaching them to the vm
        """
        logger.info("Create networks and attach them to the host")
        local_dict = {
            cls.vlan_1: {
                "vlan_id": cls.vlan_id_1, "nic": 1, "required": "false"
            },
            cls.vlan_2: {
                "vlan_id": cls.vlan_id_2, "nic": 1, "required": "false"
            },
            cls.vlan_3: {
                "vlan_id": cls.vlan_id_3, "nic": 1, "required": "false"
            },
            cls.vlan_4: {
                "vlan_id": cls.vlan_id_4, "nic": 1, "required": "false"
            }
        }

        if not createAndAttachNetworkSN(
            data_center=config.DC_NAME[0], cluster=config.CLUSTER_NAME[0],
            host=config.VDS_HOSTS[0], network_dict=local_dict, auto_nics=[0, 1]
        ):
            raise NetworkException("Cannot create and attach networks")

        logger.info("Create VNICs with different plugged/linked permutations")
        plug_link_param_list = [("true", "true"), ("true", "false"),
                                ("false", "true"), ("false", "false")]
        for nic, plug_link, net in zip(
            config.NIC_NAME[1:], plug_link_param_list, config.VLAN_NETWORKS
        ):
            if not addNic(
                True, config.VM_NAME[0], name=nic, network=net,
                plugged=plug_link[0], linked=plug_link[1]
            ):
                raise NetworkException("Cannot add nic %s to VM" % nic)

    def test_check_combination_plugged_linked_values(self):
        """
        Check all permutation for the Plugged/Linked options on VNIC
        """
        logger.info(
            "Checking Linked on %s, %s is True", config.NIC_NAME[1],
            config.NIC_NAME[3]
        )
        for nic_name in (config.NIC_NAME[1], config.NIC_NAME[3]):
            self.assertTrue(getVmNicLinked(config.VM_NAME[0], nic=nic_name))

        logger.info(
            "Checking Plugged on %s, %s is True", config.NIC_NAME[1],
            config.NIC_NAME[2]
        )
        for nic_name in (config.NIC_NAME[1], config.NIC_NAME[2]):
            self.assertTrue(getVmNicPlugged(config.VM_NAME[0], nic=nic_name))

        logger.info(
            "Checking Linked on %s, %s is False", config.NIC_NAME[2],
            config.NIC_NAME[4]
        )
        for nic_name in (config.NIC_NAME[2], config.NIC_NAME[4]):
            self.assertFalse(getVmNicLinked(config.VM_NAME[0], nic=nic_name))

        logger.info(
            "Checking Plugged on %s, %s is False", config.NIC_NAME[3],
            config.NIC_NAME[4]
        )
        for nic_name in (config.NIC_NAME[3], config.NIC_NAME[4]):
            self.assertFalse(getVmNicPlugged(config.VM_NAME[0], nic=nic_name))

    @classmethod
    def teardown_class(cls):
        """
        Removing the NICs and networks.
        """
        logger.info(
            "Updating all the networks beside mgmt network to be unplugged"
        )
        for nic_name in (config.NIC_NAME[1], config.NIC_NAME[2]):
            if not updateNic(True, config.VM_NAME[0], nic_name, plugged=False):
                logger.error("Couldn't unplug %s", nic_name)

        logger.info("Removing all the VNICs besides mgmt network")
        for nic in config.NIC_NAME[1:5]:
            if not removeNic(True, config.VM_NAME[0], nic):
                logger.error("Cannot remove %s from setup", nic)

        if not remove_net_from_setup(
            host=config.VDS_HOSTS[0], network=[cls.vlan_1, cls.vlan_2,
                                               cls.vlan_3, cls.vlan_4],
            mgmt_network=config.MGMT_BRIDGE, data_center=config.DC_NAME[0]
        ):
            logger.error("Cannot remove networks from setup")

########################################################################

########################################################################


@attr(tier=0)
class TestSanityCase12(TestCase):
    """
    Checking Linking Nic (bond test):
    Creating 4 networks (sw162, sw163, sw164 & sw165) and adding them to
    the host. Then creating vnics (with all permutations of plugged & linked)
    and attaching them to the vm, then:
    1. Checking that all the permutations of plugged & linked are correct
    Finally, Removing the nics and networks.
    """
    vlan_1 = config.VLAN_NETWORKS[0]
    vlan_2 = config.VLAN_NETWORKS[1]
    vlan_3 = config.VLAN_NETWORKS[2]
    vlan_4 = config.VLAN_NETWORKS[3]
    vlan_id_1 = config.VLAN_ID[0]
    vlan_id_2 = config.VLAN_ID[1]
    vlan_id_3 = config.VLAN_ID[2]
    vlan_id_4 = config.VLAN_ID[3]
    vm_nic = config.NIC_NAME[1]
    bond = config.BOND[0]

    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Creating 4 networks (sw162, sw163, sw164 & sw165) and adding them to
        the host. Then creating vnics (with all permutations of plugged
        & linked) and attaching them to the vm
        """
        logger.info("Create network and attach it to the host")
        local_dict = {
            None: {
                "nic": cls.bond, "mode": 1, "slaves": [2, 3]
            },
            cls.vlan_1: {
                "nic": cls.bond, "vlan_id": cls.vlan_id_1,
                "required": "false"
            },
            cls.vlan_2: {
                "nic": cls.bond, "vlan_id": cls.vlan_id_2,
                "required": "false"
            },
            cls.vlan_3: {
                "nic": cls.bond, "vlan_id": cls.vlan_id_3,
                "required": "false"
            },
            cls.vlan_4: {
                "nic": cls.bond, "vlan_id": cls.vlan_id_4,
                "required": "false"
            }
        }

        if not createAndAttachNetworkSN(
            data_center=config.DC_NAME[0], cluster=config.CLUSTER_NAME[0],
            host=config.VDS_HOSTS[0], network_dict=local_dict, auto_nics=[0, 1]
        ):
            raise NetworkException("Cannot create and attach network")

        logger.info("Create VNICs with different plugged/linked permutations")
        plug_link_param_list = [("true", "true"), ("true", "false"),
                                ("false", "true"), ("false", "false")]
        for nic, plug_link, net in zip(
            config.NIC_NAME[1:], plug_link_param_list, config.VLAN_NETWORKS
        ):
            if not addNic(
                True, config.VM_NAME[0], name=nic, network=net,
                plugged=plug_link[0], linked=plug_link[1]
            ):
                raise NetworkException("Cannot add nic %s to VM" % nic)

    def test_check_combination_plugged_linked_values(self):
        """
        Checking that all the permutations of plugged & linked are correct
        """
        logger.info(
            "Checking Linked on %s, %s is True", config.NIC_NAME[1],
            config.NIC_NAME[3]
        )
        for nic_name in (config.NIC_NAME[1], config.NIC_NAME[3]):
            self.assertTrue(getVmNicLinked(config.VM_NAME[0], nic=nic_name))

        logger.info(
            "Checking Plugged on %s, %s is True", config.NIC_NAME[1],
            config.NIC_NAME[2]
        )
        for nic_name in (config.NIC_NAME[1], config.NIC_NAME[2]):
            self.assertTrue(getVmNicPlugged(config.VM_NAME[0], nic=nic_name))

        logger.info(
            "Checking Linked on %s, %s is True", config.NIC_NAME[2],
            config.NIC_NAME[4]
        )
        for nic_name in (config.NIC_NAME[2], config.NIC_NAME[4]):
            self.assertFalse(getVmNicLinked(config.VM_NAME[0], nic=nic_name))

        logger.info(
            "Checking Plugged on %s, %s is True", config.NIC_NAME[4],
            config.NIC_NAME[3]
        )
        for nic_name in (config.NIC_NAME[3], config.NIC_NAME[4]):
            self.assertFalse(getVmNicPlugged(config.VM_NAME[0], nic=nic_name))

    @classmethod
    def teardown_class(cls):
        """
        Removing the nics and networks
        """
        logger.info(
            "Stopping the VM %s instead of unplugging the NIcs",
            config.VM_NAME[0]
        )
        if not vms.stopVm(True, vm=config.VM_NAME[0]):
            logger.error("Failed to stop VM: %s", config.VM_NAME[0])

        logger.info("Removing all the VNICs beside mgmt network")
        for nic in config.NIC_NAME[1:5]:
            if not removeNic(True, config.VM_NAME[0], nic):
                logger.error(
                    "Cannot remove vNIC from VM %s", config.VM_NAME[0]
                )

        logger.info("Remove networks %s from setup", config.VLAN_NETWORKS[:4])
        if not remove_net_from_setup(
            host=config.VDS_HOSTS[0], network=[cls.vlan_1, cls.vlan_2,
                                               cls.vlan_3, cls.vlan_4],
            mgmt_network=config.MGMT_BRIDGE, data_center=config.DC_NAME[0]
        ):
            logger.error("Cannot remove networks from setup")

        logger.info("Start VM %s", config.VM_NAME[0])
        if not startVm(positive=True, vm=config.VM_NAME[0], wait_for_ip=True):
            logger.error("Failed to start %s", config.VM_NAME[0])

########################################################################

########################################################################


@attr(tier=0)
class TestSanityCase13(TestCase):
    """
    Creates bridged network over bond with custom name and MTU of 5000
    Check physical and logical layers for the Bond
    Change the Bond mode
    Check again the physical and logical layers for the Bond
    """
    vlan_1 = config.VLAN_NETWORKS[0]
    vlan_id_1 = config.VLAN_ID[0]

    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Creates bridged networks on DC/Cluster/Hosts over bond with custom name
        """

        local_dict = {
            None: {
                "nic": "bond012345", "mode": 1, "slaves": [2, 3]
            },
            cls.vlan_1: {
                "nic": "bond012345", "mtu": 5000,
                "vlan_id": cls.vlan_id_1, "required": "false"
            }
        }

        if not createAndAttachNetworkSN(
            data_center=config.DC_NAME[0], cluster=config.CLUSTER_NAME[0],
            host=config.VDS_HOSTS[0], network_dict=local_dict, auto_nics=[0]
        ):
            raise NetworkException(
                "Cannot create and attach network %s over Bond", cls.vlan_1)

    @tcms(16421, 448116)
    def test_bond_mode_change(self):
        """
        Check physical and logical levels for networks with Jumbo frames
        """
        logger.info("Checking physical and logical layers for Jumbo bond ")
        logger.info("Checking logical layer of %s over bond", self.vlan_1)
        self.assertTrue(
            checkMTU(
                host=config.HOSTS_IP[0], user=config.HOSTS_USER,
                password=config.HOSTS_PW, mtu=config.MTU[1],
                physical_layer=False, network=self.vlan_1, bond="bond012345"
            )
        )
        logger.info("Checking physical layer of %s over bond ", self.vlan_1)
        self.assertTrue(
            checkMTU(
                host=config.HOSTS_IP[0], user=config.HOSTS_USER,
                password=config.HOSTS_PW, mtu=config.MTU[1],
                bond="bond012345", bond_nic1=config.VDS_HOSTS[0].nics[2],
                bond_nic2=config.VDS_HOSTS[0].nics[3]
            )
        )
        logger.info("Changing the bond mode to mode4")
        rc, out = genSNNic(
            nic="bond012345", network=self.vlan_1,
            slaves=[config.VDS_HOSTS[0].nics[2], config.VDS_HOSTS[0].nics[3]],
            mode=4
        )

        if not rc:
            raise NetworkException("Cannot generate network object")
        sendSNRequest(
            positive=True, host=HOST_NAME0, nics=[out["host_nic"]],
            auto_nics=[config.VDS_HOSTS[0].nics[0]], check_connectivity="true",
            connectivity_timeout=60, force="false"
        )
        logger.info("Checking layers after bond mode change")
        logger.info("Checking logical layer after bond mode change")
        self.assertTrue(
            checkMTU(
                host=config.HOSTS_IP[0], user=config.HOSTS_USER,
                password=config.HOSTS_PW, mtu=config.MTU[1],
                physical_layer=False, network=self.vlan_1, bond="bond012345"
            )
        )
        logger.info("Checking physical layer after bond mode change")
        self.assertTrue(
            checkMTU(
                host=config.HOSTS_IP[0], user=config.HOSTS_USER,
                password=config.HOSTS_PW, mtu=config.MTU[1], bond="bond012345",
                bond_nic1=config.VDS_HOSTS[0].nics[2],
                bond_nic2=config.VDS_HOSTS[0].nics[3]
            )
        )

    @classmethod
    def teardown_class(cls):
        """
        Remove networks from the setup
        """
        logger.info("Starting the teardown_class")
        if not remove_net_from_setup(
            host=config.VDS_HOSTS[0], network=[cls.vlan_1],
            mgmt_network=config.MGMT_BRIDGE, data_center=config.DC_NAME[0]
        ):
            logger.error("Cannot remove network from setup")


@attr(tier=0)
class TestSanityCase14(TestCase):
    """
    Negative: Try to create Bond with exceeded name length (more than 15 chars)
    """
    vlan_1 = config.VLAN_NETWORKS[0]
    vlan_id_1 = config.VLAN_ID[0]

    __test__ = True

    @tcms(16421, 448117)
    def test_bond_max_length(self):
        """
        Create BOND: exceed allowed length (max 15 chars)
        """
        logger.info("Generating bond012345678901 object with 2 NIC")
        net_obj = []
        rc, out = genSNNic(
            nic="bond012345678901", slaves=[config.VDS_HOSTS[0].nics[2],
                                            config.VDS_HOSTS[0].nics[3]]
        )
        if not rc:
            raise NetworkException("Cannot generate SNNIC object")

        net_obj.append(out["host_nic"])

        logger.info("sending SNRequest for bond012345678901")
        self.assertTrue(
            sendSNRequest(
                False, host=HOST_NAME0, nics=net_obj,
                auto_nics=[config.VDS_HOSTS[0].nics[0]],
                check_connectivity="true", connectivity_timeout=config.TIMEOUT,
                force="false"
            )
        )


@attr(tier=0)
class TestSanityCase15(TestCase):
    """
    Negative:  Try to create bond with wrong prefix
    """
    vlan_1 = config.VLAN_NETWORKS[0]
    vlan_id_1 = config.VLAN_ID[0]

    __test__ = True

    @tcms(16421, 448117)
    def test_bond_prefix(self):
        """
        Create BOND: use wrong prefix (eg. NET1515)
        """
        logger.info("Generating NET1515 object with 2 NIC bond")
        net_obj = []
        rc, out = genSNNic(
            nic="NET1515", slaves=[config.VDS_HOSTS[0].nics[2],
                                   config.VDS_HOSTS[0].nics[3]]
        )
        if not rc:
            raise NetworkException("Cannot generate NIC object")

        net_obj.append(out["host_nic"])

        logger.info("sending SNRequest: NET1515")
        self.assertTrue(
            sendSNRequest(
                False, host=HOST_NAME0, nics=net_obj,
                auto_nics=[config.VDS_HOSTS[0].nics[0]],
                check_connectivity="true", connectivity_timeout=config.TIMEOUT,
                force="false"
            )
        )


@attr(tier=0)
class TestSanityCase16(TestCase):
    """
    Negative: Try to create bond with wrong suffix
    """
    vlan_1 = config.VLAN_NETWORKS[0]
    vlan_id_1 = config.VLAN_ID[0]

    __test__ = True

    @tcms(16421, 448117)
    def test_bond_suffix(self):
        """
        Create BOND: use wrong suffix (e.g. bond1!)
        """
        logger.info("Generating bond1! object with 2 NIC bond")
        net_obj = []
        rc, out = genSNNic(
            nic="bond1!",  slaves=[config.VDS_HOSTS[0].nics[2],
                                   config.VDS_HOSTS[0].nics[3]]
        )
        if not rc:
            raise NetworkException("Cannot generate NIC object")

        net_obj.append(out["host_nic"])

        logger.info("sending SNRequest: bond1!")
        self.assertTrue(
            sendSNRequest(
                False, host=HOST_NAME0, nics=net_obj,
                auto_nics=[config.VDS_HOSTS[0].nics[0]],
                check_connectivity="true", connectivity_timeout=config.TIMEOUT,
                force="false"
            )
        )


@attr(tier=0)
class TestSanityCase17(TestCase):
    """
    Negative: Try to create bond with empty name
    """
    vlan_1 = config.VLAN_NETWORKS[0]
    vlan_id_1 = config.VLAN_ID[0]

    __test__ = True

    @tcms(16421, 448117)
    def test_bond_empty(self):
        """
        Create BOND: leave name field empty
        """
        logger.info("Generating bond object with 2 NIC bond and empty name")
        net_obj = []
        rc, out = genSNNic(nic="", slaves=[config.VDS_HOSTS[0].nics[2],
                                           config.VDS_HOSTS[0].nics[3]])
        if not rc:
            raise NetworkException("Cannot generate NIC object")
        net_obj.append(out["host_nic"])

        logger.info("sending SNRequest: empty bond name")
        self.assertTrue(
            sendSNRequest(
                False, host=HOST_NAME0, nics=net_obj,
                auto_nics=[config.VDS_HOSTS[0].nics[0]],
                check_connectivity="true", connectivity_timeout=config.TIMEOUT,
                force="false"
            )
        )


@attr(tier=0)
class TestSanityCase18(TestCase):
    """
    Invalid vs valid mac address ranges
    """
    __test__ = True
    engine_default_mac_range = []

    @classmethod
    def setup_class(cls):
        """
        Get default MAC range from engine
        """
        logger.info("Get engine default MAC pool range")
        cls.engine_default_mac_range.append(
            get_engine_properties(config.ENGINE, [
                config.MAC_POOL_RANGE_CMD
            ]
            )[0])

    @tcms(16421, 448119)
    def test_big_range_mac_pool(self):

        """
        set valid and invalid MAC pool ranges
        """

        macs_list_not_valid = ["FF:00:00:00:00:00-FF:00:00:00:00:01"]
        macs_list_valid = [
            "00:00:00:00:00:00-00:00:00:00:00:01,"
            "00:00:00:00:00:00-00:00:00:00:00:01",
            "00:00:00:00:00:00-00:00:00:10:00:00,"
            "00:00:00:02:00:00-00:03:00:00:00:00",
            "00:00:00:00:00:00-00:00:00:10:00:00,"
            "00:00:00:02:00:00-00:03:00:00:00:0a",
            "00:00:00:00:00:00-00:00:00:10:00:00,"
            "00:00:00:02:00:00-00:03:00:00:00:0A",
            "FF:00:00:00:00:00-FF:00:00:00:00:01,"
            "F0:00:00:00:00:00-F0:00:00:00:00:01",
            "FF:00:00:00:00:00-FF:00:00:00:00:01,"
            "00:00:00:00:00:00-00:00:00:00:00:01"
        ]

        logger.info("Check valid MAC range")
        for mac in macs_list_valid:
            logger.info("Setting valid MAC range: %s", mac)
            cmd = "=".join([config.MAC_POOL_RANGE_CMD, mac])
            if not set_engine_properties(config.ENGINE, [cmd], restart=False):
                raise NetworkException("Failed to set MAC range: %s" % mac)
        logger.info("Check invalid MAC range")
        for mac in macs_list_not_valid:
            logger.info("Setting invalid MAC range: %s", mac)
            cmd = "=".join([config.MAC_POOL_RANGE_CMD, mac])
            if set_engine_properties(config.ENGINE, [cmd], restart=False):
                raise NetworkException(
                    "Succeeded to set MAC range: %s. but shouldn't" % mac
                )

    @classmethod
    def teardown_class(cls):
        """
        Set default MAC range and MAC count and Remove the VM
        """
        logger.info("Setting engine MacPoolRange to default")
        cmd = "=".join(
            [config.MAC_POOL_RANGE_CMD, cls.engine_default_mac_range[0]]
        )
        if not set_engine_properties(config.ENGINE, [cmd], restart=False):
            logger.error(
                "Failed to set MAC: %s", cls.engine_default_mac_range[0]
            )


@attr(tier=0)
class TestSanityCase19(TestCase):
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
            "ethtool_opts": config.TX_CHECKSUM.format(
                nic=HOST_NICS[1], state="off"
            ), "bridge_opts": config.PRIORITY
        }
        network_param_dict = {
            "nic": 1, "required": "false", "properties": prop_dict
        }

        local_dict = {config.NETWORKS[0]: network_param_dict}
        logger.info(
            "Create logical VM network %s on DC/Cluster/Host with ethtool_opts"
            " and bridge_opts having non-default values", config.NETWORKS[0]
        )
        if not createAndAttachNetworkSN(
            data_center=config.DC_NAME[0], cluster=config.CLUSTER_NAME[0],
            host=config.VDS_HOSTS[0], network_dict=local_dict, auto_nics=[0]
        ):
            raise NetworkException(
                "Cannot create and attach network %s" % config.NETWORKS[0]
            )

    @tcms(16421, 448120)
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
        if not check_ethtool_opts(
            config.HOSTS_IP[0], config.HOSTS_USER, config.HOSTS_PW,
            HOST_NICS[1], "tx-checksumming", "off"
        ):
            raise NetworkException(
                "tx-checksum value of ethtool_opts was not updated correctly "
                "with non-default value"
            )

        logger.info(
            "Check that bridge_opts parameter for priority have an updated "
            "non-default value"
        )
        if not check_bridge_opts(
            config.HOSTS_IP[0], config.HOSTS_USER, config.HOSTS_PW,
            config.NETWORKS[0], config.KEY1, config.BRIDGE_OPTS.get(
                config.KEY1
            )[1]
        ):
            raise NetworkException(
                "Priority value of bridge_opts was not updated correctly "
                "with non-default value"
            )

        logger.info(
            "Update ethtool_opts for tx_checksum and bridge_opts for priority "
            "with the default parameters"
        )
        kwargs = {
            "properties": {"ethtool_opts": config.TX_CHECKSUM.format(
                nic=HOST_NICS[1], state="on"
            ), "bridge_opts": config.DEFAULT_PRIORITY}
        }
        if not update_network_host(
            HOST_NAME0, HOST_NICS[1], auto_nics=[HOST_NICS[0]], **kwargs
        ):
            raise NetworkException(
                "Couldn't update ethtool and bridge_opts with default "
                "parameters for tx_checksum and priority opts"
            )

        logger.info(
            "Check that ethtool_opts parameter has an updated default value"
        )
        if not check_ethtool_opts(
            config.HOSTS_IP[0], config.HOSTS_USER, config.HOSTS_PW,
            HOST_NICS[1], "tx-checksumming", "on"
        ):
            raise NetworkException(
                "tx-checksum value of ethtool_opts was not updated correctly "
                "with default value"
            )

        logger.info(
            "Check that bridge_opts parameter has an updated default value"
        )
        if not check_bridge_opts(
            config.HOSTS_IP[0], config.HOSTS_USER, config.HOSTS_PW,
            config.NETWORKS[0], config.KEY1, config.BRIDGE_OPTS.get(
                config.KEY1
            )[0]
        ):
            raise NetworkException(
                "Priority value of bridge opts was not updated correctly with "
                "default value"
            )

    @classmethod
    def teardown_class(cls):
        """
        Remove networks from the setup.
        """
        if not remove_net_from_setup(
            host=config.VDS_HOSTS[0], data_center=config.DC_NAME[0],
            all_net=True, mgmt_network=config.MGMT_BRIDGE
        ):
            logger.error("Cannot remove networks from setup")


@attr(tier=0)
class TestSanityCase20(TestCase):
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
        logger.info("Stopping %s", config.VM_NAME[0])
        if not stopVm(positive=True, vm=config.VM_NAME[0]):
            raise NetworkException("Fail to stop %s" % config.VM_NAME[0])

        logger.info(
            "Update custom properties on %s to %s", config.MGMT_BRIDGE,
            config.PROP_QUEUES[0]
        )
        if not updateVnicProfile(
            name=config.MGMT_BRIDGE, network=config.MGMT_BRIDGE,
            data_center=config.DC_NAME[0],
            custom_properties=config.PROP_QUEUES[0]
        ):
            raise NetworkException(
                "Failed to set custom properties on %s" % config.MGMT_BRIDGE
            )
        logger.info("Start %s on %s", config.VM_NAME[0], HOST_NAME0)
        if not startVm(
            positive=True, vm=config.VM_NAME[0], wait_for_ip=True,
            placement_host=HOST_NAME0
        ):
            raise NetworkException(
                "Failed to start %s on %s" % (
                    config.VM_NAME[0], HOST_NAME0
                )
            )

    @tcms(16421, 448121)
    def test_multiple_queue_nics(self):
        """
        Check that qemu has correct number of queues
        """
        logger.info("Check that qemu have %s queues", config.NUM_QUEUES[0])
        if not check_queues_from_qemu(
            host_obj=config.VDS_HOSTS[0], num_queues=config.NUM_QUEUES[0]
        ):
            raise NetworkException(
                "qemu did not return the expected number of queues"
            )

    @classmethod
    def teardown_class(cls):
        """
        Remove custom properties for mgmt network
        """
        logger.info(
            "Remove custom properties on %s", config.MGMT_BRIDGE
        )
        if not updateVnicProfile(
            name=config.MGMT_BRIDGE, network=config.MGMT_BRIDGE,
            data_center=config.DC_NAME[0], custom_properties="clear"
        ):
            logger.error(
                "Failed to set custom properties on %s", config.MGMT_BRIDGE
            )
        logger.info("Restart VM")
        if not stopVm(positive=True, vm=config.VM_NAME[0]):
            logger.error("Failed to stop VM %s", config.VM_NAME[0])
        logger.info("Start %s on %s", config.VM_NAME[0], HOST_NAME0)
        if not startVm(
            positive=True, vm=config.VM_NAME[0], wait_for_ip=True,
            placement_host=HOST_NAME0
        ):
            logger.error(
                "Failed to start %s on %s", config.VM_NAME[0], HOST_NAME0
            )


@attr(tier=0)
class TestSanityCase21(TestCase):
    """
    List all networks under datacenter.
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Create networks under 2 datacenters.
        """
        if not addDataCenter(
            positive=True, name=config.EXTRA_DC,
            storage_type=config.STORAGE_TYPE, version=config.COMP_VERSION
        ):
            raise NetworkException("Failed to add DC %s" % config.EXTRA_DC)

        logger.info("Create 10 networks under %s", DC_NAMES[0])
        if not create_networks_in_datacenter(DC_NAMES[0], 10, "dc1_net"):
            raise NetworkException(
                "Fail to create 10 network on %s" % DC_NAMES[0]
            )
        logger.info("Create 5 networks under %s", config.EXTRA_DC)
        if not create_networks_in_datacenter(config.EXTRA_DC, 5, "dc2_net"):
            raise NetworkException(
                "Fail to create 5 network on %s" % config.EXTRA_DC
            )

    @tcms(16421, 448122)
    def test_get_networks_list(self):
        """
        Get all networks under the datacenter.
        """
        logger.info("Checking that all networks exist in the datacenters")
        dc1_net_list = ["_".join(["dc1_net", str(i)]) for i in xrange(10)]
        engine_dc_net_list = get_networks_in_datacenter(DC_NAMES[0])
        for net in dc1_net_list:
            if net not in [i.name for i in engine_dc_net_list]:
                raise NetworkException(
                    "%s was expected to be in %s" % (net, DC_NAMES[0])
                )
        dc2_net_list = ["_".join(["dc2_net", str(i)]) for i in xrange(5)]
        engine_extra_dc_net_list = get_networks_in_datacenter(config.EXTRA_DC)
        for net in dc2_net_list:
            if net not in [i.name for i in engine_extra_dc_net_list]:
                raise NetworkException(
                    "%s was expected to be in %s" % (net, config.EXTRA_DC)
                )

    @classmethod
    def teardown_class(cls):
        """
        Remove extra DC from setup
        Remove networks from the setup.
        """
        if not removeDataCenter(positive=True, datacenter=config.EXTRA_DC):
            logger.error("Cannot remove DC")

        logger.info("Remove all networks from %s", config.DC_NAME[0])
        if not delete_networks_in_datacenter(
            config.DC_NAME[0], config.MGMT_BRIDGE
        ):
            logger.error(
                "Fail to delete all networks from %s", config.DC_NAME[0]
            )


@attr(tier=0)
class TestSanityCase22(TestCase):
    """
    Update VM network to be non-VM network
    Update non-VM network to be VM network
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Create and attach network on DC, Cluster and the host
        """

        dict_dc1 = {
            config.NETWORKS[0]: {"nic": 1,  "required": "false"}
        }

        logger.info("Attach network to DC/Cluster/Host")
        if not createAndAttachNetworkSN(
            data_center=config.DC_NAME[0], cluster=config.CLUSTER_NAME[0],
            host=config.VDS_HOSTS[0], network_dict=dict_dc1, auto_nics=[0]
        ):
            raise NetworkException("Cannot create and attach network")

    @tcms(16421, 448125)
    def test_update_with_non_vm_nonvm(self):
        """
        1) Update network to be non-VM network
        2) Check that the Host was updated accordingly
        3) Update network to be VM network
        4) Check that the Host was updated accordingly
        """
        bridge_dict1 = {"bridge": False}
        bridge_dict2 = {"bridge": True}

        logger.info(
            "Update network %s to be non-VM network", config.NETWORKS[0]
        )
        if not updateNetwork(
            True, network=config.NETWORKS[0], data_center=config.DC_NAME[0],
            usages=""
        ):
            raise NetworkException(
                "Cannot update network to be non-VM network"
            )

        logger.info("Wait till the Host is updated with the change")
        sample1 = TimeoutingSampler(
            timeout=config.SAMPLER_TIMEOUT, sleep=1,
            func=checkHostNicParameters, host=HOST_NAME0,
            nic=HOST_NICS[1], **bridge_dict1
        )
        if not sample1.waitForFuncStatus(result=True):
            raise NetworkException(
                "Network is VM network and should be Non-VM"
            )

        logger.info("Check that the change is reflected to Host")
        if isVmHostNetwork(
            host=config.HOSTS_IP[0], user=config.HOSTS_USER,
            password=config.HOSTS_PW, net_name=config.NETWORKS[0],
            conn_timeout=45
        ):
            raise NetworkException(
                "Network on host %s was not updated to be non-VM network" %
                HOST_NAME0
            )

        logger.info("Update network %s to be VM network", config.NETWORKS[0])
        if not updateNetwork(
            True, network=config.NETWORKS[0], data_center=config.DC_NAME[0],
            usages="vm"
        ):
            raise NetworkException("Cannot update network to be VM network")

        logger.info("Wait till the Host is updated with the change")
        sample2 = TimeoutingSampler(
            timeout=config.SAMPLER_TIMEOUT, sleep=1,
            func=checkHostNicParameters, host=HOST_NAME0,
            nic=HOST_NICS[1], **bridge_dict2
        )
        if not sample2.waitForFuncStatus(result=True):
            raise NetworkException("Network is not a VM network but should be")

        logger.info("Check that the change is reflected to Host")
        if not isVmHostNetwork(
            host=config.HOSTS_IP[0], user=config.HOSTS_USER,
            password=config.HOSTS_PW, net_name=config.NETWORKS[0]
        ):
            raise NetworkException(
                "Network on host %s was not updated to be VM network" %
                HOST_NAME0
            )

    @classmethod
    def teardown_class(cls):
        """
        Remove network from the setup.
        """
        logger.info("Remove network from setup")
        if not remove_net_from_setup(
            host=config.VDS_HOSTS[0], network=[config.NETWORKS[0]],
            mgmt_network=config.MGMT_BRIDGE, data_center=config.DC_NAME[0]
        ):
            logger.error("Cannot remove network from setup")


@attr(tier=0)
class TestSanityCase23(TestCase):
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
            config.VLAN_NETWORKS[0]: {
                "nic": 1, "vlan_id": config.VLAN_ID[0],
                "required": False, "bootproto": "static",
                "address": [config.MG_IP_ADDR], "netmask": [config.NETMASK],
                "gateway": [config.MG_GATEWAY]
            }
        }

        if not createAndAttachNetworkSN(
            data_center=config.DC_NAME[0], cluster=config.CLUSTER_NAME[0],
            host=config.VDS_HOSTS[0], network_dict=local_dict,
            auto_nics=[0, 1]
        ):
            raise NetworkException(
                "Cannot create and attach network %s" % config.NETWORKS[0]
            )

    @tcms(16421, 448126)
    def test_check_ip_rule(self):
        """
        Check correct configuration with ip rule function
        """
        self.assertTrue(checkIPRule(
            config.HOSTS_IP[0], user=config.HOSTS_USER,
            password=config.HOSTS_PW, subnet=config.SUBNET)
        )

    @classmethod
    def teardown_class(cls):
        """
        Remove network from the setup.
        """
        logger.info("Remove network %s from setup", config.VLAN_NETWORKS[0])
        if not remove_net_from_setup(
            host=config.VDS_HOSTS[0], network=[config.VLAN_NETWORKS[0]],
            mgmt_network=config.MGMT_BRIDGE, data_center=config.DC_NAME[0]
        ):
            logger.error(
                "Cannot remove network %s from setup", config.VLAN_NETWORKS[0]
            )


@attr(tier=0)
class TestSanityCase24(TestCase):
    """
    1) Put label on Host NIC of one Host
    2) Check network is attached to Host
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Create a network and attach it to DC and Cluster
        Create Bond on the second Host
        """
        local_dict = {config.NETWORKS[0]: {"required": "false"}}
        logger.info(
            "Create and attach network %s to DC and Cluster ",
            config.NETWORKS[0]
        )

        if not createAndAttachNetworkSN(
            data_center=config.DC_NAME[0], cluster=config.CLUSTER_NAME[0],
            network_dict=local_dict
        ):
            raise NetworkException(
                "Cannot create network %s on DC and Cluster" %
                config.NETWORKS[0]
            )

    @tcms(16421, 448127)
    def test_label_several_interfaces(self):
        """
        1) Put label on Host NIC
        2) Put label on the network
        3) Check network is attached to Host
        """
        logger.info(
            "Attach label %s to Host NIC %s and to the network %s",
            config.LABEL_LIST[0], HOST_NICS[1], config.NETWORKS[0]
        )

        if not add_label(
            label=config.LABEL_LIST[0], host_nic_dict={
                HOST_NAME0: [HOST_NICS[1]]
            }, networks=[config.NETWORKS[0]]
        ):
            raise NetworkException(
                "Couldn't attach label %s " % config.LABEL_LIST[0]
            )

        logger.info(
            "Check network %s is attached to interface %s on Host %s",
            config.NETWORKS[0], HOST_NICS[1], HOST_NAME0
        )
        if not check_network_on_nic(
            config.NETWORKS[0], HOST_NAME0, HOST_NICS[1]
        ):
            raise NetworkException(
                "Network %s is not attached to NIC %s " %
                (config.NETWORKS[0], HOST_NICS[1])
            )

    @classmethod
    def teardown_class(cls):
        """
        Remove label from the NIC
        Remove network from setup
        """
        logger.info("Removing label from %s", HOST_NICS[1])
        if not remove_label(host_nic_dict={HOST_NAME0: [HOST_NICS[1]]}):
            logger.error("Couldn't remove labels from %s", HOST_NICS[1])

        if not remove_net_from_setup(
            host=config.VDS_HOSTS, data_center=config.DC_NAME[0],
            mgmt_network=config.MGMT_BRIDGE, all_net=True
        ):
            logger.error("Cannot remove network from setup")


@attr(tier=0)
class TestSanityCase25(TestCase):
    """
    Add new network QOS
    """
    __test__ = True
    BW_PARAMS = (10, 10, 100)
    QOS_NAME = "QoSProfile1"
    QOS_TYPE = "network"

    @tcms(16421, 448128)
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
        if not add_qos_to_datacenter(
            datacenter=config.DC_NAME[0],
            qos_name=self.QOS_NAME, qos_type=self.QOS_TYPE,
            inbound_average=self.BW_PARAMS[0], inbound_peak=self.BW_PARAMS[1],
            inbound_burst=self.BW_PARAMS[2],
            outbound_average=self.BW_PARAMS[0],
            outbound_peak=self.BW_PARAMS[1],
            outbound_burst=self.BW_PARAMS[2]
        ):
            raise NetworkException(
                "Couldn't create Network QOS under DC"
            )
        logger.info(
            "Create VNIC profile with QoS and add it to the VNIC"
        )
        add_qos_profile_to_nic()
        inbound_dict = {"average": self.BW_PARAMS[0],
                        "peak": self.BW_PARAMS[1],
                        "burst": self.BW_PARAMS[2]}
        outbound_dict = {"average": self.BW_PARAMS[0],
                         "peak": self.BW_PARAMS[1],
                         "burst": self.BW_PARAMS[2]}

        dict_compare = build_dict(
            inbound_dict=inbound_dict, outbound_dict=outbound_dict,
            vm=config.VM_NAME[0], nic=config.NIC_NAME[1]
        )

        logger.info(
            "Compare provided QoS %s and %s exists with libvirt values",
            inbound_dict, outbound_dict
        )
        if not compare_qos(
            host_obj=config.VDS_HOSTS[0], vm_name=config.VM_NAME[0],
            **dict_compare
        ):
            raise NetworkException(
                "Provided QoS values %s and %s are not equal to what was "
                "found on libvirt" % (inbound_dict, outbound_dict)
            )

    @classmethod
    def teardown_class(cls):
        """
        1) Remove VNIC from VM.
        2) Remove VNIC profile
        3) Remove Network QoS
        """
        try:
            logger.info(
                "Remove VNIC from VM %s", config.VM_NAME[0]
            )
            if not updateNic(
                True, config.VM_NAME[0], config.NIC_NAME[1], plugged='false'
            ):
                logger.error("Couldn't unplug NIC %s", config.NIC_NAME[1])

            if not removeNic(
                True, config.VM_NAME[0], config.NIC_NAME[1]
            ):
                logger.error(
                    "Couldn't remove VNIC from VM %s", config.VM_NAME[0]
                )
        except EntityNotFound:
            logger.error(
                "Couldn't remove %s from %s", config.NIC_NAME[1],
                config.VM_NAME[0]
            )
        logger.info(
            "Remove VNIC profile %s", config.VNIC_PROFILE[0]
        )
        if not removeVnicProfile(
            positive=True, vnic_profile_name=config.VNIC_PROFILE[0],
            network=config.MGMT_BRIDGE, data_center=config.DC_NAME[0]
        ):
            logger.error(
                "Couldn't remove VNIC profile %s", config.VNIC_PROFILE[0]
            )
        if not delete_qos_from_datacenter(
            config.DC_NAME[0], cls.QOS_NAME
        ):
            logger.error(
                "Couldn't delete the QoS %s from DC %s",
                cls.QOS_NAME, config.DC_NAME[0]
            )


@attr(tier=0)
class TestSanityCase26(TestCase):
    """
    Negative: Create more than 5 BONDS using dummy interfaces
    """
    apis = set(["rest"])
    vlan_1 = config.VLAN_NETWORKS[0]
    vlan_id_1 = config.VLAN_ID[0]

    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Create dummy interface for BONDS
        """
        logger.info("Creating 20 dummy interfaces")
        if not create_dummy_interfaces(
            host=config.HOSTS_IP[0], username=config.HOSTS_USER,
            password=config.HOSTS_PW, num_dummy=20
        ):
            raise NetworkException("Failed to create dummy interfaces")

        logger.info("Refresh host capabilities")
        host_obj = HOST_API.find(config.HOSTS[0])
        refresh_href = "{0};force".format(host_obj.get_href())
        HOST_API.get(href=refresh_href)

        logger.info("Check if dummy0 exist on host via engine")
        sample = TimeoutingSampler(
            timeout=config.SAMPLER_TIMEOUT, sleep=1,
            func=check_dummy_on_host_interfaces, dummy_name="dummy0"
        )
        if not sample.waitForFuncStatus(result=True):
            raise NetworkException("Dummy interface not exists on engine")

    @tcms(16421, 448118)
    def test_dummy_bonds(self):
        """
        Create 10 BONDS using dummy interfaces
        """
        logger.info("Generating bond object with 2 dummy interfaces")
        net_obj = []
        idx = 0
        while idx < 20:
            rc, out = genSNNic(
                nic="bond%s" % idx, slaves=[
                    "dummy%s" % idx, "dummy%s" % (idx + 1)
                ]
            )
            if not rc:
                raise NetworkException("Cannot generate NIC object")

            net_obj.append(out["host_nic"])
            idx += 2

        logger.info("sending SNRequest: 10 bonds on dummy interfaces")
        if not sendSNRequest(
            True, host=HOST_NAME0, nics=net_obj,
            auto_nics=[config.VDS_HOSTS[0].nics[0]],
            check_connectivity="true", connectivity_timeout=config.TIMEOUT,
            force="false"
        ):
            raise NetworkException("Failed to SNRequest")

    @classmethod
    def teardown_class(cls):
        """
        Delete all bonds and dummy interfaces
        """
        logger.info("Delete all dummy interfaces")
        if not delete_dummy_interfaces(
            host=config.HOSTS_IP[0], username=config.HOSTS_USER,
            password=config.HOSTS_PW
        ):
            logger.error("Failed to delete dummy interfaces")

        logger.info("Refresh host capabilities")
        host_obj = HOST_API.find(config.HOSTS[0])
        refresh_href = "{0};force".format(host_obj.get_href())
        HOST_API.get(href=refresh_href)

        logger.info("CHeck if dummy0 not exist on host via engine")
        sample = TimeoutingSampler(
            timeout=config.SAMPLER_TIMEOUT, sleep=1,
            func=check_dummy_on_host_interfaces, dummy_name="dummy0"
        )
        if not sample.waitForFuncStatus(result=False):
            logger.error("Dummy interface exists on engine")
