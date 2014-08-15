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

from art.rhevm_api.utils.test_utils import get_api, checkTraffic
from art.test_handler.exceptions import NetworkException, VMException
from art.test_handler.settings import opts

from rhevmtests.networking import config
from art.rhevm_api.tests_lib.high_level.networks import\
    createAndAttachNetworkSN, removeNetFromSetup, TrafficMonitor,\
    checkICMPConnectivity
from art.rhevm_api.tests_lib.low_level.networks import\
    updateClusterNetwork
from art.rhevm_api.tests_lib.low_level.hosts import setHostToNonOperational
from art.rhevm_api.tests_lib.low_level.vms import addNic, removeNic,\
    updateNic
from art.rhevm_api.tests_lib.high_level.vms import check_vm_migration
from art.unittest_lib.network import find_ip, get_host

HOST_API = get_api('host', 'hosts')
VM_API = get_api('vm', 'vms')

logger = logging.getLogger(__name__)

ENUMS = opts['elements_conf']['RHEVM Enums']
NUM_PACKETS = config.NUM_PACKETS
SOURCE_IP = config.NM_SOURCE_IP
DEST_IP = config.NM_DEST_IP
NETMASK = config.NETMASK

########################################################################

########################################################################
#                             Test Cases                               #
########################################################################


@attr(tier=1)
class MigrationCase01(TestCase):
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
        local_dict = {config.NETWORKS[0]: {'nic': config.HOST_NICS[1],
                                           'required': 'true',
                                           'cluster_usages': 'migration',
                                           'bootproto': 'static',
                                           'address': [SOURCE_IP, DEST_IP],
                                           'netmask': [NETMASK,
                                                       NETMASK]},
                      config.NETWORKS[1]: {'nic': config.HOST_NICS[2],
                                           'required': 'true'}}
        if not createAndAttachNetworkSN(data_center=config.DC_NAME[0],
                                        cluster=config.CLUSTER_NAME[0],
                                        host=config.HOSTS,
                                        network_dict=local_dict,
                                        auto_nics=[config.HOST_NICS[0]]):
            raise NetworkException("Cannot create and attach network")

    @istest
    @tcms(8735, 256582)
    def dedicated_migration(self):
        """
        Check dedicated network migration
        """
        orig_host = get_host(config.VM_NAME[0])
        logger.info("Start migration from %s ", orig_host)
        logger.info("Migrating VM over migration network")
        src, dst = find_ip(vm=config.VM_NAME[0],
                           host_list=config.HOSTS, nic=config.HOST_NICS[1])
        if not checkICMPConnectivity(host=orig_host, user=config.HOSTS_USER,
                                     password=config.HOSTS_PW, ip=dst):
            logger.error("ICMP wasn't established")
        with TrafficMonitor(machine=orig_host, user=config.HOSTS_USER,
                            password=config.HOSTS_PW,
                            nic=config.HOST_NICS[1],
                            src=src, dst=dst,
                            protocol='tcp', numPackets=NUM_PACKETS) as monitor:
            monitor.addTask(check_vm_migration,
                            vm_names=config.VM_NAME[0],
                            orig_host=orig_host, vm_user=config.HOSTS_USER,
                            host_password=config.HOSTS_PW,
                            vm_password=config.HOSTS_PW,
                            os_type='rhel')
        self.assertTrue(monitor.getResult())

    @istest
    @tcms(8735, 250476)
    def dedicated_migration_nic(self):
        """
        Check dedicated network migration by putting req net down
        """
        orig_host = get_host(config.VM_NAME[0])
        logger.info("Returning VMs back to original host over migration net")
        logger.info("Start migration from %s ", orig_host)
        src, dst = find_ip(vm=config.VM_NAME[0],
                           host_list=config.HOSTS, nic=config.HOST_NICS[1])
        if not setHostToNonOperational(orig_host=orig_host,
                                       host_password=config.HOSTS_PW,
                                       nic=config.HOST_NICS[2]):
            raise NetworkException("Cannot start migration by putting"
                                   " Nic %s down", config.HOST_NICS[2])
        with TrafficMonitor(machine=orig_host, user=config.HOSTS_USER,
                            password=config.HOSTS_PW,
                            nic=config.HOST_NICS[1],
                            src=src, dst=dst,
                            protocol='tcp', numPackets=NUM_PACKETS) as monitor:
            monitor.addTask(check_vm_migration,
                            vm_names=config.VM_NAME[0],
                            orig_host=orig_host, vm_user=config.HOSTS_USER,
                            host_password=config.HOSTS_PW,
                            vm_password=config.HOSTS_PW,
                            os_type='rhel', nic=config.HOST_NICS[2],
                            nic_down=False)
        self.assertTrue(monitor.getResult())

    @classmethod
    def teardown_class(cls):
        """
        Remove network from the setup.
        """
        logger.info("Remove networks from setup")
        if not removeNetFromSetup(host=config.HOSTS,
                                  auto_nics=[config.HOST_NICS[0]],
                                  network=[config.NETWORKS[0],
                                           config.NETWORKS[1]]):
            raise NetworkException("Cannot remove network from setup")


@attr(tier=1)
class MigrationCase02(TestCase):
    """
    Verify default migration when no migration network specified
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Create logical vm network on DC/Cluster/Hosts
        """
        logger.info("Create non-migration network on DC/Cluster/Hosts")
        local_dict = {config.NETWORKS[0]: {'nic': config.HOST_NICS[1],
                                           'required': 'true',
                                           'bootproto': 'static',
                                           'address': [SOURCE_IP, DEST_IP],
                                           'netmask': [NETMASK,
                                                       NETMASK]}}

        if not createAndAttachNetworkSN(data_center=config.DC_NAME[0],
                                        cluster=config.CLUSTER_NAME[0],
                                        host=config.HOSTS,
                                        network_dict=local_dict,
                                        auto_nics=[config.HOST_NICS[0]]):
            raise NetworkException("Cannot create and attach network")

    @istest
    @tcms(8735, 250464)
    def default_migration(self):
        """
        Check default migration on mgmt network network
        """
        orig_host = get_host(config.VM_NAME[0])
        logger.info("Start migration from %s ", orig_host)
        logger.info("Migrating VM over mgmt network network")
        src, dst = find_ip(vm=config.VM_NAME[0],
                           host_list=config.HOSTS, nic=config.HOST_NICS[1])
        if not checkICMPConnectivity(host=orig_host, user=config.HOSTS_USER,
                                     password=config.HOSTS_PW, ip=dst):
            logger.error("ICMP wasn't established")
        source_ip, dest_ip = find_ip(vm=config.VM_NAME[0],
                                     host_list=config.HOSTS,
                                     nic=config.HOST_NICS[0])

        with TrafficMonitor(machine=orig_host,
                            user=config.HOSTS_USER,
                            password=config.HOSTS_PW,
                            nic=config.HOST_NICS[0],
                            src=source_ip, dst=dest_ip,
                            protocol='tcp', numPackets=NUM_PACKETS) as monitor:
            monitor.addTask(check_vm_migration,
                            vm_names=config.VM_NAME[0],
                            orig_host=orig_host, vm_user=config.HOSTS_USER,
                            host_password=config.HOSTS_PW,
                            vm_password=config.HOSTS_PW,
                            os_type='rhel')
            monitor.addTask(checkTraffic, expectedRes=False,
                            machine=orig_host, user=config.HOSTS_USER,
                            password=config.HOSTS_PW,
                            nic=config.HOST_NICS[1],
                            src=src, dst=dst)
        self.assertTrue(monitor.getResult())

    @classmethod
    def teardown_class(cls):
        """
        Remove network from the setup.
        """
        logger.info("Remove networks from setup")
        if not removeNetFromSetup(host=config.HOSTS,
                                  auto_nics=[config.HOST_NICS[0]],
                                  network=[config.NETWORKS[0]]):
            raise NetworkException("Cannot remove network from setup")


@attr(tier=1)
class MigrationCase03(TestCase):
    """
    Verify dedicated migration over tagged network over NIC
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Create logical tagged vm network on DC/Cluster/Hosts
        """
        local_dict = {config.VLAN_NETWORKS[0]: {'vlan_id': config.VLAN_ID[0],
                                                'nic': config.HOST_NICS[1],
                                                'required': 'true',
                                                'cluster_usages': 'migration',
                                                'bootproto': 'static',
                                                'address': [SOURCE_IP,
                                                            DEST_IP],
                                                'netmask': [NETMASK,
                                                            NETMASK]},
                      config.VLAN_NETWORKS[1]: {'vlan_id': config.VLAN_ID[1],
                                                'nic': config.HOST_NICS[2],
                                                'required': 'true'
                                                }}
        if not createAndAttachNetworkSN(data_center=config.DC_NAME[0],
                                        cluster=config.CLUSTER_NAME[0],
                                        host=config.HOSTS,
                                        network_dict=local_dict,
                                        auto_nics=[config.HOST_NICS[0],
                                                   config.HOST_NICS[1],
                                                   config.HOST_NICS[2]]):
            raise NetworkException("Cannot create and attach network")

    @istest
    @tcms(8735, 250466)
    def dedicated_tagged_migration(self):
        """
        Check dedicated migration over tagged network over NIC
        """
        orig_host = get_host(config.VM_NAME[0])
        logger.info("Start migration from %s ", orig_host)
        logger.info("Migrating VM over migration network")
        src, dst = find_ip(vm=config.VM_NAME[0],
                           host_list=config.HOSTS,
                           nic='.'.join([config.HOST_NICS[1],
                                         config.VLAN_ID[0]]))
        if not checkICMPConnectivity(host=orig_host, user=config.HOSTS_USER,
                                     password=config.HOSTS_PW, ip=dst):
            logger.error("ICMP wasn't established")

        with TrafficMonitor(machine=orig_host, user=config.HOSTS_USER,
                            password=config.HOSTS_PW,
                            nic=config.HOST_NICS[1],
                            src=src, dst=dst,
                            protocol='tcp', numPackets=NUM_PACKETS) as monitor:
            monitor.addTask(check_vm_migration,
                            vm_names=config.VM_NAME[0],
                            orig_host=orig_host, vm_user=config.HOSTS_USER,
                            host_password=config.HOSTS_PW,
                            vm_password=config.HOSTS_PW,
                            os_type='rhel')
        self.assertTrue(monitor.getResult())

    @istest
    @tcms(8735, 256583)
    def dedicated_tagged_migration_nic(self):
        """
        Check dedicated migration over tagged network by putting req net down
        """
        orig_host = get_host(config.VM_NAME[0])
        logger.info("Returning VMs back to original host")
        logger.info("Start migration from %s ", orig_host)
        logger.info("Migrating VM over migration network")
        src, dst = find_ip(vm=config.VM_NAME[0],
                           host_list=config.HOSTS,
                           nic='.'.join([config.HOST_NICS[1],
                                         config.VLAN_ID[0]]))
        if not setHostToNonOperational(orig_host=orig_host,
                                       host_password=config.HOSTS_PW,
                                       nic=config.HOST_NICS[2]):
            raise NetworkException("Cannot start migration by putting"
                                   " Nic %s down", config.HOST_NICS[2])

        with TrafficMonitor(machine=orig_host, user=config.HOSTS_USER,
                            password=config.HOSTS_PW,
                            nic=config.HOST_NICS[1],
                            src=src, dst=dst,
                            protocol='tcp', numPackets=NUM_PACKETS) as monitor:
            monitor.addTask(check_vm_migration,
                            vm_names=config.VM_NAME[0],
                            orig_host=orig_host, vm_user=config.HOSTS_USER,
                            host_password=config.HOSTS_PW,
                            vm_password=config.HOSTS_PW,
                            os_type='rhel', nic=config.HOST_NICS[2],
                            nic_down=False)
        self.assertTrue(monitor.getResult())

    @classmethod
    def teardown_class(cls):
        """
        Remove network from the setup.
        """
        logger.info("Remove VLAN networks from setup")
        if not removeNetFromSetup(host=config.HOSTS,
                                  auto_nics=[config.HOST_NICS[0]],
                                  network=[config.VLAN_NETWORKS[0],
                                           config.VLAN_NETWORKS[1]]):
            raise NetworkException("Cannot remove network from setup")


@attr(tier=1)
class MigrationCase04(TestCase):
    """
    Verify dedicated migration over non-VM network over NIC
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Create logical non-vm network on DC/Cluster/Hosts
        """
        local_dict = {config.NETWORKS[0]: {'nic': config.HOST_NICS[1],
                                           'required': 'true',
                                           'usages': '',
                                           'cluster_usages': 'migration',
                                           'bootproto': 'static',
                                           'address': [SOURCE_IP, DEST_IP],
                                           'netmask': [NETMASK,
                                                       NETMASK]},
                      config.NETWORKS[1]: {'nic': config.HOST_NICS[2],
                                           'required': 'true'}}
        if not createAndAttachNetworkSN(data_center=config.DC_NAME[0],
                                        cluster=config.CLUSTER_NAME[0],
                                        host=config.HOSTS,
                                        network_dict=local_dict,
                                        auto_nics=[config.HOST_NICS[0]]):
            raise NetworkException("Cannot create and attach network")

    @istest
    @tcms(8735, 260555)
    def nonvm_migration(self):
        """
        Check dedicated migration over non-VM network over NIC
        """
        orig_host = get_host(config.VM_NAME[0])
        logger.info("Start migration from %s ", orig_host)
        src, dst = find_ip(vm=config.VM_NAME[0],
                           host_list=config.HOSTS, nic=config.HOST_NICS[1])
        if not checkICMPConnectivity(host=orig_host, user=config.HOSTS_USER,
                                     password=config.HOSTS_PW, ip=dst):
            logger.error("ICMP wasn't established")
        with TrafficMonitor(machine=orig_host, user=config.HOSTS_USER,
                            password=config.HOSTS_PW,
                            nic=config.HOST_NICS[1],
                            src=src, dst=dst,
                            protocol='tcp', numPackets=NUM_PACKETS) as monitor:
            monitor.addTask(check_vm_migration,
                            vm_names=config.VM_NAME[0],
                            orig_host=orig_host, vm_user=config.HOSTS_USER,
                            host_password=config.HOSTS_PW,
                            vm_password=config.HOSTS_PW,
                            os_type='rhel')
        self.assertTrue(monitor.getResult())

    @istest
    @tcms(8735, 260554)
    def nonvm_migration_nic(self):
        """
        Check dedicated migration over non-VM network by putting req net down
        """
        orig_host = get_host(config.VM_NAME[0])
        logger.info("Returning VMs back to original host")
        logger.info("Start migration from %s ", orig_host)
        src, dst = find_ip(vm=config.VM_NAME[0],
                           host_list=config.HOSTS, nic=config.HOST_NICS[1])
        if not setHostToNonOperational(orig_host=orig_host,
                                       host_password=config.HOSTS_PW,
                                       nic=config.HOST_NICS[2]):
            raise NetworkException("Cannot start migration by putting"
                                   " Nic %s down", config.HOST_NICS[2])
        with TrafficMonitor(machine=orig_host, user=config.HOSTS_USER,
                            password=config.HOSTS_PW,
                            nic=config.HOST_NICS[1],
                            src=src, dst=dst,
                            protocol='tcp', numPackets=NUM_PACKETS) as monitor:
            monitor.addTask(check_vm_migration,
                            vm_names=config.VM_NAME[0],
                            orig_host=orig_host, vm_user=config.HOSTS_USER,
                            host_password=config.HOSTS_PW,
                            vm_password=config.HOSTS_PW,
                            os_type='rhel', nic=config.HOST_NICS[2],
                            nic_down=False)
        self.assertTrue(monitor.getResult())

    @classmethod
    def teardown_class(cls):
        """
        Remove network from the setup.
        """
        logger.info("Remove networks from setup")
        if not removeNetFromSetup(host=config.HOSTS,
                                  auto_nics=[config.HOST_NICS[0]],
                                  network=[config.NETWORKS[0],
                                           config.NETWORKS[1]]):
            raise NetworkException("Cannot remove network from setup")


@attr(tier=1)
class MigrationCase05(TestCase):
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
        local_dict = \
            {config.NETWORKS[0]: {'nic': config.HOST_NICS[1],
                                  'required': 'true',
                                  'cluster_usages': 'migration,display',
                                  'bootproto': 'static',
                                  'address': [SOURCE_IP, DEST_IP],
                                  'netmask': [NETMASK,
                                              NETMASK]},
             config.NETWORKS[1]: {'nic': config.HOST_NICS[2],
                                  'required': 'true'}}
        if not createAndAttachNetworkSN(data_center=config.DC_NAME[0],
                                        cluster=config.CLUSTER_NAME[0],
                                        host=config.HOSTS,
                                        network_dict=local_dict,
                                        auto_nics=[config.HOST_NICS[0]]):
            raise NetworkException("Cannot create and attach network")

    @istest
    @tcms(8735, 250810)
    def dedicated_migration(self):
        """
        Check dedicated network migration over display network
        """
        orig_host = get_host(config.VM_NAME[0])
        logger.info("Start migration from %s ", orig_host)
        src, dst = find_ip(vm=config.VM_NAME[0],
                           host_list=config.HOSTS, nic=config.HOST_NICS[1])
        if not checkICMPConnectivity(host=orig_host, user=config.HOSTS_USER,
                                     password=config.HOSTS_PW, ip=dst):
            logger.error("ICMP wasn't established")

        with TrafficMonitor(machine=orig_host, user=config.HOSTS_USER,
                            password=config.HOSTS_PW,
                            nic=config.HOST_NICS[1],
                            src=src, dst=dst,
                            protocol='tcp', numPackets=NUM_PACKETS) as monitor:
            monitor.addTask(check_vm_migration,
                            vm_names=config.VM_NAME[0],
                            orig_host=orig_host, vm_user=config.HOSTS_USER,
                            host_password=config.HOSTS_PW,
                            vm_password=config.HOSTS_PW,
                            os_type='rhel')
        self.assertTrue(monitor.getResult())

    @classmethod
    def teardown_class(cls):
        """
        Remove networks from the setup.
        """
        logger.info("Remove networks from setup")
        if not removeNetFromSetup(host=config.HOSTS,
                                  auto_nics=[config.HOST_NICS[0]],
                                  network=[config.NETWORKS[0],
                                           config.NETWORKS[1]]):
            raise NetworkException("Cannot remove network from setup")


@attr(tier=1)
class MigrationCase06(TestCase):
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
        local_dict = {config.NETWORKS[0]: {'nic': config.HOST_NICS[1],
                                           'required': 'true',
                                           'cluster_usages': 'migration',
                                           'bootproto': 'static',
                                           'address': [SOURCE_IP, DEST_IP],
                                           'netmask': [NETMASK,
                                                       NETMASK]},
                      config.NETWORKS[1]: {'nic': config.HOST_NICS[2],
                                           'required': 'true'}}

        logger.info("Configure migration network on the DC/Cluster/Host")
        if not createAndAttachNetworkSN(data_center=config.DC_NAME[0],
                                        cluster=config.CLUSTER_NAME[0],
                                        host=config.HOSTS,
                                        network_dict=local_dict,
                                        auto_nics=[config.HOST_NICS[0]]):
            raise NetworkException("Cannot create and attach network")
        logger.info("Creating VNICs with default plugged/linked states")
        if not addNic(True, config.VM_NAME[0], name='nic2',
                      network=config.NETWORKS[0]):
            raise VMException("Cannot add VNIC to VM")

    @istest
    @tcms(8735, 256582)
    def dedicated_migration(self):
        """
        Check dedicated network migration when network resides on VM
        """
        orig_host = get_host(config.VM_NAME[0])
        logger.info("Start migration from %s ", orig_host)
        src, dst = find_ip(vm=config.VM_NAME[0],
                           host_list=config.HOSTS, nic=config.HOST_NICS[1])
        if not checkICMPConnectivity(host=orig_host, user=config.HOSTS_USER,
                                     password=config.HOSTS_PW, ip=dst):
            logger.error("ICMP wasn't established")

        with TrafficMonitor(machine=orig_host, user=config.HOSTS_USER,
                            password=config.HOSTS_PW,
                            nic=config.HOST_NICS[1],
                            src=src, dst=dst,
                            protocol='tcp', numPackets=NUM_PACKETS) as monitor:
            monitor.addTask(check_vm_migration,
                            vm_names=config.VM_NAME[0],
                            orig_host=orig_host, vm_user=config.HOSTS_USER,
                            host_password=config.HOSTS_PW,
                            vm_password=config.HOSTS_PW,
                            os_type='rhel')
        self.assertTrue(monitor.getResult())

    @classmethod
    def teardown_class(cls):
        """
        Remove network from the setup.
        """
        if not updateNic(True, config.VM_NAME[0], "nic2", plugged='false'):
                raise NetworkException("Couldn't update nic to be unplugged")
        logger.info("Removing the nic2 from the VM %s", config.VM_NAME[0])
        if not removeNic(True, config.VM_NAME[0], "nic2"):
            raise VMException("Cannot remove nic from setup")
        logger.info("Remove networks from setup")
        if not removeNetFromSetup(host=config.HOSTS,
                                  auto_nics=[config.HOST_NICS[0]],
                                  network=[config.NETWORKS[0],
                                           config.NETWORKS[1]]):
            raise NetworkException("Cannot remove network from setup")


@attr(tier=1)
class MigrationCase07(TestCase):
    """
    Verify migration over mgmt network when migration network is not attached.
    to Hosts Migration Network is attached only to DC and Cluster
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Create logical vm network on DC/Cluster
        Configure it as migration network
        """
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
        orig_host = get_host(config.VM_NAME[0])
        logger.info("Start migration from %s ", orig_host)
        logger.info("Checking that the migration traffic is on mgmt network")
        source_ip, dest_ip = find_ip(vm=config.VM_NAME[0],
                                     host_list=config.HOSTS,
                                     nic=config.HOST_NICS[0])

        with TrafficMonitor(machine=orig_host, user=config.HOSTS_USER,
                            password=config.HOSTS_PW,
                            nic=config.HOST_NICS[0],
                            src=source_ip, dst=dest_ip,
                            protocol='tcp', numPackets=NUM_PACKETS) as monitor:
            monitor.addTask(check_vm_migration,
                            vm_names=config.VM_NAME[0],
                            orig_host=orig_host, vm_user=config.HOSTS_USER,
                            host_password=config.HOSTS_PW,
                            vm_password=config.HOSTS_PW,
                            os_type='rhel')
        self.assertTrue(monitor.getResult())

    @classmethod
    def teardown_class(cls):
        """
        Remove network from the setup.
        """
        logger.info("Remove networks from setup")
        if not removeNetFromSetup(host=config.HOSTS,
                                  auto_nics=[config.HOST_NICS[0]],
                                  network=[config.NETWORKS[0]]):
            raise NetworkException("Cannot remove network from setup")


@attr(tier=1)
class MigrationCase08(TestCase):
    """
    Verify dedicated regular network migration over Bond
    """
    __test__ = len(config.HOST_NICS) > 3

    @classmethod
    def setup_class(cls):
        """
        Create logical vm network on DC/Cluster/Hosts
        Configure it as migration network and attach it to Bond
        """
        local_dict = {config.NETWORKS[0]: {'nic': config.BOND[0],
                                           'slaves': [config.HOST_NICS[2],
                                                      config.HOST_NICS[3]],
                                           'required': 'true',
                                           'cluster_usages': 'migration',
                                           'bootproto': 'static',
                                           'address': [SOURCE_IP, DEST_IP],
                                           'netmask': [NETMASK,
                                                       NETMASK]},
                      config.NETWORKS[1]: {'nic': config.HOST_NICS[1],
                                           'required': 'true'}}
        if not createAndAttachNetworkSN(data_center=config.DC_NAME[0],
                                        cluster=config.CLUSTER_NAME[0],
                                        host=config.HOSTS,
                                        network_dict=local_dict,
                                        auto_nics=[config.HOST_NICS[0]]):
            raise NetworkException("Cannot create and attach network")

    @istest
    @tcms(8735, 260607)
    def dedicated_migration_bond(self):
        """
        Check dedicated network migration over bond
        """
        orig_host = get_host(config.VM_NAME[0])
        logger.info("Start migration from %s ", orig_host)
        src, dst = find_ip(vm=config.VM_NAME[0],
                           host_list=config.HOSTS,
                           nic=config.BOND[0])
        if not checkICMPConnectivity(host=orig_host, user=config.HOSTS_USER,
                                     password=config.HOSTS_PW, ip=dst):
            logger.error("ICMP wasn't established")

        with TrafficMonitor(machine=orig_host, user=config.HOSTS_USER,
                            password=config.HOSTS_PW,
                            nic=config.BOND[0],
                            src=src, dst=dst,
                            protocol='tcp', numPackets=NUM_PACKETS) as monitor:
            monitor.addTask(check_vm_migration,
                            vm_names=config.VM_NAME[0],
                            orig_host=orig_host, vm_user=config.HOSTS_USER,
                            host_password=config.HOSTS_PW,
                            vm_password=config.HOSTS_PW,
                            os_type='rhel')
        self.assertTrue(monitor.getResult())

    @istest
    @tcms(8735, 260604)
    def dedicated_migration_bond_nic(self):
        """
        Check dedicated network migration over bond putting req net down
        """
        orig_host = get_host(config.VM_NAME[0])
        logger.info("Returning VMs back to original host over bond ")
        logger.info("Start migration from %s ", orig_host)
        src, dst = find_ip(vm=config.VM_NAME[0],
                           host_list=config.HOSTS,
                           nic=config.BOND[0])
        if not setHostToNonOperational(orig_host=orig_host,
                                       host_password=config.HOSTS_PW,
                                       nic=config.HOST_NICS[1]):
            raise NetworkException("Cannot start migration by putting"
                                   " Nic %s down", config.HOST_NICS[1])

        with TrafficMonitor(machine=orig_host, user=config.HOSTS_USER,
                            password=config.HOSTS_PW,
                            nic='bond0',
                            src=src, dst=dst,
                            protocol='tcp', numPackets=NUM_PACKETS) as monitor:
            monitor.addTask(check_vm_migration,
                            vm_names=config.VM_NAME[0],
                            orig_host=orig_host, vm_user=config.HOSTS_USER,
                            host_password=config.HOSTS_PW,
                            vm_password=config.HOSTS_PW,
                            os_type='rhel', nic=config.HOST_NICS[1],
                            nic_down=False)
        self.assertTrue(monitor.getResult())

    @classmethod
    def teardown_class(cls):
        """
        Remove network from the setup.
        """
        logger.info("Remove networks from setup")
        if not removeNetFromSetup(host=config.HOSTS,
                                  auto_nics=[config.HOST_NICS[0]],
                                  network=[config.NETWORKS[0],
                                           config.NETWORKS[1]]):
            raise NetworkException("Cannot remove network from setup")


@attr(tier=1)
class MigrationCase09(TestCase):
    """
    Verify dedicated regular non-vm network migration over Bond
    """
    __test__ = len(config.HOST_NICS) > 3

    @classmethod
    def setup_class(cls):
        """
        Create logical non-vm network on DC/Cluster
        Configure it as migration network and attach it to Bond on the Host
        """
        local_dict = {config.NETWORKS[0]: {'nic': config.BOND[0],
                                           'slaves': [config.HOST_NICS[2],
                                                      config.HOST_NICS[3]],
                                           'required': 'true',
                                           'usages': '',
                                           'cluster_usages': 'migration',
                                           'bootproto': 'static',
                                           'address': [SOURCE_IP, DEST_IP],
                                           'netmask': [NETMASK,
                                                       NETMASK]},
                      config.NETWORKS[1]: {'nic': config.HOST_NICS[1],
                                           'required': 'true'}}
        if not createAndAttachNetworkSN(data_center=config.DC_NAME[0],
                                        cluster=config.CLUSTER_NAME[0],
                                        host=config.HOSTS,
                                        network_dict=local_dict,
                                        auto_nics=[config.HOST_NICS[0]]):
            raise NetworkException("Cannot create and attach network")

    @istest
    @tcms(8735, 260606)
    def dedicated_migration_nonvm_bond(self):
        """
        Check migration over dedicated non-vm network over bond
        """
        orig_host = get_host(config.VM_NAME[0])
        logger.info("Start migration from %s ", orig_host)
        src, dst = find_ip(vm=config.VM_NAME[0],
                           host_list=config.HOSTS,
                           nic=config.BOND[0])
        if not checkICMPConnectivity(host=orig_host, user=config.HOSTS_USER,
                                     password=config.HOSTS_PW, ip=dst):
            logger.error("ICMP wasn't established")

        with TrafficMonitor(machine=orig_host, user=config.HOSTS_USER,
                            password=config.HOSTS_PW,
                            nic='bond0',
                            src=src, dst=dst,
                            protocol='tcp', numPackets=NUM_PACKETS) as monitor:
            monitor.addTask(check_vm_migration,
                            vm_names=config.VM_NAME[0],
                            orig_host=orig_host, vm_user=config.HOSTS_USER,
                            host_password=config.HOSTS_PW,
                            vm_password=config.HOSTS_PW,
                            os_type='rhel')
        self.assertTrue(monitor.getResult())

    @istest
    @tcms(8735, 260603)
    def dedicated_migration_nonvm_bond_nic(self):
        """
        Check migration over dedicated non-vm network over bond
        Do it by turning down NIC with required network
        """
        orig_host = get_host(config.VM_NAME[0])
        logger.info("Returning VMs back to original host over bond ")
        logger.info("Start migration from %s ", orig_host)
        src, dst = find_ip(vm=config.VM_NAME[0],
                           host_list=config.HOSTS,
                           nic=config.BOND[0])
        if not setHostToNonOperational(orig_host=orig_host,
                                       host_password=config.HOSTS_PW,
                                       nic=config.HOST_NICS[1]):
            raise NetworkException("Cannot start migration by putting"
                                   " Nic %s down", config.HOST_NICS[1])

        with TrafficMonitor(timeout=200, machine=orig_host,
                            user=config.HOSTS_USER,
                            password=config.HOSTS_PW,
                            nic=config.BOND[0],
                            src=src, dst=dst,
                            protocol='tcp', numPackets=NUM_PACKETS) as monitor:
            monitor.addTask(check_vm_migration,
                            vm_names=config.VM_NAME[0],
                            orig_host=orig_host, vm_user=config.HOSTS_USER,
                            host_password=config.HOSTS_PW,
                            vm_password=config.HOSTS_PW,
                            os_type='rhel', nic=config.HOST_NICS[1],
                            nic_down=False)

        self.assertTrue(monitor.getResult())

    @classmethod
    def teardown_class(cls):
        """
        Remove network from the setup.
        """
        logger.info("Remove networks from setup")
        if not removeNetFromSetup(host=config.HOSTS,
                                  auto_nics=[config.HOST_NICS[0]],
                                  network=[config.NETWORKS[0],
                                           config.NETWORKS[1]]):
            raise NetworkException("Cannot remove network from setup")


@attr(tier=1)
class MigrationCase10(TestCase):
    """
    Verify dedicated regular tagged network migration over Bond
    """
    __test__ = len(config.HOST_NICS) > 3

    @classmethod
    def setup_class(cls):
        """
        Create logical tagged network on DC/Cluster
        Configure it as migration network and attach it to Bond on the Host
        """
        local_dict = {None: {'nic': config.BOND[0], 'mode': 1,
                             'slaves': [config.HOST_NICS[2],
                                        config.HOST_NICS[3]]},
                      config.VLAN_NETWORKS[0]: {'nic': config.BOND[0],
                                                'vlan_id': config.VLAN_ID[0],
                                                'required': 'true',
                                                'cluster_usages': 'migration',
                                                'bootproto': 'static',
                                                'address': [SOURCE_IP,
                                                            DEST_IP],
                                                'netmask': [NETMASK,
                                                            NETMASK]},
                      config.NETWORKS[1]: {'nic': config.HOST_NICS[1],
                                           'required': 'true'}}
        if not createAndAttachNetworkSN(data_center=config.DC_NAME[0],
                                        cluster=config.CLUSTER_NAME[0],
                                        host=config.HOSTS,
                                        network_dict=local_dict,
                                        auto_nics=[config.HOST_NICS[0]]):
            raise NetworkException("Cannot create and attach network")

    @istest
    @tcms(8735, 260608)
    def dedicated_migration_vlan_bond(self):
        """
        Check migration over dedicated tagged network over bond
        """
        orig_host = get_host(config.VM_NAME[0])
        logger.info("Start migration from %s ", orig_host)
        src, dst = find_ip(vm=config.VM_NAME[0],
                           host_list=config.HOSTS,
                           nic='.'.join([config.BOND[0], config.VLAN_ID[0]]))
        if not checkICMPConnectivity(host=orig_host, user=config.HOSTS_USER,
                                     password=config.HOSTS_PW, ip=dst):
            logger.error("ICMP wasn't established")
        with TrafficMonitor(machine=orig_host, user=config.HOSTS_USER,
                            password=config.HOSTS_PW,
                            nic='.'.join([config.BOND[0], config.VLAN_ID[0]]),
                            src=src, dst=dst,
                            protocol='tcp', numPackets=NUM_PACKETS) as monitor:
            monitor.addTask(check_vm_migration,
                            vm_names=config.VM_NAME[0],
                            orig_host=orig_host, vm_user=config.HOSTS_USER,
                            host_password=config.HOSTS_PW,
                            vm_password=config.HOSTS_PW,
                            os_type='rhel')
        self.assertTrue(monitor.getResult())

    @istest
    @tcms(8735, 260605)
    def dedicated_migration_vlan_bond_nic(self):
        """
        Check migration over dedicated tagged network over bond
        Disconnect the nic with required network to do it
        """
        orig_host = get_host(config.VM_NAME[0])
        logger.info("Returning VMs back to original host over bond ")
        logger.info("Start migration from %s ", orig_host)
        src, dst = find_ip(vm=config.VM_NAME[0],
                           host_list=config.HOSTS,
                           nic='.'.join([config.BOND[0], config.VLAN_ID[0]]))
        if not setHostToNonOperational(orig_host=orig_host,
                                       host_password=config.HOSTS_PW,
                                       nic=config.HOST_NICS[1]):
            raise NetworkException("Cannot start migration by putting"
                                   " Nic %s down", config.HOST_NICS[1])

        with TrafficMonitor(timeout=200, machine=orig_host,
                            user=config.HOSTS_USER,
                            password=config.HOSTS_PW,
                            nic='.'.join([config.BOND[0], config.VLAN_ID[0]]),
                            src=src, dst=dst,
                            protocol='tcp', numPackets=NUM_PACKETS) as monitor:
            monitor.addTask(check_vm_migration,
                            vm_names=config.VM_NAME[0],
                            orig_host=orig_host, vm_user=config.HOSTS_USER,
                            host_password=config.HOSTS_PW,
                            vm_password=config.HOSTS_PW,
                            os_type='rhel', nic=config.HOST_NICS[1],
                            nic_down=False)
        self.assertTrue(monitor.getResult())

    @classmethod
    def teardown_class(cls):
        """
        Remove network from the setup.
        """
        logger.info("Remove networks from setup")
        if not removeNetFromSetup(host=config.HOSTS,
                                  auto_nics=[config.HOST_NICS[0]],
                                  network=[config.VLAN_NETWORKS[0],
                                           config.NETWORKS[1]]):
            raise NetworkException("Cannot remove network from setup")


@attr(tier=1)
class MigrationCase11(TestCase):
    """
    Verify  migration over mgmt network when dedicated migration network is
    removed
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Create logical regular migration network on DC/Cluster/Hosts
        """
        local_dict = {config.NETWORKS[0]: {'nic': config.HOST_NICS[1],
                                           'required': 'true',
                                           'cluster_usages': 'migration',
                                           'bootproto': 'static',
                                           'address': [SOURCE_IP, DEST_IP],
                                           'netmask': [NETMASK,
                                                       NETMASK]},
                      config.NETWORKS[1]: {'nic': config.HOST_NICS[2],
                                           'required': 'true'}}
        if not createAndAttachNetworkSN(data_center=config.DC_NAME[0],
                                        cluster=config.CLUSTER_NAME[0],
                                        host=config.HOSTS,
                                        network_dict=local_dict,
                                        auto_nics=[config.HOST_NICS[0]]):
            raise NetworkException("Cannot create and attach network")

    @istest
    @tcms(8735, 250469)
    def mgmt_network_migration(self):
        """
        Check migration over mgmt network when migration network is changed to
        display
        """
        logger.info("Replace migration from the network with display network")
        if not updateClusterNetwork(True, cluster=config.CLUSTER_NAME[0],
                                    network=config.NETWORKS[0],
                                    usages='display'):
            raise NetworkException("Cannot update network usages param")
        orig_host = get_host(config.VM_NAME[0])
        logger.info("Start migration from %s ", orig_host)
        logger.info("Make sure the migration is over mgmt network")
        src, dst = find_ip(vm=config.VM_NAME[0],
                           host_list=config.HOSTS, nic=config.HOST_NICS[1])
        if not checkICMPConnectivity(host=orig_host, user=config.HOSTS_USER,
                                     password=config.HOSTS_PW, ip=dst):
            logger.error("ICMP wasn't established")

        source_ip, dest_ip = find_ip(vm=config.VM_NAME[0],
                                     host_list=config.HOSTS,
                                     nic=config.HOST_NICS[0])

        with TrafficMonitor(machine=orig_host,
                            user=config.HOSTS_USER,
                            password=config.HOSTS_PW,
                            nic=config.HOST_NICS[0],
                            src=source_ip, dst=dest_ip,
                            protocol='tcp', numPackets=NUM_PACKETS) as monitor:
            monitor.addTask(check_vm_migration,
                            vm_names=config.VM_NAME[0],
                            orig_host=orig_host, vm_user=config.HOSTS_USER,
                            host_password=config.HOSTS_PW,
                            vm_password=config.HOSTS_PW,
                            os_type='rhel')
            monitor.addTask(checkTraffic, expectedRes=False,
                            machine=orig_host, user=config.HOSTS_USER,
                            password=config.HOSTS_PW,
                            nic=config.HOST_NICS[1],
                            src=src, dst=dst)
        self.assertTrue(monitor.getResult())

    @classmethod
    def teardown_class(cls):
        """
        Remove network from the setup.
        """
        logger.info("Remove networks from setup")
        if not removeNetFromSetup(host=config.HOSTS,
                                  auto_nics=[config.HOST_NICS[0]],
                                  network=[config.NETWORKS[0],
                                           config.NETWORKS[1]]):
            raise NetworkException("Cannot remove network from setup")


@attr(tier=1)
class MigrationCase12(TestCase):
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
        logger.info("Create migration network and put it only on Host1")
        local_dict = {config.NETWORKS[0]: {'nic': config.HOST_NICS[1],
                                           'required': 'true',
                                           'cluster_usages': 'migration',
                                           'bootproto': 'static',
                                           'address': [SOURCE_IP],
                                           'netmask': [NETMASK]}}
        if not createAndAttachNetworkSN(data_center=config.DC_NAME[0],
                                        cluster=config.CLUSTER_NAME[0],
                                        host=config.HOSTS[0],
                                        network_dict=local_dict,
                                        auto_nics=[config.HOST_NICS[0]]):
            raise NetworkException("Cannot create and attach network")

    @istest
    @tcms(8735, 260613)
    def dedicated_migration(self):
        """
        Check dedicated network migration
        """
        orig_host = get_host(config.VM_NAME[0])
        logger.info("Start migration from %s ", orig_host)
        logger.info("Make sure the migration is over mgmt network")

        source_ip, dest_ip = find_ip(vm=config.VM_NAME[0],
                                     host_list=config.HOSTS,
                                     nic=config.HOST_NICS[0])

        with TrafficMonitor(machine=orig_host,
                            user=config.HOSTS_USER,
                            password=config.HOSTS_PW,
                            nic=config.HOST_NICS[0],
                            src=source_ip, dst=dest_ip,
                            protocol='tcp', numPackets=NUM_PACKETS) as monitor:
            monitor.addTask(check_vm_migration,
                            vm_names=config.VM_NAME[0],
                            orig_host=orig_host, vm_user=config.HOSTS_USER,
                            host_password=config.HOSTS_PW,
                            vm_password=config.HOSTS_PW,
                            os_type='rhel')
        self.assertTrue(monitor.getResult())

    @classmethod
    def teardown_class(cls):
        """
        Remove network from the setup.
        """
        logger.info("Remove networks from setup")
        if not removeNetFromSetup(host=config.HOSTS,
                                  auto_nics=[config.HOST_NICS[0]],
                                  network=[config.NETWORKS[0]]):
            raise NetworkException("Cannot remove network from setup")
