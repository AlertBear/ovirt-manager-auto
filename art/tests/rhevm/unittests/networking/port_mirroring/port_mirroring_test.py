#! /usr/bin/python

from nose.tools import istest
from unittest import TestCase
import logging

from art.test_handler.exceptions import VMException
from art.test_handler.settings import opts
from art.test_handler.tools import tcms
from art.rhevm_api.tests_lib.low_level.vms import updateNic, migrateVm,\
    getVmNicPortMirroring
from art.rhevm_api.utils.test_utils import configureTempStaticIp,\
    restartVdsmd, restartNetwork
from utils import sendAndCaptureTraffic, setPortMirroring,\
    returnVmsToOriginalHost
from art.rhevm_api.tests_lib.low_level.hosts import waitForHostsStates

import config

logger = logging.getLogger(__name__)

ENUMS = opts['elements_conf']['RHEVM Enums']

MGMT_IPS = config.MGMT_IPS
NET1_IPS = config.NET1_IPS
NET2_IPS = config.NET2_IPS
NET2_TEMP_IP = config.NET2_TEMP_IP
VM_NAME = config.VM_NAME

########################################################################

########################################################################
#                             Test Cases                               #
########################################################################


class PortMirroring_Case1_302095_098(TestCase):
    """
    Check that mirroring still works after migration
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        pass

    @istest
    @tcms(10475, 302095)
    def migrateMirroringVM(self):
        """
        Check that mirroring still works after migrating listening VM to
        another host and back
        """
        for dstVM in (2, 3):
            self.assertTrue(sendAndCaptureTraffic(srcVM=MGMT_IPS[1],
                                                  srcIP=NET1_IPS[1],
                                                  dstIP=NET1_IPS[dstVM]))

        logger.info('Migrating %s to another host and back', VM_NAME[0])
        self.assertTrue(migrateVm(True, VM_NAME[0], config.HOSTS[1]))
        self.assertTrue(migrateVm(True, VM_NAME[0], config.HOSTS[0]))

        for dstVM in (2, 3):
            self.assertTrue(sendAndCaptureTraffic(srcVM=MGMT_IPS[1],
                                                  srcIP=NET1_IPS[1],
                                                  dstIP=NET1_IPS[dstVM]))

    @istest
    @tcms(10475, 302098)
    def migrateAllVMs(self):
        """
        Check that mirroring still works after migrating all VM's involved to
        anther host
        """
        for dstVM in (2, 3):
            self.assertTrue(sendAndCaptureTraffic(srcVM=MGMT_IPS[1],
                                                  srcIP=NET1_IPS[1],
                                                  dstIP=NET1_IPS[dstVM]))

        logger.info('Migrating all VMs to another host to check if PM still '
                    'works afterward')
        for vmName in VM_NAME[:4]:
            self.assertTrue(migrateVm(True, vmName, config.HOSTS[1]))

        for dstVM in (2, 3):
            self.assertTrue(sendAndCaptureTraffic(srcVM=MGMT_IPS[1],
                                                  srcIP=NET1_IPS[1],
                                                  dstIP=NET1_IPS[dstVM]))

        logger.info('Migrating VMs back')
        for vmName in VM_NAME[:4]:
            self.assertTrue(migrateVm(True, vmName, config.HOSTS[0]))

    @classmethod
    def teardown_class(cls):
        """
        Make sure that all the VM's are back on the original host in case
        not all the migrations succeed
        """
        returnVmsToOriginalHost()


class PortMirroring_Case2_302105(TestCase):
    """
    Replace network on the mirrored VM to a non-mirrored network
    """

    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Deactivate NIC3 on VM4 so that we have only one active NIC on sw2.
        (NIC2 will be connected to sw2 during the test).
        """
        if not updateNic(True, VM_NAME[3], config.VM_NICS[2],
                         active=False):
            raise VMException('Failed to decative %s on %s' %
                              (config.VM_NICS[2], VM_NAME[3]))

    @istest
    @tcms(10475, 302105)
    def checkMirroringAfterReplacingNetwork(self):
        """
        Replace the network on a mirrored VM with a non-mirrored network and
        check that its traffic is not mirrored anymore.
        """
        for dstVM in (2, 3):
            self.assertTrue(sendAndCaptureTraffic(srcVM=MGMT_IPS[1],
                                                  srcIP=NET1_IPS[1],
                                                  dstIP=NET1_IPS[dstVM]))

        logger.info("Changing %s nic from sw1 to %s and giving it an IP",
                    VM_NAME[3], config.VLAN_NETWORKS[1])
        self.assertTrue(updateNic(True, VM_NAME[3], config.VM_NICS[1],
                                  network=config.VLAN_NETWORKS[1],
                                  vnic_profile=config.VLAN_NETWORKS[1]))
        self.assertTrue(configureTempStaticIp(MGMT_IPS[3],
                        config.VM_LINUX_USER, config.VM_LINUX_PASSWORD,
                        ip=NET2_TEMP_IP, nic='eth1'))

        # Check that traffic between VM2 and VM3 on sw1 is mirrored while
        # traffic related to VM4 on sw2 is not.
        self.assertTrue(sendAndCaptureTraffic(srcVM=MGMT_IPS[1],
                                              srcIP=NET1_IPS[1],
                                              dstIP=NET1_IPS[2]))
        for dstVM in (1, 2):
            self.assertTrue(sendAndCaptureTraffic(srcVM=MGMT_IPS[3],
                                                  srcIP=NET2_TEMP_IP,
                                                  dstIP=NET2_IPS[dstVM],
                                                  expectTraffic=False))

        logger.info("Changing %s nic back to %s and previous IP",
                    VM_NAME[3], config.VLAN_NETWORKS[0])
        self.assertTrue(updateNic(True, VM_NAME[3], config.VM_NICS[1],
                                  network=config.VLAN_NETWORKS[0],
                                  vnic_profile=config.VLAN_NETWORKS[0]))
        self.assertTrue(configureTempStaticIp(MGMT_IPS[3],
                        config.VM_LINUX_USER, config.VM_LINUX_PASSWORD,
                        ip=NET1_IPS[3], nic='eth1'))

    @classmethod
    def teardown_class(cls):
        """
        Reactivate NIC3 on VM4
        """
        if not updateNic(True, VM_NAME[3], config.VM_NICS[2],
                         active=True):
            raise VMException('Cannot activate nic on %s' % VM_NAME[3])
        if not configureTempStaticIp(MGMT_IPS[3],
                                     config.VM_LINUX_USER,
                                     config.VM_LINUX_PASSWORD,
                                     ip=NET2_IPS[3], nic='eth2'):
            raise VMException('Cannot configure %s on %s' %
                              (NET2_IPS[3], VM_NAME[3]))


########################################################################

########################################################################


########################################################################

########################################################################
class PortMirroring_Case3_302101(TestCase):
    """
    Check mirroring when listening on multiple networks on the same machine
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        pass

    @istest
    @tcms(10475, 302101)
    def checkPMOneMachineMultipleNetworks(self):
        """
        Check that VM1 gets all traffic on both mgmt netowrk and sw1
        """
        self.assertTrue(sendAndCaptureTraffic(srcVM=MGMT_IPS[1],
                                              srcIP=NET1_IPS[1],
                                              dstIP=NET1_IPS[2]))
        self.assertTrue(sendAndCaptureTraffic(srcVM=MGMT_IPS[3],
                                              srcIP=MGMT_IPS[3],
                                              dstIP=MGMT_IPS[4],
                                              nic='eth0'))

    @classmethod
    def teardown_class(cls):
        pass


########################################################################

########################################################################
class PortMirroring_Case4_302100_093_099(TestCase):
    """
    Check mirroring when it's enabled on multiple machines.
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Enable port mirroring on nic2 (connected to sw1) on VM2.
        """
        setPortMirroring(config.VM_NAME[1], config.VM_NICS[1],
                         config.VLAN_NETWORKS[0])

    @istest
    @tcms(10475, 302100)
    def checkPMTwoMachinesDiffNetworks(self):
        """
        Check mirroring when it's enabled on different machines on different
        networks (VM1 is listening to mgmt netowrk and VM2 is listening to sw1)
        """
        logger.info('Sending traffic between VM2 and VM3 on mgmt netowrk to '
                    'make sure only VM1 gets this traffic.')
        self.assertTrue(sendAndCaptureTraffic(srcVM=MGMT_IPS[1],
                                              srcIP=MGMT_IPS[1],
                                              dstIP=MGMT_IPS[2],
                                              nic='eth0'))
        self.assertTrue(sendAndCaptureTraffic(srcVM=MGMT_IPS[1],
                                              srcIP=MGMT_IPS[1],
                                              dstIP=MGMT_IPS[2],
                                              listenVM=VM_NAME[1],
                                              expectTraffic=False))

        logger.info('Sending traffic between VM1 and VM4 on sw1 to make sure'
                    ' only VM2 gets this traffic.')
        self.assertTrue(sendAndCaptureTraffic(srcVM=MGMT_IPS[0],
                                              srcIP=NET1_IPS[0],
                                              dstIP=NET1_IPS[3],
                                              listenVM=VM_NAME[1]))
        self.assertTrue(sendAndCaptureTraffic(srcVM=MGMT_IPS[0],
                                              srcIP=NET1_IPS[0],
                                              dstIP=NET1_IPS[3],
                                              nic='eth0',
                                              expectTraffic=False))

    @istest
    @tcms(10475, 302093)
    def checkPMTwoMachinesSameNetwork(self):
        """
        Check mirroring when two machines are listening to the same network
        (VM1 and VM2 listening on sw1).
        """
        logger.info('Sending traffic between VM3 and VM4 on sw1 to make sure'
                    ' both VM1 and VM2 get the traffic.')
        for vm in config.VM_NAME[:2]:
            self.assertTrue(sendAndCaptureTraffic(srcVM=MGMT_IPS[2],
                                                  srcIP=NET1_IPS[2],
                                                  dstIP=NET1_IPS[3],
                                                  listenVM=vm))

        logger.info("Disabling mirroring on VM2 and checking that VM1 still"
                    " gets the traffic while VM2 doesn't")

        setPortMirroring(config.VM_NAME[1], config.VM_NICS[1],
                         config.VLAN_NETWORKS[0], disableMirroring=True)

        for vm, expTraffic in zip(config.VM_NAME[:2], (True, False)):
            self.assertTrue(sendAndCaptureTraffic(srcVM=MGMT_IPS[2],
                                                  srcIP=NET1_IPS[2],
                                                  dstIP=NET1_IPS[3],
                                                  listenVM=vm,
                                                  expectTraffic=expTraffic))

    @classmethod
    def teardown_class(cls):
        """
        Make sure port mirroring on nic2 (connected to sw1) on VM2 is disabled
        """
        if (getVmNicPortMirroring(True, config.VM_NAME[1], config.VM_NICS[1])):
            setPortMirroring(config.VM_NAME[1], config.VM_NICS[1],
                             config.VLAN_NETWORKS[0], disableMirroring=True)


########################################################################

########################################################################
class PortMirroring_Case5_302106(TestCase):
    """
    Restart VDSM on host while mirroring is on
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        pass

    @istest
    @tcms(10475, 302106)
    def restartNetworkingOnHost(self):
        """
        Check that mirroring still occurs after restarting VDSM and networking
        on the host
        """
        self.assertTrue(sendAndCaptureTraffic(srcVM=MGMT_IPS[1],
                                              srcIP=NET1_IPS[1],
                                              dstIP=NET1_IPS[2]))

        logger.info('Restarting VDSM to check if mirroring still works'
                    'afterwards')
        self.assertTrue(restartVdsmd(config.HOSTS[0], config.HOSTS_PW[0],
                                     supervdsm=True))

        self.assertTrue(sendAndCaptureTraffic(srcVM=MGMT_IPS[1],
                                              srcIP=NET1_IPS[1],
                                              dstIP=NET1_IPS[2]))

    @classmethod
    def teardown_class(cls):
        pass


class PortMirroring_Case6_302106(TestCase):
    """
    Restart networking on host while mirroring is on
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        pass

    @istest
    def restartVDSMOnHost(self):
        """
        Check that mirroring still occurs after restarting networking
        on the host
        """
        logger.info("Restart network service on %s", config.HOSTS[0])
        self.assertTrue(restartNetwork(config.HOSTS[0], config.HOSTS_PW[0]))

        logger.info("Check that %s is UP", config.HOSTS[0])
        if not waitForHostsStates(positive=True, names=config.HOSTS[0]):
            logger.error("%s status isn't UP", config.HOSTS[0])

        logger.info("Check port mirroring traffic")
        self.assertTrue(sendAndCaptureTraffic(srcVM=MGMT_IPS[1],
                                              srcIP=NET1_IPS[1],
                                              dstIP=NET1_IPS[2],
                                              dupCheck=False))

    @classmethod
    def teardown_class(cls):
        pass
