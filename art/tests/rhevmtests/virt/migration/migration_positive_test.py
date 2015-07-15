#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Testing network migration feature.
1 DC, 1 Cluster, 2 Hosts and 1 VM will be created for testing.
Network migration will be tested for untagged, tagged, bond scenarios.
It will cover scenarios for VM/non-VM networks
"""
import logging

from rhevmtests.networking import config
from art.unittest_lib import attr
from art.rhevm_api.tests_lib.low_level import vms
from art.unittest_lib import VirtTest as TestCase
from art.test_handler.tools import polarion  # pylint: disable=E0611
from art.test_handler.exceptions import NetworkException
from art.rhevm_api.tests_lib.low_level.networks import updateClusterNetwork
from rhevmtests.networking.helper import create_random_ips
from art.rhevm_api.tests_lib.low_level.vms import (
    addNic, removeNic, updateNic, run_vms_once
)
from rhevmtests.virt.migration.helper import (
    dedicated_migration, migrate_unplug_required,
    get_origin_host
)
from art.rhevm_api.tests_lib.high_level.networks import (
    createAndAttachNetworkSN, remove_net_from_setup
)


logger = logging.getLogger("Virt_Network_Migration_Cases")

NETMASK = "255.255.0.0"

# #######################################################################

########################################################################
#                             Test Cases                               #
########################################################################


class TestMigrationCaseBase(TestCase):
    """
    base class which provides  teardown class method for each test case
    """

    @classmethod
    def teardown_class(cls):
        """
        Remove networks from the setup.
        """
        if not remove_net_from_setup(
            host=config.VDS_HOSTS, auto_nics=[0],
            data_center=config.DC_NAME[0], mgmt_network=config.MGMT_BRIDGE,
            all_net=True
        ):
            logger.error("Cannot remove networks from setup")


@attr(tier=0)
class TestMigrationCase01(TestMigrationCaseBase):
    """
    Verify dedicated regular network migration, migration 5 VMs
    """
    __test__ = True
    vms = config.VM_NAME[1:5]

    @classmethod
    def setup_class(cls):
        """
        Create logical vm network on DC/Cluster/Hosts
        Configure it as migration network
        Start 4 more VMs
        """
        ips = create_random_ips()
        local_dict = {
            config.NETWORKS[0]: {
                "nic": 1, "required": "true", "cluster_usages": "migration",
                "bootproto": "static", "address": [ips[0], ips[1]],
                "netmask": [NETMASK, NETMASK]
            },
            config.NETWORKS[1]: {
                "nic": 2, "required": "true"
            }
        }
        logger.info(
            "Configure migration VM network %s on DC/Cluster and Host ",
            config.NETWORKS[0]
        )
        if not createAndAttachNetworkSN(
            data_center=config.DC_NAME[0], cluster=config.CLUSTER_NAME[0],
            host=config.VDS_HOSTS[:2], network_dict=local_dict,
            auto_nics=[0]
        ):
            raise NetworkException(
                "Cannot create and attach network %s" % config.NETWORKS[0]
            )

        host_for_vms = get_origin_host(config.VM_NAME[0])[1]
        logger.info("Starting: %s on %s", cls.vms, host_for_vms)
        vms_kwargs = {"host": host_for_vms}
        run_vms_once(vms=cls.vms, **vms_kwargs)

    @polarion("RHEVM3-3847")
    def test_a1_dedicated_migration(self):
        """
        Check dedicated network migration for 5 VMs
        """
        logger.info(
            "Check that network migration for 5 VMs"
            "over NIC is working as expected"
        )
        dedicated_migration(vms=config.VM_NAME[:5])

    @polarion("RHEVM3-3878")
    def test_a2_dedicated_migration_nic(self):
        """
        Check dedicated network migration for 5 VMs
        by putting req net down
        """
        logger.info(
            "Check that network migration for 5 VMs"
            "over NIC is working as expected by "
            "putting NIC with required network down"
        )
        migrate_unplug_required(vms=config.VM_NAME[:5])

    def test_a3_dedicated_migration_maintenance(self):
        """
        Check dedicated network migration for 5 VMs
        by putting host into maintenance
        """
        logger.info(
            "Check that network migration for 5 VMs "
            "over NIC is working as "
            "expected by putting the host into maintenance"
        )
        dedicated_migration(vms=config.VM_NAME[:5], maintenance=True)

    @classmethod
    def teardown_class(cls):
        """
        Stopping the extra 4 VMs
        """
        logger.info("Stopping: %s", config.VM_NAME[1:5])
        try:
            vms.stop_vms_safely(vms_list=cls.vms)
        except Exception:
            logger.error("Failed to stop %s", cls.vms)
        super(TestMigrationCase01, cls).teardown_class()


@attr(tier=1)
class TestMigrationCase02(TestMigrationCaseBase):
    """
    Verify default migration when no migration network specified
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Create logical vm network on DC/Cluster/Hosts
        """
        ips = create_random_ips()
        logger.info(
            "Create non-migration network %s on DC/Cluster/Hosts",
            config.NETWORKS[0]
        )
        local_dict = {
            config.NETWORKS[0]: {
                "nic": 1, "required": "true", "bootproto": "static",
                "address": [ips[0], ips[1]], "netmask": [NETMASK, NETMASK]
            }
        }

        if not createAndAttachNetworkSN(
            data_center=config.DC_NAME[0], cluster=config.CLUSTER_NAME[0],
            host=config.VDS_HOSTS[:2], network_dict=local_dict, auto_nics=[0]
        ):
            raise NetworkException(
                "Cannot create and attach network %s" % config.NETWORKS[0]
            )

    @polarion("RHEVM3-3846")
    def test_default_migration(self):
        """
        Check default migration on mgmt network network
        """
        logger.info("Check migration over MGMT network")
        dedicated_migration(vms=[config.VM_NAME[0]], nic_index=0)


@attr(tier=1)
class TestMigrationCase03(TestMigrationCaseBase):
    """
    Verify dedicated migration over tagged network over NIC
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Create logical tagged vm network on DC/Cluster/Hosts
        """
        logger.info(
            "Create logical tagged vm network %s on DC/Cluster/Hosts",
            config.VLAN_NETWORKS[0]
        )
        ips = create_random_ips()
        local_dict = {
            config.VLAN_NETWORKS[0]: {
                "vlan_id": config.VLAN_ID[0], "nic": 1, "required": "true",
                "cluster_usages": "migration", "bootproto": "static",
                "address": [ips[0], ips[1]], "netmask": [NETMASK, NETMASK]
            },
            config.VLAN_NETWORKS[1]: {
                "vlan_id": config.VLAN_ID[1], "nic": 2, "required": "true"
            }
        }
        if not createAndAttachNetworkSN(
            data_center=config.DC_NAME[0], cluster=config.CLUSTER_NAME[0],
            host=config.VDS_HOSTS[:2], network_dict=local_dict,
            auto_nics=[0, 1, 2]
        ):
            raise NetworkException(
                "Cannot create and attach network %s" % config.VLAN_NETWORKS[0]
            )

    @polarion("RHEVM3-3851")
    def test_dedicated_tagged_migration(self):
        """
        Check dedicated migration over tagged network over NIC
        """
        logger.info(
            "Check that VLAN network migration over NIC is working as expected"
        )
        dedicated_migration(vms=[config.VM_NAME[0]], vlan=config.VLAN_ID[0])


@attr(tier=1)
class TestMigrationCase04(TestMigrationCaseBase):
    """
    Verify dedicated migration over non-VM network over NIC
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Create logical non-vm network on DC/Cluster/Hosts
        """
        logger.info(
            "Create logical non-vm network %s on DC/Cluster/Hosts",
            config.NETWORKS[0]
        )
        ips = create_random_ips()
        local_dict = {
            config.NETWORKS[0]: {
                "nic": 1, "required": "true", "usages": "",
                "cluster_usages": "migration", "bootproto": "static",
                "address": [ips[0], ips[1]], "netmask": [NETMASK, NETMASK]
            },
            config.NETWORKS[1]: {
                "nic": 2, "required": "true"
            }
        }
        if not createAndAttachNetworkSN(
            data_center=config.DC_NAME[0], cluster=config.CLUSTER_NAME[0],
            host=config.VDS_HOSTS[:2], network_dict=local_dict, auto_nics=[0]
        ):
            raise NetworkException(
                "Cannot create and attach network %s" % config.NETWORKS[0]
            )

    @polarion("RHEVM3-3849")
    def test_nonvm_migration(self):
        """
        Check dedicated migration over non-VM network over NIC
        """
        logger.info(
            "Check that non-VM network migration over NIC is working as "
            "expected"
        )
        dedicated_migration(vms=[config.VM_NAME[0]])


@attr(tier=1)
class TestMigrationCase05(TestMigrationCaseBase):
    """
    Verify dedicated regular network migration when its also display network
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Create logical vm network on DC/Cluster/Hosts
        Configure it as migration and display network
        """
        logger.info(
            "Create migration and display vm network %s on "
            "DC/Cluster/Hosts", config.NETWORKS[0]
        )
        ips = create_random_ips()
        local_dict = {
            config.NETWORKS[0]: {
                "nic": 1, "required": "true",
                "cluster_usages": "migration,display", "bootproto": "static",
                "address": [ips[0], ips[1]], "netmask": [NETMASK, NETMASK]
            },
            config.NETWORKS[1]: {
                "nic": 2, "required": "true"
            }
        }
        if not createAndAttachNetworkSN(
            data_center=config.DC_NAME[0], cluster=config.CLUSTER_NAME[0],
            host=config.VDS_HOSTS[:2], network_dict=local_dict, auto_nics=[0]
        ):
            raise NetworkException(
                "Cannot create and attach network %s" % config.NETWORKS[0]
            )

    @polarion("RHEVM3-3885")
    def test_dedicated_migration_display(self):
        """
        Check dedicated network migration over display network
        """
        logger.info(
            "Check that network migration over NIC is working as "
            "expected when the network is also the display network"
        )
        dedicated_migration(vms=[config.VM_NAME[0]])


@attr(tier=1)
class TestMigrationCase06(TestMigrationCaseBase):
    """
    Verify dedicated regular network migration when the net reside on the VM
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Create logical vm network on DC/Cluster/Hosts
        Configure it as migration and configure it on the VM
        """
        ips = create_random_ips()
        local_dict = {
            config.NETWORKS[0]: {
                "nic": 1, "required": "true", "cluster_usages": "migration",
                "bootproto": "static", "address": [ips[0], ips[1]],
                "netmask": [NETMASK, NETMASK]
            },
            config.NETWORKS[1]: {
                "nic": 2, "required": "true"
            }
        }

        logger.info(
            "Configure migration network %s on the DC/Cluster/Host",
            config.NETWORKS[0]
        )
        if not createAndAttachNetworkSN(
            data_center=config.DC_NAME[0], cluster=config.CLUSTER_NAME[0],
            host=config.VDS_HOSTS[:2], network_dict=local_dict, auto_nics=[0]
        ):
            raise NetworkException(
                "Cannot create and attach network %s" % config.NETWORKS[0]
            )
        logger.info("Creating VNIC on VM with default plugged/linked states")
        if not addNic(
            True, config.VM_NAME[0], name="nic2", network=config.NETWORKS[0]
        ):
            raise NetworkException("Cannot add VNIC to VM")

    @polarion("RHEVM3-3847")
    def test_dedicated_migration_reside_vm(self):
        """
        Check dedicated network migration when network resides on VM
        """
        logger.info(
            "Check that network migration over NIC is working as "
            "expected when the network also resides on the VM"
        )
        dedicated_migration(vms=[config.VM_NAME[0]])

    @classmethod
    def teardown_class(cls):
        """
        Remove NIC from VM and remove networks from the setup.
        """
        logger.info("Remove VNIC from VM %s", config.VM_NAME[0])
        if not updateNic(True, config.VM_NAME[0], "nic2", plugged="false"):
            logger.error("Couldn't update nic to be unplugged")

        logger.info("Removing the nic2 from the VM %s", config.VM_NAME[0])
        if not removeNic(True, config.VM_NAME[0], "nic2"):
            logger.error("Cannot remove nic from setup")

        logger.info("Remove networks from setup")
        super(TestMigrationCase06, cls).teardown_class()


@attr(tier=1)
class TestMigrationCase07(TestMigrationCaseBase):
    """
    Verify migration over mgmt network when migration network is not attached
    to Hosts. Migration Network is attached only to DC and Cluster
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Create logical vm network on DC/Cluster
        Configure it as migration network
        """
        logger.info(
            "Configure migration network %s on the DC/Cluster and not on Host",
            config.NETWORKS[0]
        )
        local_dict = {
            config.NETWORKS[0]: {
                "nic": 1, "required": "true",
                "cluster_usages": "migration"
            }
        }
        if not createAndAttachNetworkSN(
            data_center=config.DC_NAME[0], cluster=config.CLUSTER_NAME[0],
            network_dict=local_dict
        ):
            raise NetworkException("Cannot create and attach network to DC/CL")

    @polarion("RHEVM3-3847")
    def test_mgmt_network_migration(self):
        """
        Check mgmt network migration
        """
        logger.info(
            "Verify migration over mgmt network when migration network"
            " is not attached to Hosts"
        )
        dedicated_migration(vms=[config.VM_NAME[0]], nic_index=0)


@attr(tier=1)
class TestMigrationCase08(TestMigrationCaseBase):
    """
    Verify dedicated regular network migration over Bond
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Create logical vm network on DC/Cluster/Hosts
        Configure it as migration network and attach it to Bond
        """
        logger.info(
            "Configure migration network %s on the DC/Cluster/Hosts over Bond",
            config.NETWORKS[0]
        )
        ips = create_random_ips()
        local_dict = {
            config.NETWORKS[0]: {
                "nic": config.BOND[0], "slaves": [2, 3], "required": "true",
                "cluster_usages": "migration", "bootproto": "static",
                "address": [ips[0], ips[1]], "netmask": [NETMASK, NETMASK]
            },
            config.NETWORKS[1]: {
                "nic": 1, "required": "true"
            }
        }
        if not createAndAttachNetworkSN(
            data_center=config.DC_NAME[0], cluster=config.CLUSTER_NAME[0],
            host=config.VDS_HOSTS[:2], network_dict=local_dict, auto_nics=[0]
        ):
            raise NetworkException("Cannot create and attach network")

    @polarion("RHEVM3-3848")
    def test_dedicated_migration_bond(self):
        """
        Check dedicated network migration over bond
        """
        logger.info(
            "Check that network migration over Bond is working as expected "
        )
        dedicated_migration(vms=[config.VM_NAME[0]], bond=config.BOND[0])


@attr(tier=1)
class TestMigrationCase09(TestMigrationCaseBase):
    """
    Verify dedicated regular non-vm network migration over Bond
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Create logical non-vm network on DC/Cluster
        Configure it as migration network and attach it to Bond on the Host
        """
        logger.info(
            "Configure non-VM migration network %s on the DC/Cluster/Hosts "
            "over bond", config.NETWORKS[0]
        )
        ips = create_random_ips()
        local_dict = {
            config.NETWORKS[0]: {
                "nic": config.BOND[0], "slaves": [2, 3], "required": "true",
                "usages": "", "cluster_usages": "migration",
                "bootproto": "static", "address": [ips[0], ips[1]],
                "netmask": [NETMASK, NETMASK]
            },
            config.NETWORKS[1]: {
                "nic": 1, "required": "true"
            }
        }
        if not createAndAttachNetworkSN(
            data_center=config.DC_NAME[0], cluster=config.CLUSTER_NAME[0],
            host=config.VDS_HOSTS[:2], network_dict=local_dict, auto_nics=[0]
        ):
            raise NetworkException("Cannot create and attach network")

    @polarion("RHEVM3-3850")
    def test_dedicated_migration_nonvm_bond(self):
        """
        Check migration over dedicated non-vm network over bond
        """
        logger.info(
            "Check that non-VM network migration over Bond is working "
            "as expected "
        )
        dedicated_migration(vms=[config.VM_NAME[0]], bond=config.BOND[0])


@attr(tier=1)
class TestMigrationCase10(TestMigrationCaseBase):
    """
    Verify dedicated regular tagged network migration over Bond
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Create logical tagged network on DC/Cluster
        Configure it as migration network and attach it to Bond on the Host
        """
        logger.info(
            "Configure tagged migration network %s on the DC/Cluster/Host "
            "over Bond", config.NETWORKS[0]
        )
        ips = create_random_ips()
        local_dict = {
            None: {
                "nic": config.BOND[0], "mode": 1, "slaves": [2, 3]
            },
            config.VLAN_NETWORKS[0]: {
                "nic": config.BOND[0], "vlan_id": config.VLAN_ID[0],
                "required": "true", "cluster_usages": "migration",
                "bootproto": "static", "address": [ips[0], ips[1]],
                "netmask": [NETMASK, NETMASK]
            },
            config.NETWORKS[1]: {
                "nic": 1, "required": "true"
            }
        }
        if not createAndAttachNetworkSN(
            data_center=config.DC_NAME[0], cluster=config.CLUSTER_NAME[0],
            host=config.VDS_HOSTS[:2], network_dict=local_dict, auto_nics=[0]
        ):
            raise NetworkException("Cannot create and attach network")

    @polarion("RHEVM3-3852")
    def test_dedicated_migration_vlan_bond(self):
        """
        Check migration over dedicated tagged network over bond
        """
        logger.info(
            "Check that VLAN network migration over Bond is working as "
            "expected "
        )
        dedicated_migration(
            vms=[config.VM_NAME[0]], vlan=config.VLAN_ID[0],
            bond=config.BOND[0]
        )


@attr(tier=1)
class TestMigrationCase11(TestMigrationCaseBase):
    """
    Verify  migration over mgmt network when dedicated migration network is
    replaced with display network
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Create logical regular migration network on DC/Cluster/Hosts
        """
        logger.info(
            "Configure migration network %s on the DC/Cluster/Host",
            config.NETWORKS[0]
        )
        ips = create_random_ips()
        local_dict = {
            config.NETWORKS[0]: {
                "nic": 1, "required": "true", "cluster_usages": "migration",
                "bootproto": "static", "address": [ips[0], ips[1]],
                "netmask": [NETMASK, NETMASK]
            },
            config.NETWORKS[1]: {"nic": 2, "required": "true"}
        }
        if not createAndAttachNetworkSN(
            data_center=config.DC_NAME[0], cluster=config.CLUSTER_NAME[0],
            host=config.VDS_HOSTS[:2], network_dict=local_dict, auto_nics=[0]
        ):
            raise NetworkException("Cannot create and attach network")

    @polarion("RHEVM3-3859")
    def test_tmgmt_network_migration(self):
        """
        Check migration over mgmt network when migration network is changed to
        display
        """
        logger.info(
            "Replace migration from the network %s with display network",
            config.NETWORKS[0]
        )
        if not updateClusterNetwork(
            True, cluster=config.CLUSTER_NAME[0], network=config.NETWORKS[0],
            usages="display"
        ):
            raise NetworkException("Cannot update network usages param")

        logger.info("Make sure the migration is over mgmt network")
        dedicated_migration(vms=[config.VM_NAME[0]], nic_index=0)


@attr(tier=1)
class TestMigrationCase12(TestMigrationCaseBase):
    """
    Verify when dedicated regular network migration is not configured on the
    Host the migration will occur on the mgmt network network
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Create logical vm network on DC/Cluster and only one Host
        Configure it as migration network
        """
        logger.info(
            "Create migration network %s and put it only on Host1",
            config.NETWORKS[0]
        )
        ips = create_random_ips(num_of_ips=1)
        local_dict = {
            config.NETWORKS[0]: {
                "nic": 1, "required": "true", "cluster_usages": "migration",
                "bootproto": "static", "address": [ips[0]],
                "netmask": [NETMASK]
            }
        }
        if not createAndAttachNetworkSN(
            data_center=config.DC_NAME[0], cluster=config.CLUSTER_NAME[0],
            host=config.VDS_HOSTS[0], network_dict=local_dict, auto_nics=[0]
        ):
            raise NetworkException("Cannot create and attach network")

    @polarion("RHEVM3-3872")
    def test_dedicated_migration_mgmt(self):
        """
        Check dedicated network migration
        """
        logger.info("Make sure the migration is over mgmt network")
        dedicated_migration(vms=[config.VM_NAME[0]], nic_index=0)
