'''
Testing Jumbo frames feature.
1 DC, 1 Cluster, 2 Hosts and 2 VMs will be created for testing.
Jubmo frames will be tested for untagged, tagged, bond scenarios.
It will cover scenarios for VM/non-VM networks.
'''

import config
import logging
from unittest import TestCase
from nose.tools import istest
from art.test_handler.tools import tcms
from art.rhevm_api.utils.test_utils import checkMTU
from art.unittest_lib.network import skipBOND
from art.rhevm_api.tests_lib.low_level.hosts import genSNNic, sendSNRequest
from art.rhevm_api.tests_lib.high_level.vms import check_vm_migration
from art.rhevm_api.tests_lib.low_level.vms import updateNic, removeNic, \
    waitForIP, addNic, getVmHost
from art.rhevm_api.utils.test_utils import get_api, configureTempStaticIp, \
    configureTempMTU, checkConfiguredMTU
from art.test_handler.exceptions import NetworkException, VMException
from art.rhevm_api.tests_lib.high_level.networks import \
    createAndAttachNetworkSN, removeNetFromSetup, checkICMPConnectivity, \
    getIpOnHostNic, TrafficMonitor


HOST_API = get_api('host', 'hosts')
VM_API = get_api('vm', 'vms')

logger = logging.getLogger(__name__)


########################################################################

########################################################################
#                             Test Cases                               #
########################################################################


class JumboFrames_Case01_199743(TestCase):
    """
    Test the bridged VM network with MTU 5000
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Create logical vm network with MTU 5000 on DC/Cluster/Hosts
        """
        local_dict = {config.NETWORKS[0]: {'mtu': config.MTU[0],
                                           'nic': config.HOST_NICS[1],
                                           'required': 'false'}}

        if not createAndAttachNetworkSN(data_center=config.DC_NAME,
                                        cluster=config.CLUSTER_NAME,
                                        host=[config.HOSTS[0]],
                                        network_dict=local_dict,
                                        auto_nics=[config.HOST_NICS[0]]):
            raise NetworkException("Cannot create and attach network")

    @istest
    @tcms(5848, 199743)
    def checkMTU(self):
        """
        Check physical and logical levels for network sw1 with Jumbo frames
        """
        logger.info("Checking logical layer of bridged network %s on host %s"
                    % (config.NETWORKS[0], config.HOSTS[0]))
        self.assertTrue(checkMTU(host=config.HOSTS[0], user=config.HOSTS_USER,
                                 password=config.HOSTS_PW, mtu=config.MTU[0],
                                 physical_layer=False,
                                 network=config.NETWORKS[0],
                                 nic=config.HOST_NICS[1]))
        logger.info("Checking physical layer of bridged network %s on host %s"
                    % (config.NETWORKS[0], config.HOSTS[0]))
        self.assertTrue(checkMTU(host=config.HOSTS[0], user=config.HOSTS_USER,
                                 password=config.HOSTS_PW, mtu=config.MTU[0],
                                 nic=config.HOST_NICS[1]))

    @classmethod
    def teardown_class(cls):
        """
        Remove networks from the setup.
        """
        logger.info("Starting the teardown_class")
        if not removeNetFromSetup(host=[config.HOSTS[0]],
                                  auto_nics=[config.HOST_NICS[0]],
                                  network=[config.NETWORKS[0]]):
            raise NetworkException("Cannot remove network from setup")

########################################################################

########################################################################


class JumboFrames_Case02_200156(TestCase):
    """
    Positive: 1) Creates 2 Non_VM networks with Jumbo Frames
              2) Checks the correct MTU values in the sys/config
                 and sys/class/net
              files
              3) Removes one of the networks
              4) Check the correct values for the MTU in files
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Create bridgeless tagged networks with MTU on DC/Cluster/Hosts
        """
        local_dict = {config.VLAN_NETWORKS[0]: {'vlan_id': config.VLAN_ID[0],
                                                'usages': '',
                                                'mtu': config.MTU[0],
                                                'nic': config.HOST_NICS[1],
                                                'required': 'false'},
                      config.VLAN_NETWORKS[1]: {'vlan_id': config.VLAN_ID[1],
                                                'usages': '',
                                                'mtu': config.MTU[1],
                                                'nic': config.HOST_NICS[1],
                                                'required': 'false'}}

        if not createAndAttachNetworkSN(data_center=config.DC_NAME,
                                        cluster=config.CLUSTER_NAME,
                                        host=[config.HOSTS[0]],
                                        network_dict=local_dict,
                                        auto_nics=[config.HOST_NICS[0],
                                                   config.HOST_NICS[1]]):
            raise NetworkException("Cannot create and attach network")

    @istest
    @tcms(5848, 200156)
    def checkMTUAfterNetworkRemoval(self):
        """
        Check physical and logical levels for networks with Jumbo frames
        """
        logger.info("Checking logical layer of bridgless tagged network "
                    "%s with vlan %s", config.VLAN_NETWORKS[0],
                    config.VLAN_ID[0])
        self.assertTrue(checkMTU(host=config.HOSTS[0], user=config.HOSTS_USER,
                                 password=config.HOSTS_PW, mtu=config.MTU[0],
                                 physical_layer=False,
                                 network=config.VLAN_NETWORKS[0],
                                 nic=config.HOST_NICS[1],
                                 vlan=config.VLAN_ID[0],
                                 bridged=False),
                        "MTU on host %s should be %s and it is "
                        "not" % (config.HOSTS[0], config.MTU[0]))
        logger.info("Checking logical layer of bridgless tagged network "
                    "%s with vlan %s", config.VLAN_NETWORKS[1],
                    config.VLAN_ID[1])
        self.assertTrue(checkMTU(host=config.HOSTS[0], user=config.HOSTS_USER,
                                 password=config.HOSTS_PW, mtu=config.MTU[1],
                                 physical_layer=False,
                                 network=config.VLAN_NETWORKS[1],
                                 nic=config.HOST_NICS[1],
                                 vlan=config.VLAN_ID[1],
                                 bridged=False),
                        "MTU on host %s should be %s and it is "
                        "not" % (config.HOSTS[0], config.MTU[1]))
        logger.info("Checking physical layer for bridgless tagged network ")
        self.assertTrue(checkMTU(host=config.HOSTS[0], user=config.HOSTS_USER,
                                 password=config.HOSTS_PW, mtu=config.MTU[1],
                                 nic=config.HOST_NICS[1],
                                 bridged=False),
                        "MTU on host %s should be %s and it is "
                        "not" % (config.HOSTS[0], config.MTU[1]))

        rc, out = genSNNic(nic=config.HOST_NICS[1],
                           network=config.VLAN_NETWORKS[0],
                           vlan=config.VLAN_ID[0])
        if not rc:
            raise NetworkException("Cannot generate network object")
        sendSNRequest(True, host=config.HOSTS[0],
                      nics=[out['host_nic']],
                      auto_nics=[config.HOST_NICS[0],
                                 config.HOST_NICS[1]],
                      check_connectivity='true',
                      connectivity_timeout=config.CONNECT_TIMEOUT,
                      force='false')

        logger.info("Checking physical layer for bridgless tagged networks ")
        self.assertTrue(checkMTU(host=config.HOSTS[0], user=config.HOSTS_USER,
                                 password=config.HOSTS_PW, mtu=config.MTU[0],
                                 nic=config.HOST_NICS[1],
                                 bridged=False),
                        "MTU on host %s should be %s and it is "
                        "not" % (config.HOSTS[0], config.MTU[0]))

    @classmethod
    def teardown_class(cls):
        """
        Remove networks from the setup
        """
        logger.info("Starting the teardown_class")
        if not removeNetFromSetup(host=[config.HOSTS[0]],
                                  auto_nics=[config.HOST_NICS[0]],
                                  network=[config.VLAN_NETWORKS[0],
                                           config.VLAN_NETWORKS[1]]):
            raise NetworkException("Cannot remove network from setup")

########################################################################

########################################################################


class JumboFrames_Case03_197212(TestCase):
    """
    Positive: Creates bridged network over bond on Host
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Create bridged vlan network with MTU on DC/Cluster/Host over bond
        """

        local_dict = {None: {'nic': config.BONDS[0], 'mode': 1,
                             'slaves': [config.HOST_NICS[2],
                                        config.HOST_NICS[3]]},
                      config.VLAN_NETWORKS[0]: {'nic': config.BONDS[0],
                                                'mtu': config.MTU[0],
                                                'vlan_id': config.VLAN_ID[0],
                                                'required': 'false'}}
        if not createAndAttachNetworkSN(data_center=config.DC_NAME,
                                        cluster=config.CLUSTER_NAME,
                                        host=[config.HOSTS[0]],
                                        network_dict=local_dict,
                                        auto_nics=[config.HOST_NICS[0]]):
            raise NetworkException("Cannot create and attach network")

    @istest
    @tcms(5848, 197212)
    def bondModeChange(self):
        """
        Check physical and logical levels for networks with Jumbo frames
        """
        logger.info("Checking physical and logical layers on bond")
        logger.info("Checking logical layer of %s over bond with vlan %s",
                    config.VLAN_NETWORKS[0], config.VLAN_ID[0])
        self.assertTrue(checkMTU(host=config.HOSTS[0], user=config.HOSTS_USER,
                                 password=config.HOSTS_PW, mtu=config.MTU[0],
                                 physical_layer=False,
                                 network=config.VLAN_NETWORKS[0],
                                 bond=config.BONDS[0],
                                 bridged=False),
                        "MTU on host %s should be %s and it is "
                        "not" % (config.HOSTS[0], config.MTU[0]))
        logger.info("Checking physical layer of %s over bond with vlan %s",
                    config.VLAN_NETWORKS[0], config.VLAN_ID[0])
        self.assertTrue(checkMTU(host=config.HOSTS[0], user=config.HOSTS_USER,
                                 password=config.HOSTS_PW, mtu=config.MTU[0],
                                 bond=config.BONDS[0],
                                 bond_nic1=config.HOST_NICS[2],
                                 bond_nic2=config.HOST_NICS[3],
                                 bridged=False),
                        "MTU on host %s should be %s and it is "
                        "not" % (config.HOSTS[0], config.MTU[0]))
        logger.info("Changing the bond mode to mode4")
        rc, out = genSNNic(nic=config.BONDS[0],
                           network=config.VLAN_NETWORKS[0],
                           slaves=[config.HOST_NICS[2],
                                   config.HOST_NICS[3]],
                           mode=4)

        if not rc:
            raise NetworkException("Cannot generate network object")
        sendSNRequest(positive=True, host=config.HOSTS[0],
                      nics=[out['host_nic']],
                      auto_nics=[config.HOST_NICS[0]],
                      check_connectivity='true',
                      connectivity_timeout=config.CONNECT_TIMEOUT,
                      force='false')
        logger.info("Checking layers after bond mode change")
        logger.info("Checking logical layer after bond mode change")
        self.assertTrue(checkMTU(host=config.HOSTS[0], user=config.HOSTS_USER,
                                 password=config.HOSTS_PW, mtu=config.MTU[0],
                                 physical_layer=False,
                                 network=config.VLAN_NETWORKS[0],
                                 bond=config.BONDS[0],
                                 bridged=False),
                        "MTU on host %s should be %s and it is "
                        "not" % (config.HOSTS[0], config.MTU[0]))
        logger.info("Checking physical layer after bond mode change")
        self.assertTrue(checkMTU(host=config.HOSTS[0], user=config.HOSTS_USER,
                                 password=config.HOSTS_PW, mtu=config.MTU[0],
                                 bond=config.BONDS[0],
                                 bond_nic1=config.HOST_NICS[2],
                                 bond_nic2=config.HOST_NICS[3],
                                 bridged=False),
                        "MTU on host %s should be %s and it is "
                        "not" % (config.HOSTS[0], config.MTU[0]))

    @classmethod
    def teardown_class(cls):
        """
        Remove networks from the setup
        """
        logger.info("Starting the teardown_class")
        if not removeNetFromSetup(host=[config.HOSTS[0]],
                                  auto_nics=[config.HOST_NICS[0]],
                                  network=[config.VLAN_NETWORKS[0]]):
            raise NetworkException("Cannot remove networks from setup")

########################################################################

########################################################################


class JumboFrames_Case04_197214_213_742(TestCase):
    """
    Positive: Creates 2 bridged vlan network and check the network files.
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Create bridged vlan networks with MTU on DC/Cluster/Host
        """
        local_dict = {config.VLAN_NETWORKS[0]: {'vlan_id': config.VLAN_ID[0],
                                                'mtu': config.MTU[0],
                                                'nic': config.HOST_NICS[1],
                                                'required': 'false'},
                      config.VLAN_NETWORKS[1]: {'vlan_id': config.VLAN_ID[1],
                                                'mtu': config.MTU[1],
                                                'nic': config.HOST_NICS[1],
                                                'required': 'false'}}
        if not createAndAttachNetworkSN(data_center=config.DC_NAME,
                                        cluster=config.CLUSTER_NAME,
                                        host=[config.HOSTS[0]],
                                        network_dict=local_dict,
                                        auto_nics=[config.HOST_NICS[0],
                                                   config.HOST_NICS[1]]):
            raise NetworkException("Cannot create and attach network")

    @istest
    #@tcms(5848, 197214)
    #@tcms(5848, 197213)
    @tcms(5848, 197742)
    def checkMTUValuesInFiles(self):
        """
        Check physical and logical levels for bridged vlan networks
        """
        logger.info("Checking physical and logical layers on interfaces")
        logger.info("Checking logical layer of bridgless tagged network %s "
                    "with vlan %s", config.VLAN_NETWORKS[0], config.VLAN_ID[0])
        self.assertTrue(checkMTU(host=config.HOSTS[0], user=config.HOSTS_USER,
                                 password=config.HOSTS_PW, mtu=config.MTU[0],
                                 physical_layer=False,
                                 network=config.VLAN_NETWORKS[0],
                                 nic=config.HOST_NICS[1],
                                 vlan=config.VLAN_ID[0]),
                        "MTU on host %s should be %s and it is "
                        "not" % (config.HOSTS[0], config.MTU[0]))
        logger.info("Checking logical layer of bridgless tagged network %s "
                    "with vlan %s", config.VLAN_NETWORKS[1], config.VLAN_ID[1])
        self.assertTrue(checkMTU(host=config.HOSTS[0], user=config.HOSTS_USER,
                                 password=config.HOSTS_PW, mtu=config.MTU[1],
                                 physical_layer=False,
                                 network=config.VLAN_NETWORKS[1],
                                 nic=config.HOST_NICS[1],
                                 vlan=config.VLAN_ID[1]),
                        "MTU on host %s should be %s and it is "
                        "not" % (config.HOSTS[0], config.MTU[1]))
        logger.info("Checking physical layer for bridgless tagged networks ")
        self.assertTrue(checkMTU(host=config.HOSTS[0], user=config.HOSTS_USER,
                                 password=config.HOSTS_PW, mtu=config.MTU[1],
                                 nic=config.HOST_NICS[1]),
                        "MTU on host %s should be %s and it is "
                        "not" % (config.HOSTS[0], config.MTU[1]))

    @classmethod
    def teardown_class(cls):
        """
        Remove networks from the setup
        """
        logger.info("Starting the teardown_class")
        if not removeNetFromSetup(host=[config.HOSTS[0]],
                                  auto_nics=[config.HOST_NICS[0]],
                                  network=[config.VLAN_NETWORKS[0],
                                           config.VLAN_NETWORKS[1]]):
            raise NetworkException("Cannot remove network from setup")

########################################################################

########################################################################


class JumboFrames_Case05_199741(TestCase):
    """
    Positive: Creates bridged vlan network over bond on host
              Checks that increasing bond's size doesn't effect
              the parameters in ifcfg- and sys files
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Create bridged networks with MTU on DC/Cluster/Hosts over bond
        """
        local_dict = {None: {'nic': config.BONDS[0],
                             'mode': 1,
                             'slaves': [config.HOST_NICS[2],
                                        config.HOST_NICS[3]]},
                      config.VLAN_NETWORKS[0]: {'nic': config.BONDS[0],
                                                'mtu': config.MTU[0],
                                                'vlan_id': config.VLAN_ID[0],
                                                'required': 'false'}}

        if not createAndAttachNetworkSN(data_center=config.DC_NAME,
                                        cluster=config.CLUSTER_NAME,
                                        host=config.HOSTS[0],
                                        network_dict=local_dict,
                                        auto_nics=[config.HOST_NICS[0]]):
            raise NetworkException("Cannot create and attach network")

    @istest
    @tcms(5848, 199741)
    def increasingBondNics(self):
        """
        Check physical and logical levels for networks with Jumbo frames
        """

        logger.info("Checking physical and logical layers on bond")
        logger.info("Checking logical layer of %s over bond with vlan %s",
                    config.VLAN_NETWORKS[0], config.VLAN_ID[0])
        self.assertTrue(checkMTU(host=config.HOSTS[0], user=config.HOSTS_USER,
                                 password=config.HOSTS_PW, mtu=config.MTU[0],
                                 physical_layer=False,
                                 network=config.VLAN_NETWORKS[0],
                                 bond=config.BONDS[0],
                                 bridged=False),
                        "MTU on host %s should be %s and it is "
                        "not" % (config.HOSTS[0], config.MTU[0]))
        logger.info("Checking physical layer of %s over bond with vlan %s",
                    config.VLAN_NETWORKS[0], config.VLAN_ID[0])
        self.assertTrue(checkMTU(host=config.HOSTS[0], user=config.HOSTS_USER,
                                 password=config.HOSTS_PW, mtu=config.MTU[0],
                                 bond=config.BONDS[0],
                                 bond_nic1=config.HOST_NICS[2],
                                 bond_nic2=config.HOST_NICS[3],
                                 bridged=False),
                        "MTU on host %s should be %s and it is "
                        "not" % (config.HOSTS[0], config.MTU[0]))

        logger.info("Changing the bond to consist of 3 NICs")
        rc, out = genSNNic(nic=config.BONDS[0],
                           network=config.VLAN_NETWORKS[0],
                           slaves=[config.HOST_NICS[1], config.HOST_NICS[2],
                                   config.HOST_NICS[3]])
        if not rc:
            raise NetworkException("Cannot generate network object")

        sendSNRequest(positive=True, host=config.HOSTS[0],
                      nics=[out['host_nic']],
                      auto_nics=[config.HOST_NICS[0]],
                      check_connectivity='true',
                      connectivity_timeout=config.CONNECT_TIMEOUT,
                      force='false')

        logger.info("Checking layers after increasing the number "
                    "of bond's nics")
        logger.info("Checking logical layer after increasing the "
                    "number of bond's nics")
        self.assertTrue(checkMTU(host=config.HOSTS[0], user=config.HOSTS_USER,
                                 password=config.HOSTS_PW, mtu=config.MTU[0],
                                 physical_layer=False,
                                 network=config.VLAN_NETWORKS[0],
                                 bond=config.BONDS[0],
                                 bridged=False),
                        "MTU on host %s should be %s and it is "
                        "not" % (config.HOSTS[0], config.MTU[0]))
        logger.info("Checking physical layer after extending the "
                    "number of bond's nics")
        self.assertTrue(checkMTU(host=config.HOSTS[0], user=config.HOSTS_USER,
                                 password=config.HOSTS_PW, mtu=config.MTU[0],
                                 bond=config.BONDS[0],
                                 bond_nic1=config.HOST_NICS[2],
                                 bond_nic2=config.HOST_NICS[3],
                                 bridged=False),
                        "MTU on host %s should be %s and it is "
                        "not" % (config.HOSTS[0], config.MTU[0]))

    @classmethod
    def teardown_class(cls):
        """
        Remove networks from the setup
        """
        logger.info("Starting the teardown_class")
        if not removeNetFromSetup(host=config.HOSTS[0],
                                  auto_nics=[config.HOST_NICS[0]],
                                  network=[config.VLAN_NETWORKS[0]]):
            raise NetworkException("Cannot remove networks from setup")

########################################################################

########################################################################


class JumboFrames_Case06_199787(TestCase):
    """
    Negative: 1. creates bond0 and attach vlan network with MTU 9000 to it.
              2. attaches non_vm network with MTU 5000 to bond0.
    """
    __test__ = True

    local_dict = {None: {'nic': config.BONDS[0], 'mode': 1,
                         'slaves': [config.HOST_NICS[2],
                                    config.HOST_NICS[3]]},
                  config.VLAN_NETWORKS[0]: {'nic': config.BONDS[0],
                                            'mtu': config.MTU[1],
                                            'vlan_id': config.VLAN_ID[0],
                                            'required': 'false'},
                  config.NETWORKS[0]: {'nic': config.BONDS[0],
                                       'mtu': config.MTU[0],
                                       'usages': '',
                                       'required': 'false'}}

    @classmethod
    def setup_class(cls):
        """
        creates bond0 and attach network sw201 with MTU 9000 to it.
        """

        if not createAndAttachNetworkSN(data_center=config.DC_NAME,
                                        cluster=config.CLUSTER_NAME,
                                        network_dict=cls.local_dict):
            raise NetworkException("Cannot create and attach network")

    @istest
    @tcms(5848, 199787)
    def NegAddNetworksWithDifferentMTU(self):
        """
        Trying to add two networks with different MTU to the
        same interface when one is vm network and the other
        is non_vm - should fail
        """

        logger.info("Negative: Trying to add two networks with "
                    "different MTU to the same interface when "
                    "one is vm network and the other is non_vm")
        net_obj = []
        for net, net_param in self.local_dict.items():
            address_list = net_param.get('address', [])
            netmask_list = net_param.get('netmask', [])
            gateway_list = net_param.get('gateway', [])

            rc, out = genSNNic(nic=net_param['nic'],
                               network=net,
                               slaves=net_param.get('slaves', None),
                               mode=net_param.get('mode', None),
                               boot_protocol=net_param.get('bootproto', None),
                               address=address_list.pop(0)
                               if address_list else None,
                               netmask=netmask_list.pop(0)
                               if netmask_list else None,
                               gateway=gateway_list.pop(0)
                               if gateway_list else None)

            if not rc:
                logger.error("Cannot generate network object")
                return False
            net_obj.append(out['host_nic'])

        logger.info("Sending SN request to host %s" % config.HOSTS[0])
        if not sendSNRequest(positive=False,
                             host=config.HOSTS[0],
                             nics=net_obj,
                             auto_nics=[config.HOST_NICS[0]],
                             check_connectivity='true',
                             connectivity_timeout=config.CONNECT_TIMEOUT,
                             force='false'):
            logger.error("Adding two networks with different MTU when "
                         "one is vm network and the other is non_vm "
                         "was successful - Should have failed")
            return True
        return False

    @classmethod
    def teardown_class(cls):
        """
        Remove networks from the setup
        """
        logger.info("Starting the teardown_class")
        if not removeNetFromSetup(host=config.HOSTS[0],
                                  auto_nics=[config.HOST_NICS[0]],
                                  network=[config.VLAN_NETWORKS[0],
                                           config.NETWORKS[0]]):
            raise NetworkException("Cannot remove networks from setup")

########################################################################

########################################################################


class JumboFrames_Case07_200118(TestCase):
    """
    Positive: Creates 2 bridged vlan network and check the traffic between VMs
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Create bridged networks with MTU on DC/Cluster/Hosts
        """

        local_dict = {config.VLAN_NETWORKS[0]: {'vlan_id': config.VLAN_ID[0],
                                                'mtu': config.MTU[0],
                                                'nic': config.HOST_NICS[1],
                                                'required': 'false'},
                      config.VLAN_NETWORKS[1]: {'vlan_id': config.VLAN_ID[1],
                                                'mtu': config.MTU[1],
                                                'nic': config.HOST_NICS[1],
                                                'required': 'false'}}
        if not createAndAttachNetworkSN(data_center=config.DC_NAME,
                                        cluster=config.CLUSTER_NAME,
                                        host=[config.HOSTS[0],
                                              config.HOSTS[1]],
                                        network_dict=local_dict,
                                        auto_nics=[config.HOST_NICS[0],
                                                   config.HOST_NICS[1]]):
            raise NetworkException("Cannot create and attach network")

        for i in range(2):
            logger.info("Adding %s with MTU %s as %s on %s",
                        config.VLAN_NETWORKS[0], config.MTU[0],
                        config.VM_NIC_NAMES[1],
                        config.VM_NAME[i])
            if not addNic(positive=True,
                          vm=config.VM_NAME[i],
                          name=config.VM_NIC_NAMES[1],
                          network=config.VLAN_NETWORKS[0]):
                raise VMException("Cannot add vnic to VM")

            vm_ip = waitForIP(config.VM_NAME[i])[1]['ip']
            if not configureTempMTU(host=vm_ip,
                                    user=config.HOSTS_USER,
                                    password=config.HOSTS_PW,
                                    mtu=str(config.MTU[0])):
                raise VMException("Unable to configure vm's nic with MTU %s" %
                                  config.MTU[0])

    @istest
    @tcms(5848, 200118)
    def checkTrafficOnVms(self):
        """
        Send ping between 2 VMS
        """
        ip_list = []
        for i in range(2):
            ip_list.append(waitForIP(config.VM_NAME[i])[1]['ip'])

        logger.info("Configuring eth1 with static IP on both VMs ")
        for i in range(2):
            if not configureTempStaticIp(host=ip_list[i],
                                         user=config.HOSTS_USER,
                                         password=config.HOSTS_PW,
                                         ip="%s%d" % (config.INTER_SUBNET,
                                                      i + 1),
                                         nic=config.VM_NICS[1]):
                logger.error("Couldn't configure temp ip on VMs")
                return False

        logger.info("Checking if sending ICMP traffic on %s "
                    "succeed", config.VLAN_NETWORKS[0])
        if not checkICMPConnectivity(host=ip_list[0],
                                     user=config.HOSTS_USER,
                                     password=config.HOSTS_PW,
                                     ip=config.IPS[1],
                                     max_counter=config.TRAFFIC_TIMEOUT,
                                     packet_size=config.SEND_MTU[0]):
            raise VMException("Traffic between the VMs failed")
        logger.info("Traffic between the VMs succeed")

        logger.info("Removing %s from the hosts", config.VLAN_NETWORKS[1])
        for host_idx in range(len(config.HOSTS)):
            sendSNRequest(True, host=config.HOSTS[host_idx],
                          nics=[],
                          auto_nics=[config.HOST_NICS[0],
                                     config.HOST_NICS[1],
                                     "%s.%s" % (config.HOST_NICS[1],
                                                config.VLAN_ID[0])],
                          check_connectivity='true',
                          connectivity_timeout=config.CONNECT_TIMEOUT,
                          force='false')

        logger.info("Checking if sending ICMP traffic on network %s "
                    "succeed after removal of %s network",
                    config.VLAN_NETWORKS[0], config.VLAN_NETWORKS[1])
        if not checkICMPConnectivity(host=ip_list[0],
                                     user=config.HOSTS_USER,
                                     password=config.HOSTS_PW,
                                     ip=config.IPS[1],
                                     max_counter=config.TRAFFIC_TIMEOUT,
                                     packet_size=config.SEND_MTU[0]):
            raise VMException("Traffic between the VMs failed")
        logger.info("Traffic between the VMs succeed")

        for host_idx in range(len(config.HOSTS)):
            logger.info("Checking logical layer of bridged vlan "
                        "network %s on host %s"
                        % (config.VLAN_NETWORKS[0], config.HOSTS[host_idx]))
            self.assertTrue(checkMTU(host=config.HOSTS[host_idx],
                                     user=config.HOSTS_USER,
                                     password=config.HOSTS_PW,
                                     mtu=config.MTU[0],
                                     physical_layer=False,
                                     network=config.VLAN_NETWORKS[0],
                                     nic=config.HOST_NICS[1]))
            logger.info("Checking physical layer of bridged vlan "
                        "network %s on host %s"
                        % (config.VLAN_NETWORKS[0], config.HOSTS[host_idx]))

            self.assertTrue(checkMTU(host=config.HOSTS[host_idx],
                                     user=config.HOSTS_USER,
                                     password=config.HOSTS_PW,
                                     mtu=config.MTU[0],
                                     nic=config.HOST_NICS[1]))

    @classmethod
    def teardown_class(cls):
        """
        Remove networks from the setup
        """
        logger.info("Starting the teardown")
        for i in range(2):
            logger.info("Unpluging %s at %s" % (config.VM_NIC_NAMES[1],
                                                config.VM_NAME[i]))
            if not updateNic(positive=True,
                             vm=config.VM_NAME[i],
                             nic=config.VM_NIC_NAMES[1],
                             plugged=False):
                logger.error("Unplug %s failed", config.VM_NIC_NAMES[1])

            logger.info("Removing %s from %s" % (config.VM_NIC_NAMES[1],
                                                 config.VM_NAME[i]))
            if not removeNic(positive=True,
                             vm=config.VM_NAME[i],
                             nic=config.VM_NIC_NAMES[1]):
                raise VMException("Cannot remove VNIC from %s"
                                  % (config.VM_NAME[i]))

        if not removeNetFromSetup(host=config.HOSTS[0],
                                  auto_nics=[config.HOST_NICS[0]],
                                  network=[config.VLAN_NETWORKS[0],
                                           config.VLAN_NETWORKS[1]]):
            raise NetworkException("Cannot remove networks from setup")

########################################################################

########################################################################


class JumboFrames_Case08_199787(TestCase):
    """
    Negative: Creates bond0 and attach network with MTU 9000 and
    vlan 201 to it, then attaching a non_vm network with MTU 5000
    to bond0.
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Create bridged networks with MTU on DC/Cluster/Hosts
        """

        local_dict = {None: {'nic': config.BONDS[0], 'mode': 1,
                             'slaves': [config.HOST_NICS[2],
                                        config.HOST_NICS[3]]},
                      config.VLAN_NETWORKS[0]: {'nic': config.BONDS[0],
                                                'mtu': config.MTU[1],
                                                'vlan_id': config.VLAN_ID[0],
                                                'required': 'false'}}
        logger.info("Creating %s at DC and Cluster", config.VLAN_NETWORKS[0])
        if not createAndAttachNetworkSN(data_center=config.DC_NAME,
                                        cluster=config.CLUSTER_NAME,
                                        host=[config.HOSTS[0]],
                                        network_dict=local_dict,
                                        auto_nics=[config.HOST_NICS[0]]):
            raise NetworkException("Cannot create and attach network")

    @istest
    @tcms(5848, 199787)
    def addNonVmNetworkWithLowerMTU(self):
        """
        Negative: Adding a non vm network with mtu 5000 on the bond.
        Should fail because non vm network must be the highest
        """
        new_network = {config.NETWORKS[1]: {'mtu': config.MTU[0],
                                            'nic': config.BONDS[0],
                                            'required': 'false',
                                            'usages': ''}}
        logger.info("Creating %s at DC and Cluster", config.VLAN_NETWORKS[1])
        if not createAndAttachNetworkSN(data_center=config.DC_NAME,
                                        cluster=config.CLUSTER_NAME,
                                        network_dict=new_network):
            raise NetworkException("Cannot create network")

        local_dict = {None: {'nic': config.BONDS[0], 'mode': 1,
                             'slaves': [config.HOST_NICS[2],
                                        config.HOST_NICS[3]]},
                      config.NETWORKS[1]: {'mtu': config.MTU[0],
                                           'nic': config.BONDS[0],
                                           'required': 'false',
                                           'usages': ''}}

        logger.info("Trying to attach the non vm network to the host "
                    "with the second network. Should fail since non "
                    "vm network has lower MTU")
        if createAndAttachNetworkSN(host=config.HOSTS[0],
                                    network_dict=local_dict,
                                    auto_nics=[config.HOST_NICS[0],
                                               "%s.%s" % (config.BONDS[0],
                                                          config.VLAN_ID[0])]):
            raise NetworkException("Non vm network was successfully attached "
                                   "when it shouldn't have")

    @classmethod
    def teardown_class(cls):
        """
        Remove networks from the setup
        """
        logger.info("Starting the teardown")
        if not removeNetFromSetup(host=config.HOSTS[0],
                                  auto_nics=[config.HOST_NICS[0]],
                                  network=[config.VLAN_NETWORKS[0],
                                           config.NETWORKS[1]]):
            raise NetworkException("Cannot remove networks from setup")

########################################################################

########################################################################


class JumboFrames_Case09_199741(TestCase):
    """
    Positive: Creates bridged vlan network over bond on Host with MTU
    5000, then, add another network with MTU 1500 and checking that
    MTU on nics are configured correctly on the logical and physical layers.
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Create bridged vlan network with MTU on DC/Cluster/Host over bond
        """

        local_dict = {None: {'nic': config.BONDS[0], 'mode': 1,
                             'slaves': [config.HOST_NICS[2],
                                        config.HOST_NICS[3]]},
                      config.VLAN_NETWORKS[0]: {'nic': config.BONDS[0],
                                                'mtu': config.MTU[0],
                                                'vlan_id': config.VLAN_ID[0],
                                                'required': 'false'}}
        if not createAndAttachNetworkSN(data_center=config.DC_NAME,
                                        cluster=config.CLUSTER_NAME,
                                        host=[config.HOSTS[0]],
                                        network_dict=local_dict,
                                        auto_nics=[config.HOST_NICS[0]]):
            raise NetworkException("Cannot create and attach network")

    @istest
    @tcms(5848, 199741)
    def CheckMTUWithTwoDifferentMTUNetworks(self):
        """
        Check physical and logical levels for networks with Jumbo frames
        """
        logger.info("Checking logical layer of %s over bond with vlan %s",
                    config.VLAN_NETWORKS[0], config.VLAN_ID[0])
        self.assertTrue(checkMTU(host=config.HOSTS[0], user=config.HOSTS_USER,
                                 password=config.HOSTS_PW, mtu=config.MTU[0],
                                 physical_layer=False,
                                 network=config.VLAN_NETWORKS[0],
                                 bond=config.BONDS[0],
                                 bridged=False),
                        "MTU on host %s should be %s and it is "
                        "not" % (config.HOSTS[0], config.MTU[0]))

        logger.info("Checking physical layer of %s over bond with vlan %s",
                    config.VLAN_NETWORKS[0], config.VLAN_ID[0])
        self.assertTrue(checkMTU(host=config.HOSTS[0], user=config.HOSTS_USER,
                                 password=config.HOSTS_PW, mtu=config.MTU[0],
                                 bond=config.BONDS[0],
                                 bond_nic1=config.HOST_NICS[2],
                                 bond_nic2=config.HOST_NICS[3],
                                 bridged=False),
                        "MTU on host %s should be %s and it is "
                        "not" % (config.HOSTS[0], config.MTU[0]))

        new_network = {None: {'nic': config.BONDS[0], 'mode': 1,
                              'slaves': [config.HOST_NICS[2],
                                         config.HOST_NICS[3]]},
                       config.VLAN_NETWORKS[1]: {'nic': config.BONDS[0],
                                                 'required': 'false',
                                                 'vlan_id': config.VLAN_ID[1]}}

        logger.info("Adding %s to DC, Cluster and Host",
                    config.VLAN_NETWORKS[1])
        if not createAndAttachNetworkSN(data_center=config.DC_NAME,
                                        cluster=config.CLUSTER_NAME,
                                        host=config.HOSTS[0],
                                        network_dict=new_network,
                                        auto_nics=[
                                            config.HOST_NICS[0],
                                            "%s.%s" % (config.BONDS[0],
                                                       config.VLAN_ID[0])]):
            raise NetworkException("Cannot create & add network")

        logger.info("Checking logical & physical layer after adding "
                    "another network")
        logger.info("Checking logical layer for network %s",
                    config.VLAN_NETWORKS[0])
        self.assertTrue(checkMTU(host=config.HOSTS[0], user=config.HOSTS_USER,
                                 password=config.HOSTS_PW, mtu=config.MTU[0],
                                 physical_layer=False,
                                 network=config.VLAN_NETWORKS[0],
                                 bond=config.BONDS[0],
                                 bridged=False),
                        "MTU on host %s should be %s and it is "
                        "not" % (config.HOSTS[0], config.MTU[0]))

        logger.info("Checking logical layer for network %s",
                    config.VLAN_NETWORKS[1])
        self.assertTrue(checkMTU(host=config.HOSTS[0], user=config.HOSTS_USER,
                                 password=config.HOSTS_PW, mtu=config.MTU[3],
                                 physical_layer=False,
                                 network=config.VLAN_NETWORKS[1],
                                 bond=config.BONDS[0],
                                 bridged=False),
                        "MTU on host %s should be %s and it is "
                        "not" % (config.HOSTS[0], config.MTU[3]))

        logger.info("Checking physical layer for network %s",
                    config.VLAN_NETWORKS[0])
        self.assertTrue(checkMTU(host=config.HOSTS[0], user=config.HOSTS_USER,
                                 password=config.HOSTS_PW, mtu=config.MTU[0],
                                 bond=config.BONDS[0],
                                 bond_nic1=config.HOST_NICS[2],
                                 bond_nic2=config.HOST_NICS[3],
                                 bridged=False),
                        "MTU on host %s should be %s and it is "
                        "not" % (config.HOSTS[0], config.MTU[0]))

    @classmethod
    def teardown_class(cls):
        """
        Remove networks from the setup
        """
        logger.info("Starting the teardown_class")
        if not removeNetFromSetup(host=[config.HOSTS[0]],
                                  auto_nics=[config.HOST_NICS[0]],
                                  network=[config.VLAN_NETWORKS[0],
                                           config.VLAN_NETWORKS[1]]):
            raise NetworkException("Cannot remove networks from setup")

########################################################################

########################################################################


class JumboFrames_Case10_167549(TestCase):
    """
    In the host, changing eth1's MTU to 2000 (manually), then adding logical
    network without MTU on eth1, and finally, checking that eth1's MTU is
    still 2000
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        For the host, changing eth1's MTU to 2000, then adding logical network
        without MTU on eth1
        """

        if not configureTempMTU(host=config.HOSTS[0],
                                user=config.HOSTS_USER,
                                password=config.HOSTS_PW,
                                mtu=str(config.MTU[2])):
            raise NetworkException("Unable to configure host's nic "
                                   "with MTU %s" % config.MTU[2])

        local_dict = {config.VLAN_NETWORKS[0]: {'vlan_id': config.VLAN_ID[0],
                                                'nic': config.HOST_NICS[1],
                                                'required': 'false'}}

        if not createAndAttachNetworkSN(data_center=config.DC_NAME,
                                        cluster=config.CLUSTER_NAME,
                                        host=[config.HOSTS[0]],
                                        network_dict=local_dict,
                                        auto_nics=[config.HOST_NICS[0],
                                                   config.HOST_NICS[1]]):
            raise NetworkException("Cannot create and attach network")

    @istest
    @tcms(5848, 167549)
    def checkMTUPreConfigured(self):
        """
        checking that eth1's MTU is still 2000
        """

        logger.info("Checking if %s is configured correctly",
                    config.HOST_NICS[1])
        self.assertTrue(checkConfiguredMTU(host=config.HOSTS[0],
                                           user=config.HOSTS_USER,
                                           password=config.HOSTS_PW,
                                           mtu=config.MTU[2],
                                           inter_or_net=config.HOST_NICS[1]))

    @classmethod
    def teardown_class(cls):
        """
        Remove networks from the setup
        """
        logger.info("Starting the teardown_class")

        logger.info("Restoring %s's MTU to %s", config.HOST_NICS[1],
                    config.MTU[3])
        if not configureTempMTU(host=config.HOSTS[0],
                                user=config.HOSTS_USER,
                                password=config.HOSTS_PW,
                                mtu=str(config.MTU[3])):
            raise VMException("Unable to configure host's nic "
                              "with MTU %s" % config.MTU[3])

        logger.info("Removing networks from the system")
        if not removeNetFromSetup(host=[config.HOSTS[0]],
                                  auto_nics=[config.HOST_NICS[0]],
                                  network=[config.VLAN_NETWORKS[0]]):
            raise NetworkException("Cannot remove networks from setup")

########################################################################

########################################################################


class JumboFrames_Case11_148668(TestCase):
    """
    Attach a network with MTU 9000 to the host on bond, checking that
    mtu is configured correctly, adding the network to another host,
    finally, checking traffic between the hosts with the MTU configured.
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Adding a vlan network sw201 with MTU 9000 to the first host
        """
        local_dict = {None: {'nic': config.BONDS[0], 'mode': 1,
                             'slaves': [config.HOST_NICS[2],
                                        config.HOST_NICS[3]]},
                      config.VLAN_NETWORKS[0]: {'nic': config.BONDS[0],
                                                'mtu': config.MTU[1],
                                                'bootproto': 'static',
                                                'address': [config.IPS[0],
                                                            config.IPS[1]],
                                                'netmask': [config.NETMASK,
                                                            config.NETMASK],
                                                'gateway': [config.GATEWAY],
                                                'vlan_id': config.VLAN_ID[0],
                                                'required': 'false'}}

        if not createAndAttachNetworkSN(data_center=config.DC_NAME,
                                        cluster=config.CLUSTER_NAME,
                                        host=[config.HOSTS[0],
                                              config.HOSTS[1]],
                                        network_dict=local_dict,
                                        auto_nics=[config.HOST_NICS[0]]):
            raise NetworkException("Cannot create and attach network")

    @istest
    @tcms(5848, 148668)
    def checkConfigurationsAndTraffic(self):
        """
        Checking configuration of the network on the first host, adding
        the network to the second host, finally, checking traffic between
        the two hosts.
        """
        list_check_networks = [config.HOST_NICS[2],
                               config.HOST_NICS[3],
                               config.VLAN_NETWORKS[0],
                               config.BONDS[0],
                               "%s.%s" % (config.BONDS[0],
                                          config.VLAN_ID[0])]
        logger.info("Checking that networks and interfaces are "
                    "configured correctly")

        for element in list_check_networks:
            logger.info("Checking ifconfig for %s on the host %s",
                        element, config.HOSTS[0])
            self.assertTrue(checkConfiguredMTU(host=config.HOSTS[0],
                                               user=config.HOSTS_USER,
                                               password=config.HOSTS_PW,
                                               mtu=config.MTU[1],
                                               inter_or_net=element))

        logger.info("Checking physical layer of %s over bond with vlan %s",
                    config.VLAN_NETWORKS[0], config.VLAN_ID[0])
        self.assertTrue(checkMTU(host=config.HOSTS[0], user=config.HOSTS_USER,
                                 password=config.HOSTS_PW, mtu=config.MTU[1],
                                 physical_layer=False,
                                 network=config.VLAN_NETWORKS[0],
                                 bond=config.BONDS[0],
                                 bridged=False),
                        "MTU on host %s should be %s and it is "
                        "not" % (config.HOSTS[0], config.MTU[1]))

        logger.info("Checking logical layer of %s over bond with vlan %s",
                    config.VLAN_NETWORKS[0], config.VLAN_ID[0])
        self.assertTrue(checkMTU(host=config.HOSTS[0], user=config.HOSTS_USER,
                                 password=config.HOSTS_PW, mtu=config.MTU[1],
                                 bond=config.BONDS[0],
                                 bond_nic1=config.HOST_NICS[2],
                                 bond_nic2=config.HOST_NICS[3],
                                 bridged=False),
                        "MTU on host %s should be %s and it is "
                        "not" % (config.HOSTS[0], config.MTU[0]))

        logger.info("Checking traffic between the two hosts")
        if not checkICMPConnectivity(host=config.HOSTS[0],
                                     user=config.HOSTS_USER,
                                     password=config.HOSTS_PW,
                                     ip=config.IPS[1],
                                     max_counter=config.TRAFFIC_TIMEOUT,
                                     packet_size=config.SEND_MTU[1]):
            raise NetworkException("Traffic between the hosts failed")
        logger.info("Traffic between the hosts succeed")

    @classmethod
    def teardown_class(cls):
        """
        Remove networks from the setup
        """
        logger.info("Starting the teardown_class")
        logger.info("Removing networks from the system")
        if not removeNetFromSetup(host=[config.HOSTS[0]],
                                  auto_nics=[config.HOST_NICS[0]],
                                  network=[config.VLAN_NETWORKS[0]]):
            raise NetworkException("Cannot remove networks from setup")

########################################################################

########################################################################


class JumboFrames_Case12_325531(TestCase):
    """
    Positive: Checking connectivity between two VMs over bond with the
    MTU configured
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Create a network over bond with MTU 9000 over DC/Cluster/Hosts
        """
        local_dict = {None: {'nic': config.BONDS[0], 'mode': 1,
                             'slaves': [config.HOST_NICS[2],
                                        config.HOST_NICS[3]]},
                      config.VLAN_NETWORKS[0]: {'nic': config.BONDS[0],
                                                'mtu': config.MTU[1],
                                                'vlan_id': config.VLAN_ID[0],
                                                'required': 'false'}}

        if not createAndAttachNetworkSN(data_center=config.DC_NAME,
                                        cluster=config.CLUSTER_NAME,
                                        host=[config.HOSTS[0],
                                              config.HOSTS[1]],
                                        network_dict=local_dict,
                                        auto_nics=[config.HOST_NICS[0]]):
            raise NetworkException("Cannot create and attach network")

        for i in range(2):
            logger.info("Adding %s as %s to %s",
                        config.VLAN_NETWORKS[0], config.VM_NIC_NAMES[1],
                        config.VM_NAME[i])
            if not addNic(positive=True,
                          vm=config.VM_NAME[i],
                          name=config.VM_NIC_NAMES[1],
                          network=config.VLAN_NETWORKS[0]):
                raise VMException("Cannot add vnic to VM")

            vm_ip = waitForIP(config.VM_NAME[i])[1]['ip']
            if not configureTempMTU(host=vm_ip,
                                    user=config.HOSTS_USER,
                                    password=config.HOSTS_PW,
                                    mtu=str(config.MTU[1])):
                raise VMException("Unable to configure vm's nic with MTU %s" %
                                  config.MTU[1])

    @istest
    @tcms(5848, 325531)
    def checkTrafficOnVmOverBond(self):
        """
        Send ping with MTU 8500 between the two VMS
        """
        ip_list = []
        for i in range(2):
            ip_list.append(waitForIP(config.VM_NAME[i])[1]['ip'])

        logger.info("Configuring %s with static IP on both VMs ",
                    config.VM_NICS[1])
        for i in range(2):
            if not configureTempStaticIp(host=ip_list[i],
                                         user=config.HOSTS_USER,
                                         password=config.HOSTS_PW,
                                         ip="%s%d" % (config.INTER_SUBNET,
                                                      i + 1),
                                         nic=config.VM_NICS[1]):
                logger.error("Couldn't configure temp ip on VMs")
                return False

        logger.info("Checking that sending ICMP traffic on %s "
                    "succeeds", config.VLAN_NETWORKS[0])
        if not checkICMPConnectivity(host=ip_list[0],
                                     user=config.HOSTS_USER,
                                     password=config.HOSTS_PW,
                                     ip=config.IPS[1],
                                     max_counter=config.TRAFFIC_TIMEOUT,
                                     packet_size=config.SEND_MTU[1]):
            raise Exception("Traffic between the hosts failed")
        logger.info("Traffic between the hosts succeed")

    @classmethod
    def teardown_class(cls):
        """
        Remove networks from the setup
        """
        logger.info("Starting the teardown")
        for i in range(2):
            logger.info("Unpluging %s at %s" % (config.VM_NIC_NAMES[1],
                                                config.VM_NAME[i]))
            if not updateNic(positive=True,
                             vm=config.VM_NAME[i],
                             nic=config.VM_NIC_NAMES[1],
                             plugged=False):
                logger.error("Unplug %s failed", config.VM_NIC_NAMES[1])

            logger.info("Removing %s from %s" % (config.VM_NIC_NAMES[1],
                                                 config.VM_NAME[i]))
            if not removeNic(positive=True,
                             vm=config.VM_NAME[i],
                             nic=config.VM_NIC_NAMES[1]):
                raise VMException("Cannot remove VNIC from %s"
                                  % (config.VM_NAME[i]))

        logger.info("Removing networks from the system")
        if not removeNetFromSetup(host=[config.HOSTS[0],
                                        config.HOSTS[1]],
                                  auto_nics=[config.HOST_NICS[0]],
                                  network=[config.VLAN_NETWORKS[0]]):
            raise NetworkException("Cannot remove networks from setup")

########################################################################

########################################################################


class JumboFrames_Case13_325544(TestCase):
    """
    Adding multiple vlans over bond, configuring different mtu's
    on each vlan, checking configuration directly on the host and checking
    connectivity between the hosts with the MTU configured
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Create networks over bond with different MTUs over DC/Cluster/Host
        Setting those networks on one host only
        """
        local_dict = {None: {'nic': config.BONDS[0], 'mode': 1,
                             'slaves': [config.HOST_NICS[2],
                                        config.HOST_NICS[3]]},
                      config.VLAN_NETWORKS[0]: {'nic': config.BONDS[0],
                                                'mtu': config.MTU[0],
                                                'vlan_id': config.VLAN_ID[0],
                                                'required': 'false'},
                      config.VLAN_NETWORKS[1]: {'nic': config.BONDS[0],
                                                'mtu': config.MTU[1],
                                                'bootproto': 'static',
                                                'address': [config.IPS[0]],
                                                'netmask': [config.NETMASK],
                                                'gateway': [config.GATEWAY],
                                                'vlan_id': config.VLAN_ID[1],
                                                'required': 'false'},
                      config.VLAN_NETWORKS[2]: {'nic': config.BONDS[0],
                                                'mtu': config.MTU[2],
                                                'vlan_id': config.VLAN_ID[2],
                                                'required': 'false'},
                      config.VLAN_NETWORKS[3]: {'nic': config.BONDS[0],
                                                'mtu': config.MTU[3],
                                                'vlan_id': config.VLAN_ID[3],
                                                'required': 'false'}}

        if not createAndAttachNetworkSN(data_center=config.DC_NAME,
                                        cluster=config.CLUSTER_NAME,
                                        host=[config.HOSTS[0]],
                                        network_dict=local_dict,
                                        auto_nics=[config.HOST_NICS[0]]):
            raise NetworkException("Cannot create and attach network")

    @istest
    @tcms(5848, 325544)
    def checkTrafficOnHostsWhenThereAreManyNetworks(self):
        """
        Checking that the highest MTU is configured on eth2, eth3 and bond0.
        also, checking that connectivity with MTU 8500 succeed between the
        hosts.
        """
        list_check_networks = [config.HOST_NICS[2],
                               config.HOST_NICS[3],
                               config.BONDS[0]]
        logger.info("Checking that networks and interfaces are "
                    "configured correctly")

        for element in list_check_networks:
            logger.info("Checking ifconfig for %s on the host %s",
                        element, config.HOSTS[0])
            self.assertTrue(checkConfiguredMTU(host=config.HOSTS[0],
                                               user=config.HOSTS_USER,
                                               password=config.HOSTS_PW,
                                               mtu=config.MTU[1],
                                               inter_or_net=element))

        logger.info("Checking logical layer for host %s", config.HOSTS[0])
        self.assertTrue(checkMTU(host=config.HOSTS[0], user=config.HOSTS_USER,
                                 password=config.HOSTS_PW, mtu=config.MTU[1],
                                 bond=config.BONDS[0],
                                 bond_nic1=config.HOST_NICS[2],
                                 bond_nic2=config.HOST_NICS[3],
                                 bridged=False),
                        "MTU on host %s should be %s and it is "
                        "not" % (config.HOSTS[0], config.MTU[0]))

        local_dict = {None: {'nic': config.BONDS[0], 'mode': 1,
                             'slaves': [config.HOST_NICS[2],
                                        config.HOST_NICS[3]]},
                      config.VLAN_NETWORKS[0]: {'nic': config.BONDS[0],
                                                'mtu': config.MTU[0],
                                                'vlan_id': config.VLAN_ID[0],
                                                'required': 'false'},
                      config.VLAN_NETWORKS[1]: {'nic': config.BONDS[0],
                                                'mtu': config.MTU[1],
                                                'bootproto': 'static',
                                                'address': [config.IPS[1]],
                                                'netmask': [config.NETMASK],
                                                'gateway': [config.GATEWAY],
                                                'vlan_id': config.VLAN_ID[1],
                                                'required': 'false'},
                      config.VLAN_NETWORKS[2]: {'nic': config.BONDS[0],
                                                'mtu': config.MTU[2],
                                                'vlan_id': config.VLAN_ID[2],
                                                'required': 'false'},
                      config.VLAN_NETWORKS[3]: {'nic': config.BONDS[0],
                                                'mtu': config.MTU[3],
                                                'vlan_id': config.VLAN_ID[3],
                                                'required': 'false'}}

        if not createAndAttachNetworkSN(host=[config.HOSTS[1]],
                                        network_dict=local_dict,
                                        auto_nics=[config.HOST_NICS[0]]):
            raise NetworkException("Cannot attach network to the second host")

        logger.info("Checking traffic between the two hosts")
        if not checkICMPConnectivity(host=config.HOSTS[0],
                                     user=config.HOSTS_USER,
                                     password=config.HOSTS_PW,
                                     ip=config.IPS[1],
                                     max_counter=config.TRAFFIC_TIMEOUT,
                                     packet_size=config.SEND_MTU[1]):
            raise Exception("Traffic between the hosts failed")
        logger.info("Traffic between the hosts succeed")

    @classmethod
    def teardown_class(cls):
        """
        Remove networks from the setup
        """
        logger.info("Starting the teardown")
        logger.info("Removing networks from the system")
        if not removeNetFromSetup(host=[config.HOSTS[0],
                                        config.HOSTS[1]],
                                  auto_nics=[config.HOST_NICS[0]],
                                  network=[config.VLAN_NETWORKS[0],
                                           config.VLAN_NETWORKS[1],
                                           config.VLAN_NETWORKS[2],
                                           config.VLAN_NETWORKS[3]]):
            raise NetworkException("Cannot remove networks from setup")

########################################################################

########################################################################


class JumboFrames_Case14_148654(TestCase):
    """
    Adding multiple vlans over bond, configuring different mtu's
    on each vlan and checking connectivity between the VMs with
    the MTU configured
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Create networks over bond with different MTUs over DC/Cluster/Hosts
        """
        local_dict = {None: {'nic': config.BONDS[0], 'mode': 1,
                             'slaves': [config.HOST_NICS[2],
                                        config.HOST_NICS[3]]},
                      config.VLAN_NETWORKS[0]: {'nic': config.BONDS[0],
                                                'mtu': config.MTU[0],
                                                'vlan_id': config.VLAN_ID[0],
                                                'required': 'false'},
                      config.VLAN_NETWORKS[1]: {'nic': config.BONDS[0],
                                                'mtu': config.MTU[1],
                                                'vlan_id': config.VLAN_ID[1],
                                                'required': 'false'}}

        if not createAndAttachNetworkSN(data_center=config.DC_NAME,
                                        cluster=config.CLUSTER_NAME,
                                        host=[config.HOSTS[0],
                                              config.HOSTS[1]],
                                        network_dict=local_dict,
                                        auto_nics=[config.HOST_NICS[0]]):
            raise NetworkException("Cannot create and attach network")

        for net_idx in range(2):
            for vm_idx in range(2):
                logger.info("Adding %s as %s to %s",
                            config.VLAN_NETWORKS[net_idx],
                            config.VM_NIC_NAMES[net_idx+1],
                            config.VM_NAME[vm_idx])

                if not addNic(positive=True,
                              vm=config.VM_NAME[vm_idx],
                              name=config.VM_NIC_NAMES[net_idx+1],
                              network=config.VLAN_NETWORKS[net_idx]):
                    raise VMException("Cannot add vnic to %s",
                                      config.VM_NAME[vm_idx])

                vm_ip = waitForIP(config.VM_NAME[vm_idx])[1]['ip']
                if not configureTempMTU(host=vm_ip,
                                        user=config.HOSTS_USER,
                                        password=config.HOSTS_PW,
                                        nic=config.HOST_NICS[net_idx+1],
                                        mtu=str(config.MTU[net_idx])):
                    raise VMException("Unable to configure vm's nic "
                                      "with MTU %s" % config.MTU[net_idx])

    @istest
    @tcms(5848, 148654)
    def checkTrafficOnVMsWhenHostHasManyNetworks(self):
        """
        Send ping with MTU 8500 between the two VMS
        """
        ip_list = []
        for i in range(2):
            ip_list.append(waitForIP(config.VM_NAME[i])[1]['ip'])

        logger.info("Configuring %s with static IP on both VMs ",
                    config.VM_NICS[2])
        for i in range(2):
            if not configureTempStaticIp(host=ip_list[i],
                                         user=config.HOSTS_USER,
                                         password=config.HOSTS_PW,
                                         ip="%s%d" % (config.INTER_SUBNET,
                                                      i + 1),
                                         nic=config.VM_NICS[2]):
                logger.error("Couldn't configure temp ip on VMs")
                return False

        logger.info("Checking traffic between the two VMs")
        if not checkICMPConnectivity(host=ip_list[0],
                                     user=config.HOSTS_USER,
                                     password=config.HOSTS_PW,
                                     ip=config.IPS[1],
                                     max_counter=config.TRAFFIC_TIMEOUT,
                                     packet_size=config.SEND_MTU[1]):
            raise Exception("Traffic between the hosts failed")
        logger.info("Traffic between the VMs succeed")

    @classmethod
    def teardown_class(cls):
        """
        Remove networks from the setup
        """
        logger.info("Starting the teardown")
        for vm_idx in range(2):
            for net_idx in range(2):
                logger.info("Unpluging %s from %s",
                            config.VM_NIC_NAMES[net_idx+1],
                            config.VM_NAME[vm_idx])
                if not updateNic(positive=True,
                                 vm=config.VM_NAME[vm_idx],
                                 nic=config.VM_NIC_NAMES[net_idx+1],
                                 plugged=False):
                    logger.error("Unplug %s failed",
                                 config.VM_NIC_NAMES[net_idx+1])

                logger.info("Removing %s from %s",
                            config.VM_NIC_NAMES[net_idx+1],
                            config.VM_NAME[vm_idx])
                if not removeNic(positive=True,
                                 vm=config.VM_NAME[vm_idx],
                                 nic=config.VM_NIC_NAMES[net_idx+1]):
                    raise VMException("Cannot remove VNIC from %s"
                                      % (config.VM_NAME[vm_idx]))

        logger.info("Removing networks from the system")
        if not removeNetFromSetup(host=[config.HOSTS[0],
                                        config.HOSTS[1]],
                                  auto_nics=[config.HOST_NICS[0]],
                                  network=[config.VLAN_NETWORKS[0],
                                           config.VLAN_NETWORKS[1]]):
            raise NetworkException("Cannot remove networks from setup")

########################################################################

########################################################################


class JumboFrames_Case15_167554(TestCase):
    """
    Positive: Creates 2 bridged vlan network with diffarent MTU values
    and as display, Attaching those networks to VMs and checking the traffic
    between them
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Create bridged networks with MTU on DC/Cluster/Hosts
        """

        local_dict = {config.VLAN_NETWORKS[0]: {'vlan_id': config.VLAN_ID[0],
                                                'mtu': config.MTU[0],
                                                'nic': config.HOST_NICS[1],
                                                'cluster_usages': 'display',
                                                'required': 'false'}}
        if not createAndAttachNetworkSN(data_center=config.DC_NAME,
                                        cluster=config.CLUSTER_NAME,
                                        host=[config.HOSTS[0],
                                              config.HOSTS[1]],
                                        network_dict=local_dict,
                                        auto_nics=[config.HOST_NICS[0],
                                                   config.HOST_NICS[1]]):
            raise NetworkException("Cannot create and attach network")

        for i in range(2):
            logger.info("Adding %s with to %s",
                        config.VLAN_NETWORKS[0], config.VM_NAME[i])
            if not addNic(positive=True,
                          vm=config.VM_NAME[i],
                          name=config.VM_NIC_NAMES[1],
                          network=config.VLAN_NETWORKS[0]):
                raise VMException("Cannot add vnic to %s", config.VM_NAME[i])

            vm_ip = waitForIP(config.VM_NAME[i])[1]['ip']
            if not configureTempMTU(host=vm_ip,
                                    user=config.HOSTS_USER,
                                    password=config.HOSTS_PW,
                                    mtu=str(config.MTU[0])):
                raise VMException("Unable to configure vm's nic with MTU %s" %
                                  config.MTU[0])

    @istest
    @tcms(5848, 167554)
    def checkTrafficOnVmWhenNetworkIsDisplay(self):
        """
        Send ping between 2 VMS
        """
        ip_list = []
        for i in range(2):
            ip_list.append(waitForIP(config.VM_NAME[i])[1]['ip'])

        logger.info("Configuring %s with static IP on both VMs ",
                    config.VM_NICS[1])
        for i in range(2):
            if not configureTempStaticIp(host=ip_list[i],
                                         user=config.HOSTS_USER,
                                         password=config.HOSTS_PW,
                                         ip="%s%d" % (config.INTER_SUBNET,
                                                      i + 1),
                                         nic=config.VM_NICS[1]):
                logger.error("Couldn't configure temp ip on VMs")
                return False

        logger.info("Checking traffic between the two VMs")
        if not checkICMPConnectivity(host=ip_list[0],
                                     user=config.HOSTS_USER,
                                     password=config.HOSTS_PW,
                                     ip=config.IPS[1],
                                     max_counter=config.TRAFFIC_TIMEOUT,
                                     packet_size=config.SEND_MTU[0]):
            raise Exception("Traffic between the hosts failed")
        logger.info("Traffic between the VMs succeed")

    @classmethod
    def teardown_class(cls):
        """
        Remove networks from the setup
        """
        logger.info("Starting the teardown")
        for i in range(2):
            logger.info("Unpluging %s at %s" % (config.VM_NIC_NAMES[1],
                                                config.VM_NAME[i]))
            if not updateNic(positive=True,
                             vm=config.VM_NAME[i],
                             nic=config.VM_NIC_NAMES[1],
                             plugged=False):
                logger.error("Unplug %s failed", config.VM_NIC_NAMES[1])

            logger.info("Removing %s from %s" % (config.VM_NIC_NAMES[1],
                                                 config.VM_NAME[i]))
            if not removeNic(positive=True,
                             vm=config.VM_NAME[i],
                             nic=config.VM_NIC_NAMES[1]):
                raise VMException("Cannot remove VNIC from %s"
                                  % (config.VM_NAME[i]))

        if not removeNetFromSetup(host=[config.HOSTS[0],
                                        config.HOSTS[1]],
                                  auto_nics=[config.HOST_NICS[0]],
                                  network=[config.VLAN_NETWORKS[0]]):
            raise NetworkException("Cannot remove networks from setup")

########################################################################

########################################################################


class JumboFrames_Case16_260611(TestCase):
    """
    Verify dedicated regular tagged network migration over Bond with MTU 9000
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Create logical tagged network on DC/Cluster with MTU 9000
        Configure it as migration network and attach it to Bond on the Host
        """
        local_dict = {None: {'nic': config.BONDS[0], 'mode': 1,
                             'slaves': [config.HOST_NICS[2],
                                        config.HOST_NICS[3]]},
                      config.VLAN_NETWORKS[0]: {'nic': config.BONDS[0],
                                                'mtu': 9000,
                                                'vlan_id': config.VLAN_ID[0],
                                                'required': 'true',
                                                'cluster_usages': 'migration',
                                                'bootproto': 'static',
                                                'address': [config.SOURCE_IP,
                                                            config.DEST_IP],
                                                'netmask': [config.NETMASK,
                                                            config.NETMASK]},
                      config.NETWORKS[1]: {'nic': config.HOST_NICS[1],
                                           'required': 'true'}}
        if not createAndAttachNetworkSN(data_center=config.DC_NAME,
                                        cluster=config.CLUSTER_NAME,
                                        host=config.HOSTS,
                                        network_dict=local_dict,
                                        auto_nics=[config.HOST_NICS[0]]):
            raise NetworkException("Cannot create and attach network")

    @istest
    @tcms(8735, 256582)
    def dedicated_migration(self):
        """
        Check migration over dedicated tagged network over bond
        """
        orig_host = getHost(config.VM_NAME[0])
        logger.info("Start migration from %s ", orig_host)
        src, dst = find_ip(vm=config.VM_NAME[0],
                           host_list=config.HOSTS,
                           nic='.'.join([config.BONDS[0], config.VLAN_ID[0]]))
        if not checkICMPConnectivity(host=orig_host, user=config.HOSTS_USER,
                                     password=config.HOSTS_PW, ip=dst):
            logger.error("ICMP wasn't established")
        with TrafficMonitor(machine=orig_host, user=config.HOSTS_USER,
                            password=config.HOSTS_PW,
                            nic='.'.join([config.BONDS[0], config.VLAN_ID[0]]),
                            src=src, dst=dst,
                            protocol='tcp',
                            numPackets=config.NUM_PACKETS) as monitor:
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
                                  network=[config.VLAN_NETWORKS[0],
                                           config.NETWORKS[1]]):
            raise NetworkException("Cannot remove network from setup")


########################################################################

########################################################################


# Function that returns source and destination ip for specific host
def find_ip(vm, host_list, nic):
    orig_host = getHost(vm)
    dst_host = host_list[(host_list.index(orig_host)+1) % len(host_list)]
    return getIpOnHostNic(orig_host, nic), getIpOnHostNic(dst_host, nic)


#  Function that returns host the specific VM resides on
def getHost(vm):
    rc, out = getVmHost(vm)
    if not rc:
        raise NetworkException("Cannot get host that VM resides on")
    return out['vmHoster']


skipBOND(["JumboFrames_Case03_197212",
          "JumboFrames_Case05_199741",
          "JumboFrames_Case06_199787",
          "JumboFrames_Case08_199787",
          "JumboFrames_Case09_199741",
          "JumboFrames_Case11_148668",
          "JumboFrames_Case13_325544",
          "JumboFrames_Case14_148654",
          "JumboFrames_Case16_260611"],
         config.HOST_NICS)
