#! /usr/bin/python
"""
Testing network migration feature.
1 DC, 1 Cluster, 2 Hosts and 1 VM will be created for testing.
Network migration will be tested for untagged, tagged, bond scenarios.
It will cover scenarios for VM/non-VM networks
"""
from nose.tools import istest
from art.unittest_lib import attr
from art.unittest_lib import NetworkTest as TestCase
from art.test_handler.tools import tcms  # pylint: disable=E0611
import logging
from helper import(
    dedicated_migration, migrate_unplug_required, get_origin_host
)
from art.rhevm_api.utils.test_utils import checkTraffic
from art.test_handler.exceptions import NetworkException

from rhevmtests.networking import config
from art.rhevm_api.tests_lib.high_level.networks import(
    createAndAttachNetworkSN, remove_net_from_setup, TrafficMonitor,
    checkICMPConnectivity
)
from art.rhevm_api.tests_lib.low_level.networks import updateClusterNetwork
from art.rhevm_api.tests_lib.low_level.vms import addNic, removeNic, updateNic
from art.rhevm_api.tests_lib.high_level.vms import check_vm_migration
from art.unittest_lib.network import find_ip

logger = logging.getLogger("Network_Migration")

NUM_PACKETS = config.NUM_PACKETS
SOURCE_IP = config.NM_SOURCE_IP
DEST_IP = config.NM_DEST_IP
NETMASK = config.NETMASK

########################################################################

########################################################################
#                             Test Cases                               #
########################################################################


class MigrationCaseBase(TestCase):
    """
    base class which provides  teardown class method for each test case
    """

    @classmethod
    def teardown_class(cls):
        """
        Remove networks from the setup.
        """
        if not remove_net_from_setup(host=config.VDS_HOSTS, auto_nics=[0],
                                     data_center=config.DC_NAME[0],
                                     mgmt_network=config.MGMT_BRIDGE,
                                     all_net=True):
            raise NetworkException("Cannot remove networks from setup")


@attr(tier=1)
class MigrationCase01(MigrationCaseBase):
    """
    Verify dedicated regular network migration
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Create logical vm network on DC/Cluster/Hosts
        Configure it as migration network
        """
        local_dict = {config.NETWORKS[0]: {'nic': 1,
                                           'required': 'true',
                                           'cluster_usages': 'migration',
                                           'bootproto': 'static',
                                           'address': [SOURCE_IP, DEST_IP],
                                           'netmask': [NETMASK,
                                                       NETMASK]},
                      config.NETWORKS[1]: {'nic': 2,
                                           'required': 'true'}}
        logger.info(
            "Configure migration VM network %s on DC/Cluster and Host ",
            config.NETWORKS[0]
        )
        if not createAndAttachNetworkSN(data_center=config.DC_NAME[0],
                                        cluster=config.CLUSTER_NAME[0],
                                        host=config.VDS_HOSTS,
                                        network_dict=local_dict,
                                        auto_nics=[0]):
            raise NetworkException(
                "Cannot create and attach network %s" % config.NETWORKS[0]
            )

    @istest
    @tcms(8735, 256582)
    def a1_dedicated_migration(self):
        """
        Check dedicated network migration
        """
        logger.info(
            "Check that network migration over NIC is working as expected"
        )
        dedicated_migration()

    @istest
    @tcms(8735, 250476)
    def a2_dedicated_migration_nic(self):
        """
        Check dedicated network migration by putting req net down
        """
        logger.info(
            "Check that network migration over NIC is working as "
            "expected by putting NIC with required network down"
        )
        migrate_unplug_required()


@attr(tier=1)
class MigrationCase02(MigrationCaseBase):
    """
    Verify default migration when no migration network specified
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Create logical vm network on DC/Cluster/Hosts
        """
        logger.info(
            "Create non-migration network %s on DC/Cluster/Hosts",
            config.NETWORKS[0]
        )
        local_dict = {config.NETWORKS[0]: {'nic': 1,
                                           'required': 'true',
                                           'bootproto': 'static',
                                           'address': [SOURCE_IP, DEST_IP],
                                           'netmask': [NETMASK,
                                                       NETMASK]}}

        if not createAndAttachNetworkSN(data_center=config.DC_NAME[0],
                                        cluster=config.CLUSTER_NAME[0],
                                        host=config.VDS_HOSTS,
                                        network_dict=local_dict,
                                        auto_nics=[0]):
            raise NetworkException(
                "Cannot create and attach network %s" % config.NETWORKS[0]
            )

    @istest
    @tcms(8735, 250464)
    def default_migration(self):
        """
        Check default migration on mgmt network network
        """
        orig_host_obj, orig_host = get_origin_host(config.VM_NAME[0])
        logger.info("Start migration from %s ", orig_host)
        logger.info("Migrating VM over mgmt network network")
        src, dst = find_ip(vm=config.VM_NAME[0],
                           host_list=config.VDS_HOSTS, nic_index=1)
        if not checkICMPConnectivity(host=orig_host_obj.ip,
                                     user=config.HOSTS_USER,
                                     password=config.HOSTS_PW, ip=dst):
            logger.error("ICMP wasn't established")
        source_ip, dest_ip = find_ip(vm=config.VM_NAME[0],
                                     host_list=config.VDS_HOSTS, nic_index=0)

        with TrafficMonitor(machine=orig_host_obj.ip,
                            user=config.HOSTS_USER,
                            password=config.HOSTS_PW,
                            nic=orig_host_obj.nics[0],
                            src=source_ip, dst=dest_ip,
                            protocol='tcp', numPackets=NUM_PACKETS) as monitor:
            monitor.addTask(check_vm_migration,
                            vm_names=config.VM_NAME[0],
                            orig_host=orig_host, vm_user=config.HOSTS_USER,
                            host_password=config.HOSTS_PW,
                            vm_password=config.HOSTS_PW,
                            os_type='rhel')
            monitor.addTask(checkTraffic, expectedRes=False,
                            machine=orig_host_obj.ip, user=config.HOSTS_USER,
                            password=config.HOSTS_PW,
                            nic=orig_host_obj.nics[1],
                            src=src, dst=dst)
        self.assertTrue(monitor.getResult())


@attr(tier=1)
class MigrationCase03(MigrationCaseBase):
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
            config.VLAN_NETWORKS[0])
        local_dict = {config.VLAN_NETWORKS[0]: {'vlan_id': config.VLAN_ID[0],
                                                'nic': 1,
                                                'required': 'true',
                                                'cluster_usages': 'migration',
                                                'bootproto': 'static',
                                                'address': [SOURCE_IP,
                                                            DEST_IP],
                                                'netmask': [NETMASK,
                                                            NETMASK]},
                      config.VLAN_NETWORKS[1]: {'vlan_id': config.VLAN_ID[1],
                                                'nic': 2,
                                                'required': 'true'
                                                }}
        if not createAndAttachNetworkSN(data_center=config.DC_NAME[0],
                                        cluster=config.CLUSTER_NAME[0],
                                        host=config.VDS_HOSTS,
                                        network_dict=local_dict,
                                        auto_nics=[0, 1, 2]):
            raise NetworkException(
                "Cannot create and attach network %s" % config.VLAN_NETWORKS[0]
            )

    @istest
    @tcms(8735, 250466)
    def dedicated_tagged_migration(self):
        """
        Check dedicated migration over tagged network over NIC
        """
        logger.info("Check that VLAN network migration over NIC is working as "
                    "expected")
        dedicated_migration(vlan=config.VLAN_ID[0])

    @istest
    @tcms(8735, 256583)
    def dedicated_tagged_migration_nic(self):
        """
        Check dedicated migration over tagged network by putting req net down
        """
        logger.info("Check that VLAN network migration over NIC is working as "
                    "expected by putting NIC with required network down")
        migrate_unplug_required(vlan=config.VLAN_ID[0])


@attr(tier=1)
class MigrationCase04(MigrationCaseBase):
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
        local_dict = {config.NETWORKS[0]: {'nic': 1,
                                           'required': 'true',
                                           'usages': '',
                                           'cluster_usages': 'migration',
                                           'bootproto': 'static',
                                           'address': [SOURCE_IP, DEST_IP],
                                           'netmask': [NETMASK,
                                                       NETMASK]},
                      config.NETWORKS[1]: {'nic': 2,
                                           'required': 'true'}}
        if not createAndAttachNetworkSN(data_center=config.DC_NAME[0],
                                        cluster=config.CLUSTER_NAME[0],
                                        host=config.VDS_HOSTS,
                                        network_dict=local_dict,
                                        auto_nics=[0]):
            raise NetworkException(
                "Cannot create and attach network %s" % config.NETWORKS[0]
            )

    @istest
    @tcms(8735, 260555)
    def nonvm_migration(self):
        """
        Check dedicated migration over non-VM network over NIC
        """
        logger.info("Check that non-VM network migration over NIC is working "
                    "as expected")
        dedicated_migration()

    @istest
    @tcms(8735, 260554)
    def nonvm_migration_nic(self):
        """
        Check dedicated migration over non-VM network by putting req net down
        """
        logger.info("Check that non-VM network migration over NIC is working "
                    "as expected by putting NIC with required network down")
        migrate_unplug_required()


@attr(tier=1)
class MigrationCase05(MigrationCaseBase):
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
        local_dict = \
            {config.NETWORKS[0]: {'nic': 1,
                                  'required': 'true',
                                  'cluster_usages': 'migration,display',
                                  'bootproto': 'static',
                                  'address': [SOURCE_IP, DEST_IP],
                                  'netmask': [NETMASK,
                                              NETMASK]},
             config.NETWORKS[1]: {'nic': 2,
                                  'required': 'true'}}
        if not createAndAttachNetworkSN(data_center=config.DC_NAME[0],
                                        cluster=config.CLUSTER_NAME[0],
                                        host=config.VDS_HOSTS,
                                        network_dict=local_dict,
                                        auto_nics=[0]):
            raise NetworkException(
                "Cannot create and attach network %s" % config.NETWORKS[0]
            )

    @istest
    @tcms(8735, 250810)
    def dedicated_migration_display(self):
        """
        Check dedicated network migration over display network
        """
        logger.info(
            "Check that network migration over NIC is working as "
            "expected when the network is also the display network"
        )
        dedicated_migration()


@attr(tier=1)
class MigrationCase06(MigrationCaseBase):
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
        local_dict = {config.NETWORKS[0]: {'nic': 1,
                                           'required': 'true',
                                           'cluster_usages': 'migration',
                                           'bootproto': 'static',
                                           'address': [SOURCE_IP, DEST_IP],
                                           'netmask': [NETMASK,
                                                       NETMASK]},
                      config.NETWORKS[1]: {'nic': 2,
                                           'required': 'true'}}

        logger.info(
            "Configure migration network %s on the DC/Cluster/Host",
            config.NETWORKS[0]
        )
        if not createAndAttachNetworkSN(data_center=config.DC_NAME[0],
                                        cluster=config.CLUSTER_NAME[0],
                                        host=config.VDS_HOSTS,
                                        network_dict=local_dict,
                                        auto_nics=[0]):
            raise NetworkException(
                "Cannot create and attach network %s" % config.NETWORKS[0]
            )
        logger.info("Creating VNIC on VM with default plugged/linked states")
        if not addNic(True, config.VM_NAME[0], name='nic2',
                      network=config.NETWORKS[0]):
            raise NetworkException("Cannot add VNIC to VM")

    @istest
    @tcms(8735, 256582)
    def dedicated_migration_reside_vm(self):
        """
        Check dedicated network migration when network resides on VM
        """
        logger.info(
            "Check that network migration over NIC is working as "
            "expected when the network also resides on the VM"
        )
        dedicated_migration()

    @classmethod
    def teardown_class(cls):
        """
        Remove NIC from VM and remove networks from the setup.
        """
        logger.info("Remove VNIC from VM %s", config.VM_NAME[0])
        if not updateNic(True, config.VM_NAME[0], "nic2", plugged='false'):
                raise NetworkException("Couldn't update nic to be unplugged")
        logger.info("Removing the nic2 from the VM %s", config.VM_NAME[0])
        if not removeNic(True, config.VM_NAME[0], "nic2"):
            raise NetworkException("Cannot remove nic from setup")
        logger.info("Remove networks from setup")
        super(MigrationCase06, cls).teardown_class()


@attr(tier=1)
class MigrationCase07(MigrationCaseBase):
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
        local_dict = {config.NETWORKS[0]: {'nic': config.HOST_NICS[1],
                                           'required': 'true',
                                           'cluster_usages': 'migration'}}
        if not createAndAttachNetworkSN(data_center=config.DC_NAME[0],
                                        cluster=config.CLUSTER_NAME[0],
                                        network_dict=local_dict):
            raise NetworkException("Cannot create and attach network to DC/CL")

    @istest
    @tcms(8735, 256582)
    def mgmt_network_migration(self):
        """
        Check mgmt network migration
        """
        logger.info(
            "Verify migration over mgmt network when migration network"
            " is not attached to Hosts"
        )
        dedicated_migration(nic_index=0)


@attr(tier=1)
class MigrationCase08(MigrationCaseBase):
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
        local_dict = {config.NETWORKS[0]: {'nic': config.BOND[0],
                                           'slaves': [2, 3],
                                           'required': 'true',
                                           'cluster_usages': 'migration',
                                           'bootproto': 'static',
                                           'address': [SOURCE_IP, DEST_IP],
                                           'netmask': [NETMASK,
                                                       NETMASK]},
                      config.NETWORKS[1]: {'nic': 1,
                                           'required': 'true'}}
        if not createAndAttachNetworkSN(data_center=config.DC_NAME[0],
                                        cluster=config.CLUSTER_NAME[0],
                                        host=config.VDS_HOSTS,
                                        network_dict=local_dict,
                                        auto_nics=[0]):
            raise NetworkException("Cannot create and attach network")

    @istest
    @tcms(8735, 260607)
    def dedicated_migration_bond(self):
        """
        Check dedicated network migration over bond
        """
        logger.info(
            "Check that network migration over Bond is working as expected "
        )
        dedicated_migration(bond=config.BOND[0])

    @istest
    @tcms(8735, 260604)
    def dedicated_migration_bond_nic(self):
        """
        Check dedicated network migration over bond putting req net down
        """
        logger.info(
            "Check that network migration over Bond is working as "
            "expected by putting NIC with required network down"
        )
        migrate_unplug_required(bond=config.BOND[0], req_nic=1)


@attr(tier=1)
class MigrationCase09(MigrationCaseBase):
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
        local_dict = {config.NETWORKS[0]: {'nic': config.BOND[0],
                                           'slaves': [2, 3],
                                           'required': 'true',
                                           'usages': '',
                                           'cluster_usages': 'migration',
                                           'bootproto': 'static',
                                           'address': [SOURCE_IP, DEST_IP],
                                           'netmask': [NETMASK,
                                                       NETMASK]},
                      config.NETWORKS[1]: {'nic': 1,
                                           'required': 'true'}}
        if not createAndAttachNetworkSN(data_center=config.DC_NAME[0],
                                        cluster=config.CLUSTER_NAME[0],
                                        host=config.VDS_HOSTS,
                                        network_dict=local_dict,
                                        auto_nics=[0]):
            raise NetworkException("Cannot create and attach network")

    @istest
    @tcms(8735, 260606)
    def dedicated_migration_nonvm_bond(self):
        """
        Check migration over dedicated non-vm network over bond
        """
        logger.info(
            "Check that non-VM network migration over Bond is working "
            "as expected "
        )
        dedicated_migration(bond=config.BOND[0])

    @istest
    @tcms(8735, 260603)
    def dedicated_migration_nonvm_bond_nic(self):
        """
        Check migration over dedicated non-vm network over bond
        Do it by turning down NIC with required network
        """
        logger.info(
            "Check that non-VM network migration over Bond is working "
            "as expected by putting NIC with required network down"
        )
        migrate_unplug_required(bond=config.BOND[0], req_nic=1)


@attr(tier=1)
class MigrationCase10(MigrationCaseBase):
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
        local_dict = {None: {'nic': config.BOND[0], 'mode': 1,
                             'slaves': [2, 3]},
                      config.VLAN_NETWORKS[0]: {'nic': config.BOND[0],
                                                'vlan_id': config.VLAN_ID[0],
                                                'required': 'true',
                                                'cluster_usages': 'migration',
                                                'bootproto': 'static',
                                                'address': [SOURCE_IP,
                                                            DEST_IP],
                                                'netmask': [NETMASK,
                                                            NETMASK]},
                      config.NETWORKS[1]: {'nic': 1,
                                           'required': 'true'}}
        if not createAndAttachNetworkSN(data_center=config.DC_NAME[0],
                                        cluster=config.CLUSTER_NAME[0],
                                        host=config.VDS_HOSTS,
                                        network_dict=local_dict,
                                        auto_nics=[0]):
            raise NetworkException("Cannot create and attach network")

    @istest
    @tcms(8735, 260608)
    def dedicated_migration_vlan_bond(self):
        """
        Check migration over dedicated tagged network over bond
        """
        logger.info(
            "Check that VLAN network migration over Bond is working as "
            "expected "
        )
        dedicated_migration(vlan=config.VLAN_ID[0], bond=config.BOND[0])

    @istest
    @tcms(8735, 260605)
    def dedicated_migration_vlan_bond_nic(self):
        """
        Check migration over dedicated tagged network over bond
        Disconnect the nic with required network to do it
        """
        logger.info(
            "Check that VLAN network migration over Bond is working "
            "as expected by putting NIC with required network down"
        )
        migrate_unplug_required(bond=config.BOND[0], req_nic=1,
                                vlan=config.VLAN_ID[0])


@attr(tier=1)
class MigrationCase11(MigrationCaseBase):
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
        local_dict = {config.NETWORKS[0]: {'nic': 1,
                                           'required': 'true',
                                           'cluster_usages': 'migration',
                                           'bootproto': 'static',
                                           'address': [SOURCE_IP, DEST_IP],
                                           'netmask': [NETMASK,
                                                       NETMASK]},
                      config.NETWORKS[1]: {'nic': 2,
                                           'required': 'true'}}
        if not createAndAttachNetworkSN(data_center=config.DC_NAME[0],
                                        cluster=config.CLUSTER_NAME[0],
                                        host=config.VDS_HOSTS,
                                        network_dict=local_dict,
                                        auto_nics=[0]):
            raise NetworkException("Cannot create and attach network")

    @istest
    @tcms(8735, 250469)
    def mgmt_network_migration(self):
        """
        Check migration over mgmt network when migration network is changed to
        display
        """
        logger.info(
            "Replace migration from the network %s with display network",
            config.NETWORKS[0]
        )
        if not updateClusterNetwork(True, cluster=config.CLUSTER_NAME[0],
                                    network=config.NETWORKS[0],
                                    usages='display'):
            raise NetworkException("Cannot update network usages param")

        orig_host_obj, orig_host = get_origin_host(config.VM_NAME[0])
        logger.info("Start migration from %s ", orig_host)
        logger.info("Make sure the migration is over mgmt network")
        src, dst = find_ip(vm=config.VM_NAME[0],
                           host_list=config.VDS_HOSTS, nic_index=1)
        if not checkICMPConnectivity(host=orig_host, user=config.HOSTS_USER,
                                     password=config.HOSTS_PW, ip=dst):
            logger.error("ICMP wasn't established")

        source_ip, dest_ip = find_ip(vm=config.VM_NAME[0],
                                     host_list=config.VDS_HOSTS,
                                     nic_index=0)

        with TrafficMonitor(machine=orig_host_obj.ip,
                            user=config.HOSTS_USER,
                            password=config.HOSTS_PW,
                            nic=orig_host_obj.nics[0],
                            src=source_ip, dst=dest_ip,
                            protocol='tcp', numPackets=NUM_PACKETS) as monitor:
            monitor.addTask(check_vm_migration,
                            vm_names=config.VM_NAME[0],
                            orig_host=orig_host, vm_user=config.HOSTS_USER,
                            host_password=config.HOSTS_PW,
                            vm_password=config.HOSTS_PW,
                            os_type='rhel')
            monitor.addTask(checkTraffic, expectedRes=False,
                            machine=orig_host_obj.ip, user=config.HOSTS_USER,
                            password=config.HOSTS_PW,
                            nic=orig_host_obj.nics[1],
                            src=src, dst=dst)
        self.assertTrue(monitor.getResult())


@attr(tier=1)
class MigrationCase12(MigrationCaseBase):
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
        local_dict = {config.NETWORKS[0]: {'nic': 1,
                                           'required': 'true',
                                           'cluster_usages': 'migration',
                                           'bootproto': 'static',
                                           'address': [SOURCE_IP],
                                           'netmask': [NETMASK]}}
        if not createAndAttachNetworkSN(data_center=config.DC_NAME[0],
                                        cluster=config.CLUSTER_NAME[0],
                                        host=config.VDS_HOSTS[0],
                                        network_dict=local_dict,
                                        auto_nics=[0]):
            raise NetworkException("Cannot create and attach network")

    @istest
    @tcms(8735, 260613)
    def dedicated_migration_mgmt(self):
        """
        Check dedicated network migration
        """
        logger.info("Make sure the migration is over mgmt network")
        dedicated_migration(nic_index=0)
