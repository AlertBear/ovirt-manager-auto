"""
Testing Topologies feature.
1 DC, 1 Cluster, 1 Hosts and 1 VM will be created for testing.
"""

import config
import logging
from nose.tools import istest
from art.unittest_lib import BaseTestCase as TestCase
from art.rhevm_api.tests_lib.low_level.vms import checkVMConnectivity, \
    updateNic, startVm, stopVm
from art.test_handler.exceptions import NetworkException
from art.rhevm_api.tests_lib.high_level.networks import \
    createAndAttachNetworkSN, removeNetFromSetup

logger = logging.getLogger(__name__)

########################################################################

########################################################################
#                             Test Cases                               #
########################################################################


class TopologiesCase01(TestCase):
    """
    Check connectivity to VM with VLAN network
    Check virtIO, e1000 and rtl8139 drivers
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Create and attach VLAN network to host and VM
        """
        logger.info("Create and attach VLAN network")
        local_dict = {config.VLAN_NETWORKS[0]: {'vlan_id': config.VLAN_ID[0],
                                                'nic': config.HOST_NICS[1],
                                                'required': 'false'}}

        if not createAndAttachNetworkSN(data_center=config.DC_NAME,
                                        cluster=config.CLUSTER_NAME,
                                        host=config.HOSTS[0],
                                        network_dict=local_dict,
                                        auto_nics=[config.HOST_NICS[0],
                                                   config.HOST_NICS[1]]):
            raise NetworkException("Cannot create and attach network")

        logger.info("Update vNIC to VLAN network on VM")
        if not updateNic(positive=True, vm=config.VM_NAME[0], nic="nic1",
                         network=config.VLAN_NETWORKS[0],
                         vnic_profile=config.VLAN_NETWORKS[0]):
            raise NetworkException("Fail to update vNIC to VLAN network on "
                                   "VM")

        logger.info("Start VM")
        if not startVm(positive=True, vm=config.VM_NAME[0]):
            raise NetworkException("Fail to start VM")

    @istest
    def vlan_network_01_virtio(self):
        """
        Check connectivity to VLAN network with virtIO driver
        """
        logger.info("Check connectivity to VLAN network with virtIO driver")
        if not checkVMConnectivity(positive=True, vm=config.VM_NAME[0],
                                   osType="rhel", user=config.HOSTS_USER,
                                   password=config.HOSTS_PW):
            raise NetworkException("Connectivity failed to VLAN network")

    @istest
    def vlan_network_02_e1000(self):
        """
        Check connectivity to VLAN network with e1000 driver
        """
        logger.info("Stop VM")
        if not stopVm(positive=True, vm=config.VM_NAME[0]):
            raise NetworkException("Fail to stop VM")

        if not updateNic(positive=True, vm=config.VM_NAME[0], nic="nic1",
                         interface="e1000"):
            raise NetworkException("Fail to update vNIC to e1000 driver")

        logger.info("Start VM")
        if not startVm(positive=True, vm=config.VM_NAME[0]):
            raise NetworkException("Fail to start VM")

        logger.info("Check connectivity to VLAN network with e1000 driver")
        if not checkVMConnectivity(positive=True, vm=config.VM_NAME[0],
                                   osType="rhel", user=config.HOSTS_USER,
                                   password=config.HOSTS_PW):
            raise NetworkException("Connectivity failed to VLAN network with "
                                   "e1000 driver")

    @istest
    def vlan_network_03_rtl8139(self):
        """
        Check connectivity to VLAN network with rtl8139 driver
        """
        logger.info("Stop VM")
        if not stopVm(positive=True, vm=config.VM_NAME[0]):
            raise NetworkException("Fail to stop VM")

        if not updateNic(positive=True, vm=config.VM_NAME[0], nic="nic1",
                         interface="rtl8139"):
            raise NetworkException("Fail to update vNIC to rtl8139 driver")

        logger.info("Start VM")
        if not startVm(positive=True, vm=config.VM_NAME[0]):
            raise NetworkException("Fail to start VM")

        logger.info("Check connectivity to VLAN network with e1000 driver")
        if not checkVMConnectivity(positive=True, vm=config.VM_NAME[0],
                                   osType="rhel", user=config.HOSTS_USER,
                                   password=config.HOSTS_PW):
            raise NetworkException("Connectivity failed to VLAN network with "
                                   "rtl8139 driver")

    @classmethod
    def teardown_class(cls):
        """
        Remove network from setup
        """
        logger.info("Stop VM")
        if not stopVm(positive=True, vm=config.VM_NAME[0]):
            raise NetworkException("Fail to stop VM")

        logger.info("Update vNIC to RHEVM network on VM")
        if not updateNic(positive=True, vm=config.VM_NAME[0], nic="nic1",
                         network=config.MGMT_BRIDGE, interface="virtio",
                         vnic_profile=config.MGMT_BRIDGE):
            raise NetworkException("Fail to update vNIC to RHEVM network on "
                                   "VM")

        logger.info("Remove network from setup")
        if not removeNetFromSetup(host=config.HOSTS[0],
                                  auto_nics=[config.HOST_NICS[0]],
                                  network=[config.VLAN_NETWORKS[0]]):
            raise NetworkException("Cannot remove network from setup")

##############################################################################


class TopologiesCase02(TestCase):
    """
    Check connectivity to VM with VLAN over BOND network
    Check virtIO, e1000 and rtl8139 drivers
    """
    __test__ = len(config.HOST_NICS) >= 4

    @classmethod
    def setup_class(cls):
        """
        Create and attach VLAN over BOND network to host and VM
        """
        logger.info("Create and attach VLAN over BOND network")
        local_dict = {None: {"nic": config.BOND[0], "mode": 1,
                             "slaves": [config.HOST_NICS[2],
                                        config.HOST_NICS[3]]},
                      config.VLAN_NETWORKS[0]: {"nic": config.BOND[0],
                                                "vlan_id": config.VLAN_ID[0],
                                                "required": "false"}}

        if not createAndAttachNetworkSN(data_center=config.DC_NAME,
                                        cluster=config.CLUSTER_NAME,
                                        host=config.HOSTS[0],
                                        network_dict=local_dict,
                                        auto_nics=[config.HOST_NICS[0]]):
            raise NetworkException("Cannot create and attach network")

        logger.info("Update vNIC to VLAN over BOND network on VM")
        if not updateNic(positive=True, vm=config.VM_NAME[0], nic="nic1",
                         network=config.VLAN_NETWORKS[0],
                         vnic_profile=config.VLAN_NETWORKS[0]):
            raise NetworkException("Fail to update vNIC to VLAN over BOND "
                                   "network on VM")

        logger.info("Start VM")
        if not startVm(positive=True, vm=config.VM_NAME[0]):
            raise NetworkException("Fail to start VM")

    @istest
    def vlan_over_bond_network_01_virtio(self):
        """
        Check connectivity to VLAN over BOND network with virtIO driver
        """
        logger.info("Check connectivity to VLAN over BOND network with "
                    "virtIO driver")
        if not checkVMConnectivity(positive=True, vm=config.VM_NAME[0],
                                   osType="rhel", user=config.HOSTS_USER,
                                   password=config.HOSTS_PW):
            raise NetworkException("Connectivity failed to VLAN over BOND "
                                   "network with virtIO driver")

    @istest
    def vlan_over_bond_network_02_e1000(self):
        """
        Check connectivity to VLAN over BOND network with e1000 driver
        """
        logger.info("Stop VM")
        if not stopVm(positive=True, vm=config.VM_NAME[0]):
            raise NetworkException("Fail to stop VM")

        if not updateNic(positive=True, vm=config.VM_NAME[0], nic="nic1",
                         interface="e1000"):
            raise NetworkException("Fail to update vNIC to e1000 driver")

        logger.info("Start VM")
        if not startVm(positive=True, vm=config.VM_NAME[0]):
            raise NetworkException("Fail to start VM")

        logger.info("Check connectivity to VLAN over BOND network with e1000 "
                    "driver")
        if not checkVMConnectivity(positive=True, vm=config.VM_NAME[0],
                                   osType="rhel", user=config.HOSTS_USER,
                                   password=config.HOSTS_PW):
            raise NetworkException("Connectivity failed to VLAN over "
                                   "BOND network with e1000 driver")

    @istest
    def vlan_over_bond_network_03_rtl8139(self):
        """
        Check connectivity to VLAN over BOND network with rtl8139 driver
        """
        logger.info("Stop VM")
        if not stopVm(positive=True, vm=config.VM_NAME[0]):
            raise NetworkException("Fail to stop VM")

        if not updateNic(positive=True, vm=config.VM_NAME[0], nic="nic1",
                         interface="rtl8139"):
            raise NetworkException("Fail to update vNIC to rtl8139 driver")

        logger.info("Start VM")
        if not startVm(positive=True, vm=config.VM_NAME[0]):
            raise NetworkException("Fail to start VM")

        logger.info("Check connectivity to VLAN over BOND network with e1000 "
                    "driver")
        if not checkVMConnectivity(positive=True, vm=config.VM_NAME[0],
                                   osType="rhel", user=config.HOSTS_USER,
                                   password=config.HOSTS_PW):
            raise NetworkException("Connectivity failed to VLAN over "
                                   "BOND network with rtl8139 driver")

    @classmethod
    def teardown_class(cls):
        """
        Remove network from setup
        """
        logger.info("Stop VM")
        if not stopVm(positive=True, vm=config.VM_NAME[0]):
            raise NetworkException("Fail to stop VM")

        logger.info("Update vNIC to RHEVM network on VM")
        if not updateNic(positive=True, vm=config.VM_NAME[0], nic="nic1",
                         network=config.MGMT_BRIDGE, interface="virtio",
                         vnic_profile=config.MGMT_BRIDGE):
            raise NetworkException("Fail to update vNIC to RHEVM network on "
                                   "VM")

        logger.info("Remove network from setup")
        if not removeNetFromSetup(host=config.HOSTS[0],
                                  auto_nics=[config.HOST_NICS[0]],
                                  network=[config.VLAN_NETWORKS[0]]):
            raise NetworkException("Cannot remove network from setup")


##############################################################################


class TopologiesCase03(TestCase):
    """
    Check connectivity to VM with BOND network
    Check virtIO, e1000 and rtl8139 drivers
    """
    __test__ = len(config.HOST_NICS) >= 4

    @classmethod
    def setup_class(cls):
        """
        Create and attach BOND network to host and VM
        """
        logger.info("Create and attach BOND network")
        local_dict = {config.NETWORKS[0]: {"nic": config.BOND[0], "mode": 1,
                                           "slaves": [config.HOST_NICS[2],
                                                      config.HOST_NICS[3]]}}

        if not createAndAttachNetworkSN(data_center=config.DC_NAME,
                                        cluster=config.CLUSTER_NAME,
                                        host=config.HOSTS[0],
                                        network_dict=local_dict,
                                        auto_nics=[config.HOST_NICS[0]]):
            raise NetworkException("Cannot create and attach network")

        logger.info("Update vNIC to BOND network on VM")
        if not updateNic(positive=True, vm=config.VM_NAME[0], nic="nic1",
                         network=config.NETWORKS[0],
                         vnic_profile=config.NETWORKS[0]):
            raise NetworkException("Fail to update vNIC to BOND "
                                   "network on VM")

        logger.info("Start VM")
        if not startVm(positive=True, vm=config.VM_NAME[0]):
            raise NetworkException("Fail to start VM")

    @istest
    def bond_network_01_virtio(self):
        """
        Check connectivity to VLAN network with virtIO driver
        """
        logger.info("Check connectivity to BOND network")
        if not checkVMConnectivity(positive=True, vm=config.VM_NAME[0],
                                   osType="rhel", user=config.HOSTS_USER,
                                   password=config.HOSTS_PW):
            raise NetworkException("Connectivity failed to BOND network with "
                                   "virtIO driver")

    @istest
    def bond_network_02_e1000(self):
        """
        Check connectivity to VLAN over BOND network with e1000 driver
        """
        logger.info("Stop VM")
        if not stopVm(positive=True, vm=config.VM_NAME[0]):
            raise NetworkException("Fail to stop VM")

        if not updateNic(positive=True, vm=config.VM_NAME[0], nic="nic1",
                         interface="e1000"):
            raise NetworkException("Fail to update vNIC to e1000 driver")

        logger.info("Start VM")
        if not startVm(positive=True, vm=config.VM_NAME[0]):
            raise NetworkException("Fail to start VM")

        logger.info("Check connectivity to BOND network with e1000 driver")
        if not checkVMConnectivity(positive=True, vm=config.VM_NAME[0],
                                   osType="rhel", user=config.HOSTS_USER,
                                   password=config.HOSTS_PW):
            raise NetworkException("Connectivity failed to BOND network with "
                                   "e1000 driver")

    @istest
    def bond_network_03_rtl8139(self):
        """
        Check connectivity to VLAN over BOND network with rtl8139 driver
        """
        logger.info("Stop VM")
        if not stopVm(positive=True, vm=config.VM_NAME[0]):
            raise NetworkException("Fail to stop VM")

        if not updateNic(positive=True, vm=config.VM_NAME[0], nic="nic1",
                         interface="rtl8139"):
            raise NetworkException("Fail to update vNIC to rtl8139 driver")

        logger.info("Start VM")
        if not startVm(positive=True, vm=config.VM_NAME[0]):
            raise NetworkException("Fail to start VM")

        logger.info("Check connectivity to BOND network with e1000 driver")
        if not checkVMConnectivity(positive=True, vm=config.VM_NAME[0],
                                   osType="rhel", user=config.HOSTS_USER,
                                   password=config.HOSTS_PW):
            raise NetworkException("Connectivity failed to BOND network with "
                                   "rtl8139 driver")

    @classmethod
    def teardown_class(cls):
        """
        Remove network from setup
        """
        logger.info("Stop VM")
        if not stopVm(positive=True, vm=config.VM_NAME[0]):
            raise NetworkException("Fail to stop VM")

        logger.info("Update vNIC to RHEVM network on VM")
        if not updateNic(positive=True, vm=config.VM_NAME[0], nic="nic1",
                         network=config.MGMT_BRIDGE, interface="virtio",
                         vnic_profile=config.MGMT_BRIDGE):
            raise NetworkException("Fail to update vNIC to RHEVM network on "
                                   "VM")

        logger.info("Remove network from setup")
        if not removeNetFromSetup(host=config.HOSTS[0],
                                  auto_nics=[config.HOST_NICS[0]],
                                  network=[config.NETWORKS[0]]):
            raise NetworkException("Cannot remove network from setup")
