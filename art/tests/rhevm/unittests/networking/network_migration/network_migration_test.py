#! /usr/bin/python

from nose.tools import istest
from unittest import TestCase
from art.test_handler.tools import tcms
import time
import logging

from art.rhevm_api.utils.test_utils import get_api, checkTraffic
from art.test_handler.exceptions import NetworkException, VMException
from art.test_handler.settings import opts

import config
from art.rhevm_api.tests_lib.high_level.networks import\
    createAndAttachNetworkSN, removeNetFromSetup, TrafficMonitor
from art.rhevm_api.tests_lib.low_level.networks import\
    updateClusterNetwork
from art.rhevm_api.tests_lib.low_level.hosts import \
    ifdownNic, ifupNic, activateHost, waitForHostsStates
from art.rhevm_api.tests_lib.low_level.vms import addNic, removeNic,\
    updateNic, waitForVMState, getVmHost
from art.rhevm_api.tests_lib.high_level.vms import check_vm_migration
from art.unittest_lib.network import skipBOND
HOST_API = get_api('host', 'hosts')
VM_API = get_api('vm', 'vms')

logger = logging.getLogger(__package__ + __name__)

ENUMS = opts['elements_conf']['RHEVM Enums']
NUM_PACKETS = 1000

########################################################################

########################################################################
#                             Test Cases                               #
########################################################################

'''
    There is an opened bug 982634 - migration fails when there is no sleep
    between creating network and migration itself
    That is the reason we are using time.sleep in all our tests.
    The moment the bug will be solved it will be removed
'''


class Migration_Case1_256582_250476(TestCase):
    '''
    Verify dedicated regular network migration
    '''
    __test__ = True

    @classmethod
    def setup_class(cls):
        '''
        Create logical vm network on DC/Cluster/Hosts
        Configure it as migration network
        '''
        local_dict = {config.NETWORKS[0]: {'nic': config.HOST_NICS[1],
                                           'required': 'false',
                                           'cluster_usages': 'migration',
                                           'bootproto': 'static',
                                           'address': ['1.1.1.1', '1.1.1.2'],
                                           'netmask': ['255.255.255.0',
                                                       '255.255.255.0']},
                      config.NETWORKS[1]: {'nic': config.HOST_NICS[2],
                                           'required': 'true'}}
        if not createAndAttachNetworkSN(data_center=config.DC_NAME,
                                        cluster=config.CLUSTER_NAME,
                                        host=config.HOSTS,
                                        network_dict=local_dict,
                                        auto_nics=[config.HOST_NICS[0]]):
            raise NetworkException("Cannot create and attach network")

        time.sleep(30)

    @istest
    @tcms(8735, 256582)
    def dedicated_migration(self):
        '''
        Check dedicated network migration
        '''
        orig_host = getHost(config.VM_NAME[0])
        logger.info("Start migration from %s ", orig_host)
        logger.info("Migrating VM over migration network")
        src, dst = find_ip(orig_host)

        with TrafficMonitor(machine=orig_host, user='root',
                            password='qum5net', nic=config.HOST_NICS[1],
                            src=src, dst=dst,
                            protocol='tcp', numPackets=NUM_PACKETS) as monitor:
            monitor.addTask(check_vm_migration,
                            vm_names=config.VM_NAME[0],
                            orig_host=orig_host, vm_user=config.HOSTS_USER,
                            host_password=config.HOSTS_PW[0],
                            vm_password=config.HOSTS_PW[0],
                            os_type='rhel')
        self.assertTrue(monitor.getResult())

    @istest
    @tcms(8735, 250476)
    def dedicated_migration_nic(self):
        '''
        Check dedicated network migration by putting req net down
        '''
        orig_host = getHost(config.VM_NAME[0])

        logger.info("Returning VMs back to original host over migration net")
        logger.info("Start migration from %s ", orig_host)
        orig_host = getHost(config.VM_NAME[0])
        src, dst = find_ip(orig_host)

        with TrafficMonitor(machine=orig_host, user=config.HOSTS_USER,
                            password=config.HOSTS_PW[0],
                            nic=config.HOST_NICS[1],
                            src=src, dst=dst,
                            protocol='tcp', numPackets=NUM_PACKETS) as monitor:
            monitor.addTask(check_vm_migration,
                            vm_names=config.VM_NAME[0],
                            orig_host=orig_host, vm_user=config.HOSTS_USER,
                            host_password=config.HOSTS_PW[0],
                            vm_password=config.HOSTS_PW[0],
                            os_type='rhel')
        self.assertTrue(monitor.getResult())

    @classmethod
    def teardown_class(cls):
        '''
        Remove network from the setup.
        '''
        logger.info("Remove networks from setup")
        if not removeNetFromSetup(host=config.HOSTS,
                                  auto_nics=[config.HOST_NICS[0]],
                                  network=[config.NETWORKS[0],
                                           config.NETWORKS[1]]):
            raise NetworkException("Cannot remove network from setup")


class Migration_Case2_250464(TestCase):
    """
    Verify default migration when no migration network specified
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        '''
        Create logical vm network on DC/Cluster/Hosts
        '''
        logger.info("Create non-migration network on DC/Cluster/Hosts")
        local_dict = {config.NETWORKS[0]: {'nic': config.HOST_NICS[1],
                                           'required': 'true',
                                           'bootproto': 'static',
                                           'address': ['1.1.1.1', '1.1.1.2'],
                                           'netmask': ['255.255.255.0',
                                                       '255.255.255.0']}}

        if not createAndAttachNetworkSN(data_center=config.DC_NAME,
                                        cluster=config.CLUSTER_NAME,
                                        host=config.HOSTS,
                                        network_dict=local_dict,
                                        auto_nics=[config.HOST_NICS[0]]):
            raise NetworkException("Cannot create and attach network")

    @istest
    @tcms(8735, 250464)
    def default_migration(self):
        """
        Check default migration on rhevm network
        """
        orig_host = getHost(config.VM_NAME[0])
        logger.info("Start migration from %s ", orig_host)
        logger.info("Migrating VM over rhevm network")
        src, dst = find_ip(orig_host)
        source_ip = HOST_API.find(orig_host).get_address()
        dest_ip = HOST_API.find(config.HOSTS[1]).get_address()
        if orig_host == config.HOSTS[1]:
            dest_ip = HOST_API.find(config.HOSTS[0]).get_address()

        with TrafficMonitor(machine=orig_host,
                            user=config.HOSTS_USER,
                            password=config.HOSTS_PW[0],
                            nic=config.HOST_NICS[0],
                            src=source_ip, dst=dest_ip,
                            protocol='tcp', numPackets=NUM_PACKETS) as monitor:
            monitor.addTask(check_vm_migration,
                            vm_names=config.VM_NAME[0],
                            orig_host=orig_host, vm_user=config.HOSTS_USER,
                            host_password=config.HOSTS_PW[0],
                            vm_password=config.HOSTS_PW[0],
                            os_type='rhel')
            monitor.addTask(checkTraffic, expectedRes=False,
                            machine=orig_host, user=config.HOSTS_USER,
                            password=config.HOSTS_PW[0],
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


class Migration_Case3_250466_256583(TestCase):
    """
    Verify dedicated migration over tagged network over NIC
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        '''
        Create logical tagged vm network on DC/Cluster/Hosts
        '''
        local_dict = {config.VLAN_NETWORKS[0]: {'vlan_id': config.VLAN_ID[0],
                                                'nic': config.HOST_NICS[1],
                                                'required': 'false',
                                                'cluster_usages': 'migration',
                                                'bootproto': 'static',
                                                'address': ['1.1.1.1',
                                                            '1.1.1.2'],
                                                'netmask': ['255.255.255.0',
                                                            '255.255.255.0']},
                      config.VLAN_NETWORKS[1]: {'vlan_id': config.VLAN_ID[1],
                                                'nic': config.HOST_NICS[2],
                                                'required': 'true'
                                                }}
        if not createAndAttachNetworkSN(data_center=config.DC_NAME,
                                        cluster=config.CLUSTER_NAME,
                                        host=config.HOSTS,
                                        network_dict=local_dict,
                                        auto_nics=[config.HOST_NICS[0],
                                                   config.HOST_NICS[1],
                                                   config.HOST_NICS[2]]):
            raise NetworkException("Cannot create and attach network")

        time.sleep(30)

    @istest
    @tcms(8735, 250466)
    def dedicated_tagged_migration(self):
        """
        Check dedicated migration over tagged network over NIC
        """
        orig_host = getHost(config.VM_NAME[0])
        logger.info("Start migration from %s ", orig_host)
        logger.info("Migrating VM over migration network")
        src, dst = find_ip(orig_host)

        with TrafficMonitor(machine=orig_host, user=config.HOSTS_USER,
                            password=config.HOSTS_PW[0],
                            nic=config.HOST_NICS[1],
                            src=src, dst=dst,
                            protocol='tcp', numPackets=NUM_PACKETS) as monitor:
            monitor.addTask(check_vm_migration,
                            vm_names=config.VM_NAME[0],
                            orig_host=orig_host, vm_user=config.HOSTS_USER,
                            host_password=config.HOSTS_PW[0],
                            vm_password=config.HOSTS_PW[0],
                            os_type='rhel')
        self.assertTrue(monitor.getResult())

    @istest
    @tcms(8735, 256583)
    def dedicated_tagged_migration_nic(self):
        """
        Check dedicated migration over tagged network by putting req net down
        """
        orig_host = getHost(config.VM_NAME[0])
        logger.info("Returning VMs back to original host")
        logger.info("Start migration from %s ", orig_host)
        logger.info("Migrating VM over migration network")
        src, dst = find_ip(orig_host)

        with TrafficMonitor(machine=orig_host, user=config.HOSTS_USER,
                            password=config.HOSTS_PW[0],
                            nic=config.HOST_NICS[1],
                            src=src, dst=dst,
                            protocol='tcp', numPackets=NUM_PACKETS) as monitor:
            monitor.addTask(check_vm_migration,
                            vm_names=config.VM_NAME[0],
                            orig_host=orig_host, vm_user=config.HOSTS_USER,
                            host_password=config.HOSTS_PW[0],
                            vm_password=config.HOSTS_PW[0],
                            os_type='rhel')
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


class Migration_Case4_260555_260554(TestCase):
    """
    Verify dedicated migration over non-VM network over NIC
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        '''
        Create logical non-vm network on DC/Cluster/Hosts
        '''
        local_dict = {config.NETWORKS[0]: {'nic': config.HOST_NICS[1],
                                           'required': 'false',
                                           'usages': '',
                                           'cluster_usages': 'migration',
                                           'bootproto': 'static',
                                           'address': ['1.1.1.1', '1.1.1.2'],
                                           'netmask': ['255.255.255.0',
                                                       '255.255.255.0']},
                      config.NETWORKS[1]: {'nic': config.HOST_NICS[2],
                                           'required': 'true'}}
        if not createAndAttachNetworkSN(data_center=config.DC_NAME,
                                        cluster=config.CLUSTER_NAME,
                                        host=config.HOSTS,
                                        network_dict=local_dict,
                                        auto_nics=[config.HOST_NICS[0]]):
            raise NetworkException("Cannot create and attach network")

        time.sleep(30)

    @istest
    @tcms(8735, 260555)
    def nonvm_migration(self):
        """
        Check dedicated migration over non-VM network over NIC
        """
        orig_host = getHost(config.VM_NAME[0])
        logger.info("Start migration from %s ", orig_host)
        src, dst = find_ip(orig_host)

        with TrafficMonitor(machine=orig_host, user=config.HOSTS_USER,
                            password=config.HOSTS_PW[0],
                            nic=config.HOST_NICS[1],
                            src=src, dst=dst,
                            protocol='tcp', numPackets=NUM_PACKETS) as monitor:
            monitor.addTask(check_vm_migration,
                            vm_names=config.VM_NAME[0],
                            orig_host=orig_host, vm_user=config.HOSTS_USER,
                            host_password=config.HOSTS_PW[0],
                            vm_password=config.HOSTS_PW[0],
                            os_type='rhel')
        self.assertTrue(monitor.getResult())

    @istest
    @tcms(8735, 260554)
    def nonvm_migration_nic(self):
        """
        Check dedicated migration over non-VM network by putting req net down
        """
        orig_host = getHost(config.VM_NAME[0])
        logger.info("Returning VMs back to original host")
        logger.info("Start migration from %s ", orig_host)
        src, dst = find_ip(orig_host)

        with TrafficMonitor(machine=orig_host, user=config.HOSTS_USER,
                            password=config.HOSTS_PW[0],
                            nic=config.HOST_NICS[1],
                            src=src, dst=dst,
                            protocol='tcp', numPackets=NUM_PACKETS) as monitor:
            monitor.addTask(check_vm_migration,
                            vm_names=config.VM_NAME[0],
                            orig_host=orig_host, vm_user=config.HOSTS_USER,
                            host_password=config.HOSTS_PW[0],
                            vm_password=config.HOSTS_PW[0],
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
                                  network=[config.NETWORKS[0],
                                           config.NETWORKS[1]]):
            raise NetworkException("Cannot remove network from setup")


class Migration_Case5_250810(TestCase):
    """
    Verify dedicated regular network migration when its also display network
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        '''
        Create logical vm network on DC/Cluster/Hosts
        Configure it as migration and display network
        '''
        local_dict = \
            {config.NETWORKS[0]: {'nic': config.HOST_NICS[1],
                                  'required': 'false',
                                  'cluster_usages': 'migration,display',
                                  'bootproto': 'static',
                                  'address': ['1.1.1.1', '1.1.1.2'],
                                  'netmask': ['255.255.255.0',
                                              '255.255.255.0']},
             config.NETWORKS[1]: {'nic': config.HOST_NICS[2],
                                  'required': 'true'}}
        if not createAndAttachNetworkSN(data_center=config.DC_NAME,
                                        cluster=config.CLUSTER_NAME,
                                        host=config.HOSTS,
                                        network_dict=local_dict,
                                        auto_nics=[config.HOST_NICS[0]]):
            raise NetworkException("Cannot create and attach network")

        time.sleep(30)

    @istest
    @tcms(8735, 250810)
    def dedicated_migration(self):
        """
        Check dedicated network migration over display network
        """
        orig_host = getHost(config.VM_NAME[0])
        logger.info("Start migration from %s ", orig_host)
        src, dst = find_ip(orig_host)

        with TrafficMonitor(machine=orig_host, user=config.HOSTS_USER,
                            password=config.HOSTS_PW[0],
                            nic=config.HOST_NICS[1],
                            src=src, dst=dst,
                            protocol='tcp', numPackets=NUM_PACKETS) as monitor:
            monitor.addTask(check_vm_migration,
                            vm_names=config.VM_NAME[0],
                            orig_host=orig_host, vm_user=config.HOSTS_USER,
                            host_password=config.HOSTS_PW[0],
                            vm_password=config.HOSTS_PW[0],
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


class Migration_Case6_250915(TestCase):
    """
    Verify dedicated regular network migration when the net reside on the VM
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        '''
        Create logical vm network on DC/Cluster/Hosts
        Configure it as migration and configure it on the VM
        '''
        local_dict = {config.NETWORKS[0]: {'nic': config.HOST_NICS[1],
                                           'required': 'false',
                                           'cluster_usages': 'migration',
                                           'bootproto': 'static',
                                           'address': ['1.1.1.1', '1.1.1.2'],
                                           'netmask': ['255.255.255.0',
                                                       '255.255.255.0']},
                      config.NETWORKS[1]: {'nic': config.HOST_NICS[2],
                                           'required': 'true'}}

        logger.info("Configure migration network on the DC/Cluster/Host")
        if not createAndAttachNetworkSN(data_center=config.DC_NAME,
                                        cluster=config.CLUSTER_NAME,
                                        host=config.HOSTS,
                                        network_dict=local_dict,
                                        auto_nics=[config.HOST_NICS[0]]):
            raise NetworkException("Cannot create and attach network")
        logger.info("Creating VNICs with default plugged/linked states")
        if not addNic(True, config.VM_NAME[0], name='nic2',
                      network=config.NETWORKS[0]):
            raise VMException("Cannot add VNIC to VM")

        time.sleep(30)

    @istest
    @tcms(8735, 256582)
    def dedicated_migration(self):
        """
        Check dedicated network migration when network resides on VM
        """
        orig_host = getHost(config.VM_NAME[0])
        logger.info("Start migration from %s ", orig_host)
        src, dst = find_ip(orig_host)

        with TrafficMonitor(machine=orig_host, user=config.HOSTS_USER,
                            password=config.HOSTS_PW[0],
                            nic=config.HOST_NICS[1],
                            src=src, dst=dst,
                            protocol='tcp', numPackets=NUM_PACKETS) as monitor:
            monitor.addTask(check_vm_migration,
                            vm_names=config.VM_NAME[0],
                            orig_host=orig_host, vm_user=config.HOSTS_USER,
                            host_password=config.HOSTS_PW[0],
                            vm_password=config.HOSTS_PW[0],
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


class Migration_Case7_285179(TestCase):
    """
    Verify migration over rhevm when migration network is not attached to Hosts
    Migration Network is attached only to DC and Cluster
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        '''
        Create logical vm network on DC/Cluster
        Configure it as migration network
        '''
        local_dict = {config.NETWORKS[0]: {'nic': config.HOST_NICS[1],
                                           'required': 'false',
                                           'cluster_usages': 'migration'}}
        if not createAndAttachNetworkSN(data_center=config.DC_NAME,
                                        cluster=config.CLUSTER_NAME,
                                        network_dict=local_dict):
            raise NetworkException("Cannot create and attach network to DC/CL")

    @istest
    @tcms(8735, 256582)
    def rhevm_migration(self):
        """
        Check rhevm network migration
        """
        orig_host = getHost(config.VM_NAME[0])
        logger.info("Start migration from %s ", orig_host)
        logger.info("Checking that the migration traffic is on rhevm network")
        source_ip = HOST_API.find(orig_host).get_address()
        dest_ip = HOST_API.find(config.HOSTS[1]).get_address()
        if orig_host == config.HOSTS[1]:
            dest_ip = HOST_API.find(config.HOSTS[0]).get_address()

        with TrafficMonitor(machine=orig_host, user=config.HOSTS_USER,
                            password=config.HOSTS_PW[0],
                            nic=config.HOST_NICS[0],
                            src=source_ip, dst=dest_ip,
                            protocol='tcp', numPackets=NUM_PACKETS) as monitor:
            monitor.addTask(check_vm_migration,
                            vm_names=config.VM_NAME[0],
                            orig_host=orig_host, vm_user=config.HOSTS_USER,
                            host_password=config.HOSTS_PW[0],
                            vm_password=config.HOSTS_PW[0],
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


class Migration_Case8_260607(TestCase):
    """
    Verify dedicated regular network migration over Bond
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        '''
        Create logical vm network on DC/Cluster/Hosts
        Configure it as migration network and attach it to Bond
        '''
        local_dict = {config.NETWORKS[0]: {'nic': 'bond0',
                                           'slaves': [config.HOST_NICS[2],
                                                      config.HOST_NICS[3]],
                                           'required': 'false',
                                           'cluster_usages': 'migration',
                                           'bootproto': 'static',
                                           'address': ['1.1.1.1', '1.1.1.2'],
                                           'netmask': ['255.255.255.0',
                                                       '255.255.255.0']},
                      config.NETWORKS[1]: {'nic': config.HOST_NICS[1],
                                           'required': 'true'}}
        if not createAndAttachNetworkSN(data_center=config.DC_NAME,
                                        cluster=config.CLUSTER_NAME,
                                        host=config.HOSTS,
                                        network_dict=local_dict,
                                        auto_nics=[config.HOST_NICS[0]]):
            raise NetworkException("Cannot create and attach network")

        time.sleep(30)

    @istest
    @tcms(8735, 260607)
    def dedicated_migration_bond(self):
        """
        Check dedicated network migration over bond
        """
        orig_host = getHost(config.VM_NAME[0])
        logger.info("Start migration from %s ", orig_host)
        src, dst = find_ip(orig_host)

        with TrafficMonitor(machine=orig_host, user=config.HOSTS_USER,
                            password=config.HOSTS_PW[0],
                            nic='bond0',
                            src=src, dst=dst,
                            protocol='tcp', numPackets=NUM_PACKETS) as monitor:
            monitor.addTask(check_vm_migration,
                            vm_names=config.VM_NAME[0],
                            orig_host=orig_host, vm_user=config.HOSTS_USER,
                            host_password=config.HOSTS_PW[0],
                            vm_password=config.HOSTS_PW[0],
                            os_type='rhel')
        self.assertTrue(monitor.getResult())

    @istest
    @tcms(8735, 260604)
    def dedicated_migration_bond_nic(self):
        """
        Check dedicated network migration over bond putting req net down
        """
        orig_host = getHost(config.VM_NAME[0])
        logger.info("Returning VMs back to original host over bond ")
        logger.info("Start migration from %s ", orig_host)
        src, dst = find_ip(orig_host)

        with TrafficMonitor(machine=orig_host, user=config.HOSTS_USER,
                            password=config.HOSTS_PW[0],
                            nic='bond0',
                            src=src, dst=dst,
                            protocol='tcp', numPackets=NUM_PACKETS) as monitor:
            monitor.addTask(check_vm_migration,
                            vm_names=config.VM_NAME[0],
                            orig_host=orig_host, vm_user=config.HOSTS_USER,
                            host_password=config.HOSTS_PW[0],
                            vm_password=config.HOSTS_PW[0],
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
                                  network=[config.NETWORKS[0],
                                           config.NETWORKS[1]]):
            raise NetworkException("Cannot remove network from setup")


class Migration_Case9_260606(TestCase):
    """
    Verify dedicated regular non-vm network migration over Bond
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        '''
        Create logical non-vm network on DC/Cluster
        Configure it as migration network and attach it to Bond on the Host
        '''
        local_dict = {config.NETWORKS[0]: {'nic': 'bond0',
                                           'slaves': [config.HOST_NICS[2],
                                                      config.HOST_NICS[3]],
                                           'required': 'false',
                                           'usages': '',
                                           'cluster_usages': 'migration',
                                           'bootproto': 'static',
                                           'address': ['1.1.1.1', '1.1.1.2'],
                                           'netmask': ['255.255.255.0',
                                                       '255.255.255.0']},
                      config.NETWORKS[1]: {'nic': config.HOST_NICS[1],
                                           'required': 'true'}}
        if not createAndAttachNetworkSN(data_center=config.DC_NAME,
                                        cluster=config.CLUSTER_NAME,
                                        host=config.HOSTS,
                                        network_dict=local_dict,
                                        auto_nics=[config.HOST_NICS[0]]):
            raise NetworkException("Cannot create and attach network")

        time.sleep(30)

    @istest
    @tcms(8735, 260606)
    def dedicated_migration_nonvm_bond(self):
        """
        Check migration over dedicated non-vm network over bond
        """
        orig_host = getHost(config.VM_NAME[0])
        logger.info("Start migration from %s ", orig_host)
        src, dst = find_ip(orig_host)

        with TrafficMonitor(machine=orig_host, user=config.HOSTS_USER,
                            password=config.HOSTS_PW[0],
                            nic='bond0',
                            src=src, dst=dst,
                            protocol='tcp', numPackets=NUM_PACKETS) as monitor:
            monitor.addTask(check_vm_migration,
                            vm_names=config.VM_NAME[0],
                            orig_host=orig_host, vm_user=config.HOSTS_USER,
                            host_password=config.HOSTS_PW[0],
                            vm_password=config.HOSTS_PW[0],
                            os_type='rhel')
        self.assertTrue(monitor.getResult())

    @istest
    @tcms(8735, 260603)
    def dedicated_migration_nonvm_bond_nic(self):
        """
        Check migration over dedicated non-vm network over bond
        Do it by turning down NIC with required network
        """
        orig_host = getHost(config.VM_NAME[0])
        logger.info("Returning VMs back to original host over bond ")
        logger.info("Start migration from %s ", orig_host)
        src, dst = find_ip(orig_host)

        with TrafficMonitor(machine=orig_host, user=config.HOSTS_USER,
                            password=config.HOSTS_PW[0],
                            nic='bond0',
                            src=src, dst=dst,
                            protocol='tcp', numPackets=NUM_PACKETS) as monitor:
            monitor.addTask(check_vm_migration,
                            vm_names=config.VM_NAME[0],
                            orig_host=orig_host, vm_user=config.HOSTS_USER,
                            host_password=config.HOSTS_PW[0],
                            vm_password=config.HOSTS_PW[0],
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
                                  network=[config.NETWORKS[0],
                                           config.NETWORKS[1]]):
            raise NetworkException("Cannot remove network from setup")


class Migration_Case10_260608(TestCase):
    """
    Verify dedicated regular tagged network migration over Bond
    """
    __test__ = False

    @classmethod
    def setup_class(cls):
        '''
        Create logical tagged network on DC/Cluster
        Configure it as migration network and attach it to Bond on the Host
        '''
        local_dict = {None: {'nic': 'bond0', 'mode': 1,
                             'slaves': [config.HOST_NICS[2],
                                        config.HOST_NICS[3]]},
                      config.VLAN_NETWORKS[0]: {'nic': 'bond0',
                                                'vlan_id': config.VLAN_ID[0],
                                                'required': 'false',
                                                'cluster_usages': 'migration',
                                                'bootproto': 'static',
                                                'address': ['1.1.1.1',
                                                            '1.1.1.2'],
                                                'netmask': ['255.255.255.0',
                                                       '255.255.255.0']},
                      config.NETWORKS[1]: {'nic': config.HOST_NICS[1],
                                           'required': 'true'}}
        if not createAndAttachNetworkSN(data_center=config.DC_NAME,
                                        cluster=config.CLUSTER_NAME,
                                        host=config.HOSTS,
                                        network_dict=local_dict,
                                        auto_nics=[config.HOST_NICS[0]]):
            raise NetworkException("Cannot create and attach network")

        time.sleep(30)

    @istest
    #tcms(8735, 260608)
    def dedicated_migration_vlan_bond(self):
        """
        Check migration over dedicated tagged network over bond
        """
        orig_host = getHost(config.VM_NAME[0])
        logger.info("Start migration from %s ", orig_host)
        src, dst = find_ip(orig_host)

        self.assertTrue(check_vm_migration(vm_names=config.VM_NAME[0],
                                           orig_host=orig_host,
                                           vm_user=config.HOSTS_USER,
                                           host_password=config.HOSTS_PW[0],
                                           vm_password=config.HOSTS_PW[0],
                                           os_type='rhel'))

    @istest
    #tcms(8735, 260605)
    def dedicated_migration_vlan_bond_nic(self):
        """
        Check migration over dedicated tagged network over bond
        Disconnect the nic with required network to do it
        """
        orig_host = getHost(config.VM_NAME[0])
        logger.info("Returning VMs back to original host over bond ")
        logger.info("Start migration from %s ", orig_host)
        self.assertTrue(check_vm_migration(vm_names=config.VM_NAME[0],
                                           orig_host=orig_host,
                                           vm_user=config.HOSTS_USER,
                                           host_password=config.HOSTS_PW[0],
                                           vm_password=config.HOSTS_PW[0],
                                           os_type='rhel',
                                           nic=config.HOST_NICS[1]))

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


class Migration_Case11_260611(TestCase):
    """
    Test is false till it will run on specific hosts with configured MTU
    Verify dedicated regular tagged network migration over Bond with MTU 9000
    """
    __test__ = False

    @classmethod
    def setup_class(cls):
        '''
        Create logical tagged network on DC/Cluster with MTU 9000
        Configure it as migration network and attach it to Bond on the Host
        '''
        local_dict = {None: {'nic': 'bond0', 'mode': 1,
                             'slaves': [config.HOST_NICS[2],
                                        config.HOST_NICS[3]]},
                      config.VLAN_NETWORKS[0]: {'nic': 'bond0', 'mtu': 9000,
                                                'vlan_id': config.VLAN_ID[0],
                                                'required': 'false',
                                                'cluster_usages': 'migration',
                                                'bootproto': 'static',
                                                'address': ['1.1.1.1',
                                                            '1.1.1.2'],
                                                'netmask': ['255.255.255.0',
                                                       '255.255.255.0']},
                      config.NETWORKS[1]: {'nic': config.HOST_NICS[1],
                                           'required': 'true'}}
        if not createAndAttachNetworkSN(data_center=config.DC_NAME,
                                        cluster=config.CLUSTER_NAME,
                                        host=config.HOSTS,
                                        network_dict=local_dict,
                                        auto_nics=[config.HOST_NICS[0]]):
            raise NetworkException("Cannot create and attach network")

        time.sleep(30)

    @istest
    #tcms(8735, 256582)
    def dedicated_migration(self):
        """
        Check migration over dedicated tagged network over bond
        """
        orig_host = getHost(config.VM_NAME[0])
        logger.info("Start migration from %s ", orig_host)
        src, dst = find_ip(orig_host)

        self.assertTrue(check_vm_migration(vm_names=config.VM_NAME[0],
                                           orig_host=orig_host,
                                           vm_user=config.HOSTS_USER,
                                           host_password=config.HOSTS_PW[0],
                                           vm_password=config.HOSTS_PW[0],
                                           os_type='rhel'))

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


class Migration_Case12_250469(TestCase):
    """
    Verify  migration over rhevm when dedicated migration network is removed
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        '''
        Create logical regular migration network on DC/Cluster/Hosts
        '''
        local_dict = {config.NETWORKS[0]: {'nic': config.HOST_NICS[1],
                                           'required': 'false',
                                           'cluster_usages': 'migration',
                                           'bootproto': 'static',
                                           'address': ['1.1.1.1', '1.1.1.2'],
                                           'netmask': ['255.255.255.0',
                                                       '255.255.255.0']},
                      config.NETWORKS[1]: {'nic': config.HOST_NICS[2],
                                           'required': 'true'}}
        if not createAndAttachNetworkSN(data_center=config.DC_NAME,
                                        cluster=config.CLUSTER_NAME,
                                        host=config.HOSTS,
                                        network_dict=local_dict,
                                        auto_nics=[config.HOST_NICS[0]]):
            raise NetworkException("Cannot create and attach network")

    @istest
    @tcms(8735, 250469)
    def rhevm_migration(self):
        """
        Check migration over rhevm when migration network is changed to display
        """
        logger.info("Replace migration from the network with display network")
        if not updateClusterNetwork(True, cluster=config.CLUSTER_NAME,
                                    network=config.NETWORKS[0],
                                    usages='display'):
            raise NetworkException("Cannot update network usages param")
        orig_host = getHost(config.VM_NAME[0])
        logger.info("Start migration from %s ", orig_host)
        logger.info("Make sure the migration is over rhevm network")
        src, dst = find_ip(orig_host)
        source_ip = HOST_API.find(orig_host).get_address()
        dest_ip = HOST_API.find(config.HOSTS[1]).get_address()
        if orig_host == config.HOSTS[1]:
            dest_ip = HOST_API.find(config.HOSTS[0]).get_address()

        with TrafficMonitor(machine=orig_host,
                            user=config.HOSTS_USER,
                            password=config.HOSTS_PW[0],
                            nic=config.HOST_NICS[0],
                            src=source_ip, dst=dest_ip,
                            protocol='tcp', numPackets=NUM_PACKETS) as monitor:
            monitor.addTask(check_vm_migration,
                            vm_names=config.VM_NAME[0],
                            orig_host=orig_host, vm_user=config.HOSTS_USER,
                            host_password=config.HOSTS_PW[0],
                            vm_password=config.HOSTS_PW[0],
                            os_type='rhel')
            monitor.addTask(checkTraffic, expectedRes=False,
                            machine=orig_host, user=config.HOSTS_USER,
                            password=config.HOSTS_PW[0],
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


class Migration_Case13_260613(TestCase):
    '''
    bug 983515 is opened - till then the case is False
    Verify when dedicated regular network migration is not configured on the
    Host the migration will occur on the rhevm network
    '''
    __test__ = False

    @classmethod
    def setup_class(cls):
        '''
        Create logical vm network on DC/Cluster/Hosts
        Configure it as migration network
        '''
        logger.info("Create migration network and put it only on Host1")
        local_dict = {config.NETWORKS[0]: {'nic': config.HOST_NICS[1],
                                           'required': 'false',
                                           'cluster_usages': 'migration',
                                           'bootproto': 'static',
                                           'address': ['1.1.1.1'],
                                           'netmask': ['255.255.255.0']}}
        if not createAndAttachNetworkSN(data_center=config.DC_NAME,
                                        cluster=config.CLUSTER_NAME,
                                        host=config.HOSTS[0],
                                        network_dict=local_dict,
                                        auto_nics=[config.HOST_NICS[0]]):
            raise NetworkException("Cannot create and attach network")

    @istest
    #tcms(8735, 260613)
    def dedicated_migration(self):
        '''
        Check dedicated network migration
        '''
        logger.info("Start migration from %s to %s", config.HOSTS[0],
                    config.HOSTS[1])

        logger.info("Make sure the migration is happening on rhevm network")
        self.assertTrue(check_vm_migration(vm_names=config.VM_NAME[0],
                                           orig_host=config.HOSTS[0],
                                           dest_host=config.HOSTS[1],
                                           vm_user=config.HOSTS_USER,
                                           host_password=config.HOSTS_PW,
                                           vm_password=config.HOSTS_PW,
                                           os_type='rhel'))

        logger.info("Returning VMs back to original host over rhevm net")
        logger.info("Start migration from %s to %s", config.HOSTS[1],
                    config.HOSTS[0])
        logger.info("Make sure the migration is happening on rhevm network")
        self.assertTrue(check_vm_migration(vm_names=config.VM_NAME[0],
                                           orig_host=config.HOSTS[1],
                                           dest_host=config.HOSTS[0],
                                           vm_user=config.HOSTS_USER,
                                           host_password=config.HOSTS_PW,
                                           vm_password=config.HOSTS_PW,
                                           os_type='rhel'))

    @classmethod
    def teardown_class(cls):
        '''
        Remove network from the setup.
        '''
        logger.info("Remove networks from setup")
        if not removeNetFromSetup(host=config.HOSTS,
                                  auto_nics=[config.HOST_NICS[0]],
                                  network=[config.NETWORKS[0]]):
            raise NetworkException("Cannot remove network from setup")


class Migration_Case14_256586(TestCase):
    """
    Verify dedicated migration over tagged network
    The network is changed from required to non-required
    BUG is opened till then __test__= False
    """
    __test__ = False

    @classmethod
    def setup_class(cls):
        '''
        Create logical tagged network on DC/Cluster/Hosts
        '''
        local_dict = {config.VLAN_NETWORKS[0]: {'nic': config.HOST_NICS[1],
                                                'required': 'true',
                                                'vlan_id': config.VLAN_ID[0],
                                                'cluster_usages': 'migration',
                                                'bootproto': 'static',
                                                'address': ['1.1.1.1',
                                                            '1.1.1.2'],
                                                'netmask': ['255.255.255.0',
                                                            '255.255.255.0']}}
        if not createAndAttachNetworkSN(data_center=config.DC_NAME,
                                        cluster=config.CLUSTER_NAME,
                                        host=config.HOSTS,
                                        network_dict=local_dict,
                                        auto_nics=[config.HOST_NICS[0],
                                                   config.HOST_NICS[1]]):
            raise NetworkException("Cannot create and attach network")

    @istest
    #@tcms(8735, 256586)
    def vm_migration(self):
        """
        Take down nic with migration required network
        Change it non-required
        Activate the host after turning the NIC up
        Perform migration
        """
        orig_host = getHost(config.VM_NAME[0])
        logger.info("Turn down the required Network NIC to start migration")
        if not ifdownNic(host=orig_host,
                         root_password=config.HOSTS_PW[0],
                         nic=config.HOST_NICS[1]):
            logger.error("Coudn't disconnect the NIC %s ", config.HOSTS[1])
            return False
        if not waitForHostsStates(True, names=orig_host,
                                  states='nonoperational',
                                  timeout=90):
            logger.error("Host %s is not in non-operational state",
                         config.HOSTS[0])
            return False
        if not waitForVMState(vm=config.VM_NAME[0], state='up', sleep=10,
                              timeout=90):
                logger.error("VM %s is not up after migration",
                             config.VM_NAME[0])
                return False
        logger.info("Changing migration network to be non-required")
        if not updateClusterNetwork(True, cluster=config.CLUSTER_NAME,
                                    network=config.VLAN_NETWORKS[0],
                                    required=False, usages='migration'):
            logger.error("Couldn't update the network to be non-required")
            return False

        logger.info("Put the NIC in the UP state and activate the Host")
        if not ifupNic(host=orig_host,
                       root_password=config.HOSTS_PW[0],
                       nic=config.HOST_NICS[1], wait=False):
            logger.error("Couldn't put NIC %s in up state", orig_host)
            return False

        if not activateHost(True, host=orig_host):
            logger.error("Couldn't activate host %s", orig_host)
            return False
        #logger.info("Start migration from %s to %s", config.HOSTS[1],
        #            config.HOSTS[0])
        orig_host = getHost(config.VM_NAME[0])
        self.assertTrue(check_vm_migration(vm_names=config.VM_NAME[0],
                                           orig_host=orig_host,
                                           vm_user=config.HOSTS_USER,
                                           host_password=config.HOSTS_PW,
                                           vm_password=config.HOSTS_PW,
                                           os_type='rhel'))

    @classmethod
    def teardown_class(cls):
        """
        Remove network from the setup.
        """
        logger.info("Remove networks from setup")
        if not removeNetFromSetup(host=config.HOSTS,
                                  auto_nics=[config.HOST_NICS[0]],
                                  network=[config.VLAN_NETWORKS[0]]):
            raise NetworkException("Cannot remove network from setup")


# Function that returns source and destination ip for specific host
def find_ip(host):
    logger.info("Host is %s", host)
    if host == config.HOSTS[0]:
        return '1.1.1.1', '1.1.1.2'
    else:
        return '1.1.1.2', '1.1.1.1'


#  Function that returns host the specific VM resides on
def getHost(vm):
    rc, out = getVmHost(vm)
    if not rc:
        raise NetworkException("Cannot get host that VM resides on")
    return out['vmHoster']

skipBOND([Migration_Case8_260607, Migration_Case9_260606,
          Migration_Case10_260608, Migration_Case11_260611], config.HOST_NICS)
