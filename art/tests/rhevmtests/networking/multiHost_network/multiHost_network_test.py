"""
Testing MultiHost feature.
1 DC, 1 Cluster, 2 Hosts and 2 VMs will be created for testing.
MultiHost will be tested for untagged, tagged, MTU, VM/non-VM and bond
scenarios.
"""

from nose.tools import istest
from art.unittest_lib import attr
from art.rhevm_api.tests_lib.low_level.clusters import addCluster,\
    removeCluster
from art.rhevm_api.tests_lib.low_level.datacenters import addDataCenter, \
    removeDataCenter
from art.unittest_lib import NetworkTest as TestCase
import logging
from rhevmtests.networking import config
import time
from art.rhevm_api.utils.test_utils import checkMTU
from art.test_handler.exceptions import NetworkException
from art.test_handler.tools import tcms
from art.core_api.apis_utils import TimeoutingSampler
from art.rhevm_api.tests_lib.high_level.networks import\
    createAndAttachNetworkSN, removeNetFromSetup, checkHostNicParameters
from art.rhevm_api.tests_lib.low_level.networks import\
    updateNetwork, checkVlanNet, isVmHostNetwork
from art.rhevm_api.tests_lib.low_level.hosts import sendSNRequest, \
    deactivateHost, updateHost, activateHost, attachHostNic, detachHostNic
from art.rhevm_api.tests_lib.low_level.vms import addNic, removeNic, updateNic
from art.rhevm_api.tests_lib.low_level.templates import addTemplateNic,\
    removeTemplateNic

logger = logging.getLogger(__name__)

########################################################################

########################################################################
#                             Test Cases                               #
########################################################################


@attr(tier=1)
class MultiHostCase01(TestCase):
    """
    Update untagged network with VLAN
    Update tagged network with another VLAN
    Update tagged network to be untagged
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Create untagged network on DC/Cluster/Host
        """
        local_dict = {config.VLAN_NETWORKS[0]: {"nic": config.HOST_NICS[1],
                                                "required": "false"}}

        logger.info("Attach network to DC/Cluster and Host")
        if not createAndAttachNetworkSN(data_center=config.DC_NAME[0],
                                        cluster=config.CLUSTER_NAME[0],
                                        host=config.HOSTS[0],
                                        network_dict=local_dict,
                                        auto_nics=[config.HOST_NICS[0]]):
            raise NetworkException("Cannot create and attach network")

    @istest
    @tcms(12030, 331894)
    def update_with_vlan(self):
        """
        1) Update network with VLAN 162
        2) Check that the Host was updated with VLAN 162
        3) Update network with VLAN 163
        4) Check that the Host was updated with VLAN 163
        5) Update network with VLAN 163 to be untagged
        6) Check that the Host was updated as well
        """
        vlan_dict1 = {"vlan_id": config.VLAN_ID[0]}
        vlan_dict2 = {"vlan_id": config.VLAN_ID[1]}

        logger.info("Update network with VLAN %s", config.VLAN_ID[0])
        if not updateNetwork(True, network=config.VLAN_NETWORKS[0],
                             data_center=config.DC_NAME[0],
                             vlan_id=config.VLAN_ID[0]):
            raise NetworkException("Cannot update network to be tagged with "
                                   "VLAN %s" % config.VLAN_ID[0])

        logger.info("Wait till the Host is updated with the change")
        sample1 = TimeoutingSampler(
            timeout=config.SAMPLER_TIMEOUT,
            sleep=1,
            func=checkHostNicParameters,
            host=config.HOSTS[0],
            nic=config.HOST_NICS[1],
            **vlan_dict1
        )
        if not sample1.waitForFuncStatus(result=True):
            raise NetworkException("Couldn't get correct VLAN interface on "
                                   "host")

        logger.info("Check that the change is reflected to Host")
        if not checkVlanNet(host=config.HOSTS[0], user=config.HOSTS_USER,
                            password=config.HOSTS_PW,
                            interface=config.HOST_NICS[1],
                            vlan=config.VLAN_ID[0]):
            raise NetworkException("Host %s was not updated with correct "
                                   "VLAN %s" % (config.HOSTS[0],
                                                config.VLAN_ID[0]))

        logger.info("Update network with VLAN %s", config.VLAN_ID[1])
        if not updateNetwork(True, network=config.VLAN_NETWORKS[0],
                             data_center=config.DC_NAME[0],
                             vlan_id=config.VLAN_ID[1]):
            raise NetworkException("Cannot update network to be tagged with "
                                   "VLAN %s" % config.VLAN_ID[1])

        logger.info("Wait till the Host is updated with the change")
        sample2 = TimeoutingSampler(
            timeout=config.SAMPLER_TIMEOUT,
            sleep=1,
            func=checkHostNicParameters,
            host=config.HOSTS[0],
            nic=config.HOST_NICS[1],
            **vlan_dict2
        )
        if not sample2.waitForFuncStatus(result=True):
            raise NetworkException("Couldn't get correct vlan interface on "
                                   "host")

        logger.info("Check that the change is reflected to Host")
        if not checkVlanNet(host=config.HOSTS[0], user=config.HOSTS_USER,
                            password=config.HOSTS_PW,
                            interface=config.HOST_NICS[1],
                            vlan=config.VLAN_ID[1]):
            raise NetworkException("Host %s was not updated with correct "
                                   "VLAN %s" % (config.HOSTS[0],
                                                config.VLAN_ID[1]))

        logger.info("Update network to be untagged")
        if not updateNetwork(True, network=config.VLAN_NETWORKS[0],
                             data_center=config.DC_NAME[0],
                             vlan_id=None):
            raise NetworkException("Cannot update network to be untagged")

        logger.info("Wait till the Host is updated with the change")
        if not sample2.waitForFuncStatus(result=False):
            raise NetworkException("Could get VLAN interface on host but "
                                   "shouldn't")

        logger.info("Check that the change is reflected to Host")
        if checkVlanNet(host=config.HOSTS[0], user=config.HOSTS_USER,
                        password=config.HOSTS_PW,
                        interface=config.HOST_NICS[1],
                        vlan=config.VLAN_ID[1]):
            raise NetworkException("Network on Host %s was not updated to be "
                                   "untagged" % config.HOSTS[0])

    @classmethod
    def teardown_class(cls):
        """
        Remove network from the setup.
        """
        logger.info("Remove networks from setup")
        if not removeNetFromSetup(host=config.HOSTS[0],
                                  auto_nics=[config.HOST_NICS[0]],
                                  network=[config.VLAN_NETWORKS[0]]):
            raise NetworkException("Cannot remove network from setup")


@attr(tier=1)
class MultiHostCase02(TestCase):
    """
    Update network with the default MTU to the MTU of 9000
    Update network to have default MTU value
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Create and attach network on DC, Cluster and the host
        """
        dict_dc1 = {config.NETWORKS[0]: {"nic": config.HOST_NICS[1],
                                         "required": "false"}}

        logger.info("Attach network to DC/Cluster/Host")
        if not createAndAttachNetworkSN(data_center=config.DC_NAME[0],
                                        cluster=config.CLUSTER_NAME[0],
                                        host=config.HOSTS[0],
                                        network_dict=dict_dc1,
                                        auto_nics=[config.HOST_NICS[0]]):
            raise NetworkException("Cannot create and attach network")

    @istest
    @tcms(12030, 331895)
    def update_with_mtu(self):
        """
        1) Update network with MTU 9000
        2) Check that the Host was updated with MTU 9000
        3) Update network with MTU 1500
        4) Check that the Host was updated with MTU 1500
        """
        mtu_dict1 = {"mtu": config.MTU[0]}
        mtu_dict2 = {"mtu": config.MTU[-1]}

        logger.info("Update network with MTU %s", config.MTU[0])
        if not updateNetwork(True, network=config.NETWORKS[0],
                             data_center=config.DC_NAME[0],
                             mtu=config.MTU[0]):
            raise NetworkException("Cannot update  network with  MTU %s" %
                                   config.MTU[0])

        logger.info("Wait till the Host is updated with the change")
        sample1 = TimeoutingSampler(
            timeout=config.SAMPLER_TIMEOUT,
            sleep=1,
            func=checkHostNicParameters,
            host=config.HOSTS[0],
            nic=config.HOST_NICS[1],
            **mtu_dict1
        )
        if not sample1.waitForFuncStatus(result=True):
            raise NetworkException("Couldn't get correct MTU on host")

        logger.info("Check that the change is reflected to Host")
        logger.info("Checking logical layer of bridged network %s on host %s",
                    config.NETWORKS[0], config.HOSTS[0])
        self.assertTrue(checkMTU(host=config.HOSTS[0], user=config.HOSTS_USER,
                                 password=config.HOSTS_PW, mtu=config.MTU[0],
                                 physical_layer=False,
                                 network=config.NETWORKS[0],
                                 nic=config.HOST_NICS[1]))

        logger.info("Checking physical layer of bridged network %s on host "
                    "%s", config.NETWORKS[0], config.HOSTS[0])
        self.assertTrue(checkMTU(host=config.HOSTS[0], user=config.HOSTS_USER,
                                 password=config.HOSTS_PW, mtu=config.MTU[0],
                                 nic=config.HOST_NICS[1]))

        logger.info("Update MTU network with MTU %s", config.MTU[-1])
        if not updateNetwork(True, network=config.NETWORKS[0],
                             data_center=config.DC_NAME[0],
                             mtu=config.MTU[-1]):
            raise NetworkException("Cannot update network with MTU %s" %
                                   config.MTU[-1])

        logger.info("Wait till the Host is updated with the change")
        sample2 = TimeoutingSampler(
            timeout=config.SAMPLER_TIMEOUT,
            sleep=1,
            func=checkHostNicParameters,
            host=config.HOSTS[0],
            nic=config.HOST_NICS[1],
            **mtu_dict2
        )
        if not sample2.waitForFuncStatus(result=True):
            raise NetworkException("Couldn't get correct MTU on host")

        logger.info("Check that the change is reflected to Host")
        logger.info("Checking logical layer of bridged network %s on host "
                    "%s", config.NETWORKS[0], config.HOSTS[0])
        self.assertTrue(checkMTU(host=config.HOSTS[0], user=config.HOSTS_USER,
                                 password=config.HOSTS_PW, mtu=config.MTU[-1],
                                 physical_layer=False,
                                 network=config.NETWORKS[0],
                                 nic=config.HOST_NICS[1]))

        logger.info("Checking physical layer of bridged network %s on host %s"
                    % (config.NETWORKS[0], config.HOSTS[0]))
        self.assertTrue(checkMTU(host=config.HOSTS[0], user=config.HOSTS_USER,
                                 password=config.HOSTS_PW, mtu=config.MTU[-1],
                                 nic=config.HOST_NICS[1]))

    @classmethod
    def teardown_class(cls):
        """
        Remove network from the setup.
        """
        logger.info("Remove network from setup")
        if not removeNetFromSetup(host=config.HOSTS[0],
                                  auto_nics=[config.HOST_NICS[0]],
                                  network=[config.NETWORKS[0]]):
            raise NetworkException("Cannot remove network from setup")


@attr(tier=1)
class MultiHostCase03(TestCase):
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

        dict_dc1 = {config.NETWORKS[0]: {"nic": config.HOST_NICS[1],
                                         "required": "false"}}

        logger.info("Attach network to DC/Cluster/Host")
        if not createAndAttachNetworkSN(data_center=config.DC_NAME[0],
                                        cluster=config.CLUSTER_NAME[0],
                                        host=config.HOSTS[0],
                                        network_dict=dict_dc1,
                                        auto_nics=[config.HOST_NICS[0]]):
            raise NetworkException("Cannot create and attach network")

    @istest
    @tcms(12030, 331911)
    def update_with_non_vm_nonvm(self):
        """
        1) Update network to be non-VM network
        2) Check that the Host was updated accordingly
        3) Update network to be VM network
        4) Check that the Host was updated accordingly
        """
        bridge_dict1 = {"bridge": False}
        bridge_dict2 = {"bridge": True}

        logger.info("Update network %s to be non-VM network",
                    config.NETWORKS[0])
        if not updateNetwork(True, network=config.NETWORKS[0],
                             data_center=config.DC_NAME[0], usages=""):
            raise NetworkException("Cannot update network to be non-VM "
                                   "network")

        logger.info("Wait till the Host is updated with the change")
        sample1 = TimeoutingSampler(
            timeout=config.SAMPLER_TIMEOUT,
            sleep=1,
            func=checkHostNicParameters,
            host=config.HOSTS[0],
            nic=config.HOST_NICS[1],
            **bridge_dict1
        )
        if not sample1.waitForFuncStatus(result=True):
            raise NetworkException("Network is VM network and should be "
                                   "Non-VM")

        logger.info("Check that the change is reflected to Host")
        if isVmHostNetwork(host=config.HOSTS[0], user=config.HOSTS_USER,
                           password=config.HOSTS_PW,
                           net_name=config.NETWORKS[0], conn_timeout=45):
            raise NetworkException("Network on host %s was not updated to be "
                                   "non-VM network" % config.HOSTS[0])

        logger.info("Update network %s to be VM network", config.NETWORKS[0])
        if not updateNetwork(True, network=config.NETWORKS[0],
                             data_center=config.DC_NAME[0],
                             usages="vm"):
            raise NetworkException("Cannot update network to be VM network")

        logger.info("Wait till the Host is updated with the change")
        sample2 = TimeoutingSampler(
            timeout=config.SAMPLER_TIMEOUT,
            sleep=1,
            func=checkHostNicParameters,
            host=config.HOSTS[0],
            nic=config.HOST_NICS[1],
            **bridge_dict2
        )
        if not sample2.waitForFuncStatus(result=True):
            raise NetworkException("Network is not a VM network but should be")

        logger.info("Check that the change is reflected to Host")
        if not isVmHostNetwork(host=config.HOSTS[0], user=config.HOSTS_USER,
                               password=config.HOSTS_PW,
                               net_name=config.NETWORKS[0]):
            raise NetworkException("Network on host %s was not updated to be "
                                   "VM network" % config.HOSTS[0])

    @classmethod
    def teardown_class(cls):
        """
        Remove network from the setup.
        """
        logger.info("Remove network from setup")
        if not removeNetFromSetup(host=config.HOSTS[0],
                                  auto_nics=[config.HOST_NICS[0]],
                                  network=[config.NETWORKS[0]]):
            raise NetworkException("Cannot remove network from setup")


@attr(tier=1)
class MultiHostCase04(TestCase):
    """
    Update network name:
    1) Negative when host is using it
    2) Negative when VM is using it (even non-running one)
    3) Negative when template is using it
    4) Positive when only DC/Cluster are using it
    Update non-VM network to be VM network
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Create and attach network on DC, Cluster and the host
        """

        dict_dc1 = {config.NETWORKS[0]: {"nic": config.HOST_NICS[1],
                                         "required": "false"}}

        logger.info("Attach network to DC/Cluster/Host")
        if not createAndAttachNetworkSN(data_center=config.DC_NAME[0],
                                        cluster=config.CLUSTER_NAME[0],
                                        host=config.HOSTS[0],
                                        network_dict=dict_dc1,
                                        auto_nics=[config.HOST_NICS[0]]):
            raise NetworkException("Cannot create and attach network")

    @istest
    @tcms(12030, 331896)
    def update_net_name(self):
        """
        1) Try to update network name when the network resides on the Host
        2) Try to update network name when the network resides on VM
        3) Try to update network name when the network resides on Template
        All cases should fail being negative cases
        4) Update network name when the network resides only on DC and Cluster
        Test should succeed
        """

        logger.info("Negative: Try to update network name when network "
                    "resides on host")
        if not updateNetwork(False, network=config.NETWORKS[0],
                             data_center=config.DC_NAME[0],
                             name=config.NETWORKS[1]):
            raise NetworkException("Could update network name when shouldn't")

        logger.info("Remove network from the Host")
        if not sendSNRequest(True, host=config.HOSTS[0],
                             auto_nics=[config.HOST_NICS[0]],
                             check_connectivity="true",
                             connectivity_timeout=config.CONNECT_TIMEOUT,
                             force="false"):
            raise NetworkException("Cannot remove Network from Host")

        logger.info("Add network to the non-running VM")
        if not addNic(True, config.VM_NAME[1], name="nic2",
                      network=config.NETWORKS[0]):
            raise NetworkException("Cannot add VNIC to VM")

        logger.info("Negative: Try to update network name when network "
                    "resides on VM")
        if not updateNetwork(False, network=config.NETWORKS[0],
                             data_center=config.DC_NAME[0],
                             name=config.NETWORKS[1]):
            raise NetworkException("Could update network name when shouldn't")

        logger.info("Remove network from VM")
        if not removeNic(True, config.VM_NAME[1], "nic2"):
            raise NetworkException("Cannot remove NIC from VM")

        logger.info("Put network on the Template")
        if not addTemplateNic(True, config.TEMPLATE_NAME[0], name="nic2",
                              data_center=config.DC_NAME[0],
                              network=config.NETWORKS[0]):
            raise NetworkException("Cannot add NIC to Template")

        logger.info("Negative: Try to update network name when network "
                    "resides on Template")
        if not updateNetwork(False, network=config.NETWORKS[0],
                             data_center=config.DC_NAME[0],
                             name=config.NETWORKS[1]):
            raise NetworkException("Could update network name when shouldn't")

        logger.info("Remove network from Template")
        if not removeTemplateNic(True, config.TEMPLATE_NAME[0], "nic2"):
            raise NetworkException("Cannot remove nic from Template")

        logger.info("Update network name when network resides only on "
                    "DC and Cluster")
        if not updateNetwork(True, network=config.NETWORKS[0],
                             data_center=config.DC_NAME[0],
                             name=config.NETWORKS[1]):
            raise NetworkException("Couldn't update network name when should")

    @classmethod
    def teardown_class(cls):
        """
        Remove network from the setup.
        """
        logger.info("Remove network from setup")
        if not removeNetFromSetup(host=config.HOSTS[0],
                                  auto_nics=[config.HOST_NICS[0]],
                                  network=[config.NETWORKS[1]]):
            raise NetworkException("Cannot remove network from setup")


@attr(tier=1)
class MultiHostCase05(TestCase):
    """
    Update network on running/non-running VM:
    1) Negative: Try to change MTU on net when running VM is using it
    2) Negative: Try to change VLAN on net when running VM is using it
    3) Positive: Try to change MTU on net when non-running VM is using it
    4) Positive: Try to change VLAN on net when non-running VM is using it
    5) Negative: Update non-VM network to be VM network used by non-running VM
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Create and attach network on DC, Cluster,Host, running and
        non-running VMs
        """

        dict_dc1 = {config.NETWORKS[0]: {"nic": config.HOST_NICS[1],
                                         "required": "false"}}

        logger.info("Attach network to DC/Cluster/Host")
        if not createAndAttachNetworkSN(data_center=config.DC_NAME[0],
                                        cluster=config.CLUSTER_NAME[0],
                                        host=config.HOSTS[0],
                                        network_dict=dict_dc1,
                                        auto_nics=[config.HOST_NICS[0]]):
            raise NetworkException("Cannot create and attach network")

        logger.info("Add network to running and non-running VMs")
        for i in range(2):
            if not addNic(True, config.VM_NAME[i], name="nic2",
                          network=config.NETWORKS[0]):
                raise NetworkException("Cannot add VNIC %s for network to "
                                       "VM %s " % (config.NETWORKS[0],
                                                   config.VM_NAME[i]))

    @istest
    @tcms(12030, 331909)
    def update_net_on_vm(self):
        """
        1) Negative: Try to change MTU on net when running VM is using it
        2) Negative: Try to change VLAN on net when running VM is using it
        3) Positive: Try to change MTU on net when non-running VM is using it
        4) Positive: Try to change VLAN on net when non-running VM is using it
        5) Negative: Update non-VM network to be VM network used by
        non-running VM
        """

        mtu_dict1 = {"mtu": config.MTU[0]}
        vlan_dict1 = {"vlan_id": config.VLAN_ID[0]}

        logger.info("Negative: Update MTU network with MTU %s", config.MTU[0])
        if not updateNetwork(False, network=config.NETWORKS[0],
                             data_center=config.DC_NAME[0],
                             mtu=config.MTU[0]):
            raise NetworkException("Could update  network with MTU %s "
                                   "when running VM is using the network" %
                                   config.MTU[0])

        logger.info("Negative: Update network with VLAN %s", config.VLAN_ID[0])
        if not updateNetwork(False, network=config.NETWORKS[0],
                             data_center=config.DC_NAME[0],
                             vlan_id=config.VLAN_ID[0]):
            raise NetworkException("Could update network to be tagged with "
                                   "VLAN %s when running VM is using the"
                                   " network" % config.VLAN_ID[0])

        logger.info("Unplugging NIC with the network in order "
                    "to be able to update the Network that reside on that NIC")
        if not updateNic(True, config.VM_NAME[0], "nic2",
                         plugged="false"):
            raise NetworkException("Couldn't unplug NIC")

        logger.info("Update MTU network with MTU %s", config.MTU[0])
        if not updateNetwork(True, network=config.NETWORKS[0],
                             data_center=config.DC_NAME[0],
                             mtu=config.MTU[0]):
            raise NetworkException("Couldn't update  network (with MTU 9000) "
                                   "when Network resides on non-running VM "
                                   "and unplugged NIC of running VM")

        logger.info("Wait till the Host is updated with the change")
        sample1 = TimeoutingSampler(
            timeout=config.SAMPLER_TIMEOUT,
            sleep=1,
            func=checkHostNicParameters,
            host=config.HOSTS[0],
            nic=config.HOST_NICS[1],
            **mtu_dict1
        )
        if not sample1.waitForFuncStatus(result=True):
            raise NetworkException("Couldn't get correct MTU on host")

        logger.info("Check that the change is reflected to Host")
        logger.info("Checking logical layer of bridged network %s on host %s",
                    config.NETWORKS[0], config.HOSTS[0])

        self.assertTrue(checkMTU(host=config.HOSTS[0], user=config.HOSTS_USER,
                                 password=config.HOSTS_PW, mtu=config.MTU[0],
                                 physical_layer=False,
                                 network=config.NETWORKS[0],
                                 nic=config.HOST_NICS[1]))

        logger.info("Checking physical layer of bridged network %s on host "
                    "%s", config.NETWORKS[0], config.HOSTS[0])
        self.assertTrue(checkMTU(host=config.HOSTS[0], user=config.HOSTS_USER,
                                 password=config.HOSTS_PW, mtu=config.MTU[0],
                                 nic=config.HOST_NICS[1]))

        logger.info("Update network with VLAN %s", config.VLAN_ID[0])
        if not updateNetwork(True, network=config.NETWORKS[0],
                             data_center=config.DC_NAME[0],
                             vlan_id=config.VLAN_ID[0]):
            raise NetworkException("Couldn't update network (to be tagged "
                                   "with VLAN %s) when Network resides on "
                                   "non-running VM and/or unplugged NIC of"
                                   "running VM" % config.VLAN_ID[0])

        logger.info("Wait till the Host is updated with the change")
        sample1 = TimeoutingSampler(
            timeout=config.SAMPLER_TIMEOUT,
            sleep=1,
            func=checkHostNicParameters,
            host=config.HOSTS[0],
            nic=config.HOST_NICS[1],
            **vlan_dict1
        )
        if not sample1.waitForFuncStatus(result=True):
            raise NetworkException("Couldn't get correct VLAN interface on "
                                   "host")

        logger.info("Check that the change is reflected to Host")
        if not checkVlanNet(host=config.HOSTS[0], user=config.HOSTS_USER,
                            password=config.HOSTS_PW,
                            interface=config.HOST_NICS[1],
                            vlan=config.VLAN_ID[0]):
            raise NetworkException("Host %s was not updated with correct "
                                   "VLAN %s" % (config.HOSTS[0],
                                                config.VLAN_ID[0]))

        logger.info("Negative: Update network %s to be non-VM network",
                    config.NETWORKS[0])
        if not updateNetwork(False, network=config.NETWORKS[0],
                             data_center=config.DC_NAME[0],
                             usages=""):
            raise NetworkException("Could update network to be non-VM net "
                                   "though it's attached to VM")

        logger.info("Check that the change is reflected to Host")
        if not isVmHostNetwork(host=config.HOSTS[0], user=config.HOSTS_USER,
                               password=config.HOSTS_PW,
                               net_name=config.NETWORKS[0]):
            raise NetworkException("Network on host %s was not updated to be "
                                   "non-VM network" % config.HOSTS[0])

    @classmethod
    def teardown_class(cls):
        """
        Remove network from the setup.
        """
        mtu_dict1 = {"mtu": config.MTU[-1]}

        logger.info("Update MTU network with MTU %s", config.MTU[-1])
        if not updateNetwork(True, network=config.NETWORKS[0],
                             data_center=config.DC_NAME[0],
                             mtu=config.MTU[-1]):
            raise NetworkException("Couldn't update  network with MTU %s " %
                                   config.MTU[-1])

        logger.info("Wait till the Host is updated with the change")
        sample1 = TimeoutingSampler(
            timeout=config.SAMPLER_TIMEOUT,
            sleep=1,
            func=checkHostNicParameters,
            host=config.HOSTS[0],
            nic=config.HOST_NICS[1],
            **mtu_dict1
        )
        if not sample1.waitForFuncStatus(result=True):
            raise NetworkException("Couldn't update with correct MTU on host")

        logger.info("Remove network from VMs")
        for i in range(2):
            if not removeNic(True, config.VM_NAME[i], "nic2"):
                raise NetworkException("Cannot remove NIC from VM %s " %
                                       config.VM_NAME[i])

        logger.info("Remove network from setup")
        if not removeNetFromSetup(host=config.HOSTS[0],
                                  auto_nics=[config.HOST_NICS[0]],
                                  network=[config.NETWORKS[0]]):
            raise NetworkException("Cannot remove network from setup")


@attr(tier=1)
class MultiHostCase06(TestCase):
    """
    Update network when template is using it:
    1) Negative: Try to update network from VM to non-VM
    2) Positive: Try to change MTU on net when template is using it
    3) Positive: Try to change VLAN on net when template is using it
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Create and attach network on DC, Cluster,Host and Template
        """

        dict_dc1 = {config.NETWORKS[0]: {"nic": config.HOST_NICS[1],
                                         "required": "false"}}

        logger.info("Attach network to DC/Cluster/Host")
        if not createAndAttachNetworkSN(data_center=config.DC_NAME[0],
                                        cluster=config.CLUSTER_NAME[0],
                                        host=config.HOSTS[0],
                                        network_dict=dict_dc1,
                                        auto_nics=[config.HOST_NICS[0]]):
            raise NetworkException("Cannot create and attach network")

        logger.info("Attach NIC to the Template")
        if not addTemplateNic(True, config.TEMPLATE_NAME[0], name="nic2",
                              data_center=config.DC_NAME[0],
                              network=config.NETWORKS[0]):
            raise NetworkException("Cannot add NIC to Template")

    @istest
    @tcms(12030, 331910)
    def update_net_on_template(self):
        """
        1) Negative: Try to update network from VM to non-VM
        2) Positive: Try to change MTU on net when template is using it
        3) Positive: Try to change VLAN on net when template is using it
        """
        mtu_dict1 = {"mtu": config.MTU[0]}
        vlan_dict1 = {"vlan_id": config.VLAN_ID[0]}

        logger.info("Negative: Try to update network from VM to non-VM "
                    "when network resides on Template")
        if not updateNetwork(False, network=config.NETWORKS[0],
                             data_center=config.DC_NAME[0],
                             usages=""):
            raise NetworkException("Could update network to be non-VM net "
                                   "though it's attached to Template")

        logger.info("Update network with MTU %s", config.MTU[0])
        if not updateNetwork(True, network=config.NETWORKS[0],
                             data_center=config.DC_NAME[0],
                             mtu=config.MTU[0]):
            raise NetworkException("Couldn't update  network with MTU %s "
                                   "when network resides on Template" %
                                   config.MTU[0])

        logger.info("Wait till the Host is updated with the change")
        sample1 = TimeoutingSampler(
            timeout=config.SAMPLER_TIMEOUT,
            sleep=1,
            func=checkHostNicParameters,
            host=config.HOSTS[0],
            nic=config.HOST_NICS[1],
            **mtu_dict1
        )
        if not sample1.waitForFuncStatus(result=True):
            raise NetworkException("Couldn't get correct MTU on host")

        logger.info("Check that the change is reflected to Host")
        logger.info("Checking logical layer of bridged network %s on host %s"
                    % (config.NETWORKS[0], config.HOSTS[0]))

        self.assertTrue(checkMTU(host=config.HOSTS[0], user=config.HOSTS_USER,
                                 password=config.HOSTS_PW, mtu=config.MTU[0],
                                 physical_layer=False,
                                 network=config.NETWORKS[0],
                                 nic=config.HOST_NICS[1]))

        logger.info("Checking physical layer of bridged network %s on host "
                    "%s", config.NETWORKS[0], config.HOSTS[0])
        self.assertTrue(checkMTU(host=config.HOSTS[0], user=config.HOSTS_USER,
                                 password=config.HOSTS_PW, mtu=config.MTU[0],
                                 nic=config.HOST_NICS[1]))

        logger.info("Update network with VLAN %s", config.VLAN_ID[0])
        if not updateNetwork(True, network=config.NETWORKS[0],
                             data_center=config.DC_NAME[0],
                             vlan_id=config.VLAN_ID[0]):
            raise NetworkException("Couldn't update network to be tagged  "
                                   "with VLAN %s when network resides on "
                                   "Template" % config.VLAN_ID[0])

        logger.info("Wait till the Host is updated with the change")
        sample1 = TimeoutingSampler(
            timeout=config.SAMPLER_TIMEOUT,
            sleep=1,
            func=checkHostNicParameters,
            host=config.HOSTS[0],
            nic=config.HOST_NICS[1],
            **vlan_dict1
        )
        if not sample1.waitForFuncStatus(result=True):
            raise NetworkException("Couldn't get correct VLAN interface on "
                                   "host")

        logger.info("Check that the change is reflected to Host")
        if not checkVlanNet(host=config.HOSTS[0], user=config.HOSTS_USER,
                            password=config.HOSTS_PW,
                            interface=config.HOST_NICS[1],
                            vlan=config.VLAN_ID[0]):
            raise NetworkException("Host %s was not updated with correct "
                                   "VLAN %s" % (config.HOSTS[0],
                                                config.VLAN_ID[0]))

    @classmethod
    def teardown_class(cls):
        """
        Remove network from the setup.
        """
        mtu_dict1 = {"mtu": config.MTU[-1]}

        logger.info("Update MTU network with MTU %s", config.MTU[-1])
        if not updateNetwork(True, network=config.NETWORKS[0],
                             data_center=config.DC_NAME[0],
                             mtu=config.MTU[-1]):
            raise NetworkException("Couldn't update  network with MTU %s " %
                                   config.MTU[-1])

        logger.info("Wait till the Host is updated with the change")
        sample1 = TimeoutingSampler(
            timeout=config.SAMPLER_TIMEOUT,
            sleep=1,
            func=checkHostNicParameters,
            host=config.HOSTS[0],
            nic=config.HOST_NICS[1],
            **mtu_dict1
        )
        if not sample1.waitForFuncStatus(result=True):
            raise NetworkException("Couldn't update with correct MTU on host")

        logger.info("Remove NIC from Template")
        if not removeTemplateNic(positive=True,
                                 template=config.TEMPLATE_NAME[0],
                                 nic=config.NIC_NAME[1]):
            raise NetworkException("NIC %s wasn't removed from Template %s" %
                                   (config.NIC_NAME[1],
                                    config.TEMPLATE_NAME[0]))

        logger.info("Remove network from setup")
        if not removeNetFromSetup(host=config.HOSTS[0],
                                  auto_nics=[config.HOST_NICS[0]],
                                  network=[config.NETWORKS[0]]):
            raise NetworkException("Cannot remove network from setup")


@attr(tier=1)
class MultiHostCase07(TestCase):
    """
    Update untagged network with VLAN and MTU when several hosts reside under
    the same DC/Cluster
    Make sure all the changes exist on both Hosts
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Create network on DC/Cluster/Hosts
        """

        local_dict = {config.VLAN_NETWORKS[0]: {"nic": config.HOST_NICS[1],
                                                "required": "false"}}

        logger.info("Attach network to DC/Cluster and 2 Hosts")
        if not createAndAttachNetworkSN(data_center=config.DC_NAME[0],
                                        cluster=config.CLUSTER_NAME[0],
                                        host=config.HOSTS,
                                        network_dict=local_dict,
                                        auto_nics=[config.HOST_NICS[0]]):
            raise NetworkException("Cannot create and attach network")

    @istest
    @tcms(12030, 331897)
    def update_with_vlan_mtu(self):
        """
        1) Update network with VLAN 162
        3) Update network with MTU 9000
        4) Check that the both Hosts were updated with VLAN 162 and MTU 9000
        """

        mtu_dict1 = {"mtu": config.MTU[0]}
        sample1 = []

        logger.info("Update network with VLAN %s and MTU %s ",
                    config.VLAN_ID[0], config.MTU[0])
        if not updateNetwork(True, network=config.VLAN_NETWORKS[0],
                             data_center=config.DC_NAME[0],
                             vlan_id=config.VLAN_ID[0], mtu=config.MTU[0]):
            raise NetworkException("Cannot update network to be tagged "
                                   "and to have MTU in one action")

        logger.info("Check that both Hosts are updated with correct MTU "
                    "value")
        for host in config.HOSTS:
            sample1.append(
                TimeoutingSampler(
                    timeout=config.SAMPLER_TIMEOUT,
                    sleep=1,
                    func=checkHostNicParameters,
                    host=host,
                    nic=config.HOST_NICS[1],
                    **mtu_dict1
                )
            )
        for i in range(2):
            if not sample1[i].waitForFuncStatus(result=True):
                raise NetworkException("Couldn't get correct MTU on host")

        logger.info("Check that the MTU change is reflected to both Hosts")
        for host in config.HOSTS:
            logger.info("Checking logical layer of bridged network %s on host"
                        "%s" % (config.VLAN_NETWORKS[0], host))

            self.assertTrue(checkMTU(host=host, user=config.HOSTS_USER,
                                     password=config.HOSTS_PW,
                                     mtu=config.MTU[0],
                                     physical_layer=False,
                                     network=config.VLAN_NETWORKS[0],
                                     nic=config.HOST_NICS[1]))

            logger.info("Checking physical layer of bridged network %s on host"
                        " %s" % (config.NETWORKS[0], host))
            self.assertTrue(checkMTU(host=host, user=config.HOSTS_USER,
                                     password=config.HOSTS_PW,
                                     mtu=config.MTU[0],
                                     nic=config.HOST_NICS[1]))

        logger.info("Check that the VLAN change is reflected to both Hosts")
        for host in config.HOSTS:
            if not checkVlanNet(host=host, user=config.HOSTS_USER,
                                password=config.HOSTS_PW,
                                interface=config.HOST_NICS[1],
                                vlan=config.VLAN_ID[0]):
                raise NetworkException("Host %s was not updated with correct "
                                       "VLAN %s" % (host, config.VLAN_ID[0]))

    @classmethod
    def teardown_class(cls):
        """
        Remove network from the setup.
        """
        mtu_dict1 = {"mtu": config.MTU[-1]}
        sample1 = []

        logger.info("Update MTU network with MTU %s", config.MTU[-1])
        if not updateNetwork(True, network=config.VLAN_NETWORKS[0],
                             data_center=config.DC_NAME[0],
                             mtu=config.MTU[-1]):
            raise NetworkException("Couldn't update  network with MTU %s " %
                                   config.MTU[-1])

        logger.info("Check correct MTU on both Hosts")
        for host in config.HOSTS:
            sample1.append(
                TimeoutingSampler(
                    timeout=config.SAMPLER_TIMEOUT,
                    sleep=1,
                    func=checkHostNicParameters,
                    host=host,
                    nic=config.HOST_NICS[1],
                    **mtu_dict1
                )
            )
        for i in range(2):
            if not sample1[i].waitForFuncStatus(result=True):
                raise NetworkException("Couldn't get correct MTU on host")

        if not removeNetFromSetup(host=config.HOSTS,
                                  auto_nics=[config.HOST_NICS[0]],
                                  network=[config.VLAN_NETWORKS[0]]):
            raise NetworkException("Cannot remove network from setup")


@attr(tier=1)
class MultiHostCase08(TestCase):
    """
    Update untagged network with VLAN and MTU when several hosts reside under
    the same DC, but under different Clusters of the same DC
    Make sure all the changes exist on both Hosts
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Move the second Host to different Cluster under the same DC
        Create network on DC/Clusters/Hosts
        """

        logger .info("Add additional Cluster %s under DC %s ",
                     config.CLUSTER_NAME[1], config.DC_NAME[0])
        if not addCluster(positive=True, name=config.CLUSTER_NAME[1],
                          cpu=config.CPU_NAME, data_center=config.DC_NAME[0],
                          version=config.COMP_VERSION):
            raise NetworkException("Cannot add Cluster %s under DC %s " %
                                   (config.CLUSTER_NAME[1], config.DC_NAME[0]))

        logger.info("Deactivate host %s, move it to other Cluster and "
                    "reactivate it", config.HOSTS[1])
        assert (deactivateHost(True, host=config.HOSTS[1]))
        if not updateHost(True, host=config.HOSTS[1],
                          cluster=config.CLUSTER_NAME[1]):
            raise NetworkException("Cannot move host to another Cluster")
        assert (activateHost(True, host=config.HOSTS[1]))

        local_dict = {config.VLAN_NETWORKS[0]: {"nic": config.HOST_NICS[1],
                                                "required": "false"}}

        logger.info("Attach network to DC/Cluster and 2 Hosts")
        if not createAndAttachNetworkSN(data_center=config.DC_NAME[0],
                                        cluster=config.CLUSTER_NAME[0],
                                        host=config.HOSTS[0],
                                        network_dict=local_dict,
                                        auto_nics=[config.HOST_NICS[0]]):
            raise NetworkException("Cannot create and attach network")
        if not createAndAttachNetworkSN(cluster=config.CLUSTER_NAME[1],
                                        host=config.HOSTS[1],
                                        network_dict=local_dict,
                                        auto_nics=[config.HOST_NICS[0]]):
            raise NetworkException("Cannot create and attach network")

    @istest
    @tcms(12030, 331903)
    def update_with_vlan_mtu(self):
        """
        1) Update network with VLAN 162
        3) Update network with MTU 9000
        4) Check that the both Hosts were updated with VLAN 162 and MTU 9000
        """

        mtu_dict1 = {"mtu": config.MTU[0]}
        sample1 = []

        logger.info("Update network with VLAN %s and MTU %s ",
                    config.VLAN_ID[0], config.MTU[0])
        if not updateNetwork(True, network=config.VLAN_NETWORKS[0],
                             data_center=config.DC_NAME[0],
                             vlan_id=config.VLAN_ID[0], mtu=config.MTU[0]):
            raise NetworkException("Cannot update network to be tagged "
                                   "and to have MTU in one action")

        logger.info("Check that both Hosts are updated with correct MTU "
                    "value")
        for host in config.HOSTS:
            sample1.append(
                TimeoutingSampler(
                    timeout=config.SAMPLER_TIMEOUT,
                    sleep=1,
                    func=checkHostNicParameters,
                    host=host,
                    nic=config.HOST_NICS[1],
                    **mtu_dict1
                )
            )
        for i in range(2):
            if not sample1[i].waitForFuncStatus(result=True):
                raise NetworkException("Couldn't get correct MTU on host")

        logger.info("Check that the MTU change is reflected to both Hosts")
        for host in config.HOSTS:
            logger.info("Checking logical layer of bridged network %s on host"
                        "%s" % (config.VLAN_NETWORKS[0], host))
            self.assertTrue(checkMTU(host=host, user=config.HOSTS_USER,
                                     password=config.HOSTS_PW,
                                     mtu=config.MTU[0],
                                     physical_layer=False,
                                     network=config.VLAN_NETWORKS[0],
                                     nic=config.HOST_NICS[1]))

            logger.info("Checking physical layer of bridged network %s on host"
                        " %s" % (config.NETWORKS[0], host))
            self.assertTrue(checkMTU(host=host, user=config.HOSTS_USER,
                                     password=config.HOSTS_PW,
                                     mtu=config.MTU[0],
                                     nic=config.HOST_NICS[1]))

        logger.info("Check that the VLAN change is reflected to both Hosts")
        for host in config.HOSTS:
            if not checkVlanNet(host=host, user=config.HOSTS_USER,
                                password=config.HOSTS_PW,
                                interface=config.HOST_NICS[1],
                                vlan=config.VLAN_ID[0]):
                raise NetworkException("Host %s was not updated with correct "
                                       "VLAN %s" % (host, config.VLAN_ID[0]))

    @classmethod
    def teardown_class(cls):
        """
        Remove network from the setup.
        """

        mtu_dict1 = {"mtu": config.MTU[-1]}
        sample1 = []

        logger.info("Update network %s with MTU %s", config.VLAN_NETWORKS[0],
                    config.MTU[-1])
        if not updateNetwork(True, network=config.VLAN_NETWORKS[0],
                             data_center=config.DC_NAME[0],
                             mtu=config.MTU[-1]):
            raise NetworkException("Couldn't update  network with MTU %s ",
                                   config.MTU[-1])

        logger.info("Check correct MTU on both Hosts")
        for host in config.HOSTS:
            sample1.append(
                TimeoutingSampler(
                    timeout=config.SAMPLER_TIMEOUT,
                    sleep=1,
                    func=checkHostNicParameters,
                    host=host,
                    nic=config.HOST_NICS[1],
                    **mtu_dict1
                )
            )
        for i in range(2):
            if not sample1[i].waitForFuncStatus(result=True):
                raise NetworkException("Couldn't get correct MTU on host")

        logger.info("Remove network %s from setup", config.VLAN_NETWORKS[0])
        if not removeNetFromSetup(host=config.HOSTS,
                                  auto_nics=[config.HOST_NICS[0]],
                                  network=[config.VLAN_NETWORKS[0]]):
            raise NetworkException("Cannot remove network from setup")

        logger.info("Deactivate host, move it to original Cluster and "
                    "reactivate it")
        assert (deactivateHost(True, host=config.HOSTS[1]))
        if not updateHost(True, host=config.HOSTS[1],
                          cluster=config.CLUSTER_NAME[0]):
            raise NetworkException("Cannot move host to another Cluster")
        assert (activateHost(True, host=config.HOSTS[1]))

        logger.info("Remove cluster %s from setup", config.CLUSTER_NAME[1])
        if not removeCluster(True, config.CLUSTER_NAME[1]):
            raise NetworkException("Cannot remove Cluster %s from setup" %
                                   config.CLUSTER_NAME[1])


@attr(tier=1)
class MultiHostCase09(TestCase):
    """
    Update untagged network with VLAN when that network is attached to
    the Host bond
    Update tagged network with another VLAN when that network is attached to
    the Host bond
    Update tagged network to be untagged when that network is attached to
    the Host bond
    """
    __test__ = len(config.HOST_NICS) > 3

    @classmethod
    def setup_class(cls):
        """
        Create untagged network on DC/Cluster/Host
        """
        local_dict = {config.VLAN_NETWORKS[0]: {"nic": config.BOND[0],
                                                "slaves":
                                                [config.HOST_NICS[2],
                                                 config.HOST_NICS[3]],
                                                "required": "false"}}

        logger.info("Attach network to DC/Cluster and bond on Host")
        if not createAndAttachNetworkSN(data_center=config.DC_NAME[0],
                                        cluster=config.CLUSTER_NAME[0],
                                        host=config.HOSTS[0],
                                        network_dict=local_dict,
                                        auto_nics=[config.HOST_NICS[0]]):
            raise NetworkException("Cannot create and attach network")

    @istest
    @tcms(12030, 355193)
    def update_with_vlan(self):
        """
        There is a bz for updating network to be tagged - 1081489

        1) Update network with VLAN 162
        2) Check that the Host was updated with VLAN 162
        3) Update network with VLAN 163
        4) Check that the Host was updated with VLAN 163
        5) Update network with VLAN 163 to be untagged
        6) Check that the Host was updated as well
        """
        vlan_dict1 = {"vlan_id": config.VLAN_ID[0]}
        vlan_dict2 = {"vlan_id": config.VLAN_ID[1]}

        logger.info("Update network with VLAN %s", config.VLAN_ID[0])
        if not updateNetwork(True, network=config.VLAN_NETWORKS[0],
                             data_center=config.DC_NAME[0],
                             vlan_id=config.VLAN_ID[0]):
            raise NetworkException("Cannot update network to be tagged with "
                                   "VLAN %s" % config.VLAN_ID[0])

        logger.info("Wait till the Host is updated with the change")
        sample1 = TimeoutingSampler(
            timeout=config.SAMPLER_TIMEOUT,
            sleep=1,
            func=checkHostNicParameters,
            host=config.HOSTS[0],
            nic=config.BOND[0],
            **vlan_dict1
        )
        if not sample1.waitForFuncStatus(result=True):
            raise NetworkException("Couldn't get correct vlan interface on "
                                   "host")

        logger.info("Check that the change is reflected to Host")
        if not checkVlanNet(host=config.HOSTS[0], user=config.HOSTS_USER,
                            password=config.HOSTS_PW,
                            interface=config.BOND[0],
                            vlan=config.VLAN_ID[0]):
            raise NetworkException("Host %s was not updated with correct "
                                   "VLAN %s" % (config.HOSTS[0],
                                                config.VLAN_ID[0]))

        logger.info("Update network with VLAN %s", config.VLAN_ID[1])
        if not updateNetwork(True, network=config.VLAN_NETWORKS[0],
                             data_center=config.DC_NAME[0],
                             vlan_id=config.VLAN_ID[1]):
            raise NetworkException("Cannot update network to be tagged with "
                                   "VLAN %s" % config.VLAN_ID[1])

        logger.info("Wait till the Host is updated with the change")
        sample2 = TimeoutingSampler(
            timeout=config.SAMPLER_TIMEOUT,
            sleep=1,
            func=checkHostNicParameters,
            host=config.HOSTS[0],
            nic=config.BOND[0],
            **vlan_dict2
        )
        if not sample2.waitForFuncStatus(result=True):
            raise NetworkException("Couldn't get correct vlan interface on "
                                   "host")

        logger.info("Check that the change is reflected to Host")
        if not checkVlanNet(host=config.HOSTS[0], user=config.HOSTS_USER,
                            password=config.HOSTS_PW,
                            interface=config.BOND[0],
                            vlan=config.VLAN_ID[1]):
            raise NetworkException("Host %s was not updated with correct "
                                   "VLAN %s" % (config.HOSTS[0],
                                                config.VLAN_ID[1]))

        logger.info("Update network to be untagged")
        if not updateNetwork(True, network=config.VLAN_NETWORKS[0],
                             data_center=config.DC_NAME[0],
                             vlan_id=None):
            raise NetworkException("Cannot update network to be untagged")

        logger.info("Wait till the Host is updated with the change")
        if not sample2.waitForFuncStatus(result=False):
            raise NetworkException("Could get vlan interface on host but "
                                   "shouldn't")

        logger.info("Check that the change is reflected to Host")
        if checkVlanNet(host=config.HOSTS[0], user=config.HOSTS_USER,
                        password=config.HOSTS_PW,
                        interface=config.BOND[0],
                        vlan=config.VLAN_ID[1]):
            raise NetworkException("Network on Host %s was not updated to be "
                                   "untagged" % config.HOSTS[0])

    @classmethod
    def teardown_class(cls):
        """
        Remove network from the setup.
        """
        logger.info("Remove networks from setup")
        if not removeNetFromSetup(host=config.HOSTS[0],
                                  auto_nics=[config.HOST_NICS[0]],
                                  network=[config.VLAN_NETWORKS[0]]):
            raise NetworkException("Cannot remove network from setup")


@attr(tier=1)
class MultiHostCase10(TestCase):
    """
    Update network with the default MTU to the new MTU when that network
    is attached to the Host bond
    Update network with another MTU value when that network is attached to
    the Host bond
    """
    __test__ = len(config.HOST_NICS) > 3

    @classmethod
    def setup_class(cls):
        """
        Create and attach network on DC, Cluster and the host
        """
        local_dict = {config.NETWORKS[0]: {"nic": config.BOND[0],
                                           "slaves": [config.HOST_NICS[2],
                                                      config.HOST_NICS[3]],
                                           "required": "false"}}

        logger.info("Attach network to DC/Cluster/Host")
        if not createAndAttachNetworkSN(data_center=config.DC_NAME[0],
                                        cluster=config.CLUSTER_NAME[0],
                                        host=config.HOSTS[0],
                                        network_dict=local_dict,
                                        auto_nics=[config.HOST_NICS[0]]):
            raise NetworkException("Cannot create and attach network")

    @istest
    @tcms(12030, 355194)
    def update_with_mtu(self):
        """
        1) Update network with MTU 9000
        2) Check that the Host was updated with MTU 9000
        3) Update network with MTU 1500
        4) Check that the Host was updated with MTU 1500
        """
        mtu_dict1 = {"mtu": config.MTU[0]}
        mtu_dict2 = {"mtu": config.MTU[-1]}

        logger.info("Update network with MTU %s", config.MTU[0])
        if not updateNetwork(True, network=config.NETWORKS[0],
                             data_center=config.DC_NAME[0],
                             mtu=config.MTU[0]):
            raise NetworkException("Cannot update  network with  MTU %s" %
                                   config.MTU[0])

        logger.info("Wait till the Host is updated with the change")
        sample1 = TimeoutingSampler(
            timeout=config.SAMPLER_TIMEOUT,
            sleep=1,
            func=checkHostNicParameters,
            host=config.HOSTS[0],
            nic=config.BOND[0],
            **mtu_dict1
        )
        if not sample1.waitForFuncStatus(result=True):
            raise NetworkException("Couldn't get correct MTU on host")

        logger.info("Check that the change is reflected to Host")
        logger.info("Checking logical layer of bridged network %s on host %s"
                    % (config.NETWORKS[0], config.HOSTS[0]))
        self.assertTrue(checkMTU(host=config.HOSTS[0], user=config.HOSTS_USER,
                                 password=config.HOSTS_PW, mtu=config.MTU[0],
                                 physical_layer=False,
                                 network=config.NETWORKS[0],
                                 nic=config.BOND[0]))

        logger.info("Checking physical layer of bridged network %s on host %s"
                    % (config.NETWORKS[0], config.HOSTS[0]))
        self.assertTrue(checkMTU(host=config.HOSTS[0], user=config.HOSTS_USER,
                                 password=config.HOSTS_PW, mtu=config.MTU[0],
                                 nic=config.BOND[0]))

        logger.info("Update MTU network with MTU %s", config.MTU[-1])
        if not updateNetwork(True, network=config.NETWORKS[0],
                             data_center=config.DC_NAME[0],
                             mtu=config.MTU[-1]):
            raise NetworkException("Cannot update network with MTU %s" %
                                   config.MTU[-1])

        logger.info("Wait till the Host is updated with the change")
        sample2 = TimeoutingSampler(
            timeout=config.SAMPLER_TIMEOUT,
            sleep=1,
            func=checkHostNicParameters,
            host=config.HOSTS[0],
            nic=config.BOND[0],
            **mtu_dict2
        )
        if not sample2.waitForFuncStatus(result=True):
            raise NetworkException("Couldn't get correct MTU on host")

        logger.info("Check that the change is reflected to Host")
        logger.info("Checking logical layer of bridged network %s on host %s"
                    % (config.NETWORKS[0], config.HOSTS[0]))
        self.assertTrue(checkMTU(host=config.HOSTS[0], user=config.HOSTS_USER,
                                 password=config.HOSTS_PW, mtu=config.MTU[-1],
                                 physical_layer=False,
                                 network=config.NETWORKS[0],
                                 nic=config.BOND[0]))

        logger.info("Checking physical layer of bridged network %s on host %s"
                    % (config.NETWORKS[0], config.HOSTS[0]))
        self.assertTrue(checkMTU(host=config.HOSTS[0], user=config.HOSTS_USER,
                                 password=config.HOSTS_PW, mtu=config.MTU[-1],
                                 nic=config.BOND[0]))

    @classmethod
    def teardown_class(cls):
        """
        Remove network from the setup.
        """
        logger.info("Remove network from setup")
        if not removeNetFromSetup(host=config.HOSTS[0],
                                  auto_nics=[config.HOST_NICS[0]],
                                  network=[config.NETWORKS[0]]):
            raise NetworkException("Cannot remove network from setup")


@attr(tier=1)
class MultiHostCase11(TestCase):
    """
    Update VM network to be non-VM network when that network is attached to
    the Host bond
    Update non-VM network to be VM network when that network is attached to
    the Host bond
    """
    __test__ = len(config.HOST_NICS) > 3

    @classmethod
    def setup_class(cls):
        """
        Create and attach network on DC, Cluster and the host
        """

        local_dict = {config.NETWORKS[0]: {"nic": config.BOND[0],
                                           "slaves": [config.HOST_NICS[2],
                                                      config.HOST_NICS[3]],
                                           "required": "false"}}

        logger.info("Attach network to DC/Cluster/Host")
        if not createAndAttachNetworkSN(data_center=config.DC_NAME[0],
                                        cluster=config.CLUSTER_NAME[0],
                                        host=config.HOSTS[0],
                                        network_dict=local_dict,
                                        auto_nics=[config.HOST_NICS[0]]):
            raise NetworkException("Cannot create and attach network")

    @istest
    @tcms(12030, 355294)
    def update_with_non_vm_nonvm(self):
        """
        Fails due to existing bug - 1082275
        1) Update network to be non-VM network
        2) Check that the Host was updated accordingly
        3) Update network to be VM network
        4) Check that the Host was updated accordingly
        """
        bridge_dict1 = {"bridge": False}
        bridge_dict2 = {"bridge": True}

        logger.info("Update network %s to be non-VM network",
                    config.NETWORKS[0])
        if not updateNetwork(True, network=config.NETWORKS[0],
                             data_center=config.DC_NAME[0], usages=""):
            raise NetworkException("Cannot update network to be non-VM net")

        logger.info("Wait till the Host is updated with the change")
        sample1 = TimeoutingSampler(
            timeout=config.SAMPLER_TIMEOUT,
            sleep=1,
            func=checkHostNicParameters,
            host=config.HOSTS[0],
            nic=config.BOND[0],
            **bridge_dict1
        )
        if not sample1.waitForFuncStatus(result=True):
            raise NetworkException("Network is VM network and should be "
                                   "Non-VM")

        logger.info("Check that the change is reflected to Host")
        if isVmHostNetwork(host=config.HOSTS[0], user=config.HOSTS_USER,
                           password=config.HOSTS_PW,
                           net_name=config.NETWORKS[0], conn_timeout=45):
            raise NetworkException("Network on host %s was not updated to be "
                                   "non-VM network" % config.HOSTS[0])

        logger.info("Update network %s to be VM network", config.NETWORKS[0])
        if not updateNetwork(True, network=config.NETWORKS[0],
                             data_center=config.DC_NAME[0],
                             usages="vm"):
            raise NetworkException("Cannot update network to be VM net")

        logger.info("Wait till the Host is updated with the change")
        sample2 = TimeoutingSampler(
            timeout=config.SAMPLER_TIMEOUT,
            sleep=1,
            func=checkHostNicParameters,
            host=config.HOSTS[0],
            nic=config.BOND[0],
            **bridge_dict2
        )
        if not sample2.waitForFuncStatus(result=True):
            raise NetworkException("Network is not a VM network but should be")

        logger.info("Check that the change is reflected to Host")
        if not isVmHostNetwork(host=config.HOSTS[0], user=config.HOSTS_USER,
                               password=config.HOSTS_PW,
                               net_name=config.NETWORKS[0]):
            raise NetworkException("Network on host %s was not updated to be "
                                   "VM network" % config.HOSTS[0])

    @classmethod
    def teardown_class(cls):
        """
        Remove network from the setup.
        """
        logger.info("Remove network from setup")
        if not removeNetFromSetup(host=config.HOSTS[0],
                                  auto_nics=[config.HOST_NICS[0]],
                                  network=[config.NETWORKS[0]]):
            raise NetworkException("Cannot remove network from setup")


@attr(tier=1)
class MultiHostCase12(TestCase):
    """
    1)Check that for unsupported DC version multiHost feature is not
    working
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        1) Create a new DC with 3.0 version
        2) Create a Cluster with 3.1 version
        3) Move the Host from the original DC to the newly created DC and
        Cluster
        4) Create a VM network on DC/Cluster and Host
        """

        logger.info("Create new DC with version 3.0 in the setup ")
        if not addDataCenter(positive=True, name=config.UNCOMP_DC_NAME,
                             storage_type=config.STORAGE_TYPE,
                             version=config.VERSION[0], local=False):
            raise NetworkException("Couldn't add a new DC with %s version "
                                   "to the setup" % config.VERSION[0])

        logger.info("Create new Cluster with version %s in the setup ",
                    config.VERSION[1])
        if not addCluster(positive=True, name=config.UNCOMP_CL_NAME[1],
                          cpu=config.CPU_NAME, version=config.VERSION[1],
                          data_center=config.UNCOMP_DC_NAME):
            raise NetworkException("Couldn't add a new Cluster with %s "
                                   "version to the setup" % config.VERSION[1])

        logger.info("Deactivate host, move it to the new DC %s and "
                    "reactivate it", config.UNCOMP_DC_NAME)
        assert (deactivateHost(True, host=config.HOSTS[0]))
        if not updateHost(True, host=config.HOSTS[0],
                          cluster=config.UNCOMP_CL_NAME[1]):
            raise NetworkException("Cannot move host to another DC/Cluster")
        assert (activateHost(True, host=config.HOSTS[0]))

        local_dict = {config.NETWORKS[0]: {"nic": config.HOST_NICS[1],
                                           "required": "false"}}
        logger.info("Attach network %s to DC and Cluster for Cluster "
                    "version %s", config.NETWORKS[0], config.VERSION[1])
        if not createAndAttachNetworkSN(data_center=config.UNCOMP_DC_NAME,
                                        cluster=config.UNCOMP_CL_NAME[1],
                                        network_dict=local_dict):
            raise NetworkException("Cannot create and attach network %s" %
                                   config.NETWORKS[0])

        logger.info("Adding network %s to NIC %s", config.NETWORKS[0],
                    config.HOST_NICS[1])
        if not attachHostNic(True, config.HOSTS[0], config.HOST_NICS[1],
                             config.NETWORKS[0]):
            raise NetworkException("Cannot add network %s to Host NIC %s" %
                                   (config.NETWORKS[0], config.HOST_NICS[1]))

    @tcms(12030, 331907)
    def test_move_host_unsupported_dc(self):
        """
        1) Update the network with VLAN
        2) Make sure the change for the logical network is not projected to
        the Host
        """

        logger.info("Update network with VLAN %s", config.VLAN_ID[1])
        if not updateNetwork(True, network=config.NETWORKS[0],
                             data_center=config.UNCOMP_DC_NAME,
                             vlan_id=config.VLAN_ID[1]):
            raise NetworkException("Cannot update network to be tagged with "
                                   "VLAN %s" % config.VLAN_ID[1])

        logger.info("Check that the change is not reflected to Host")
        time.sleep(10)
        if checkVlanNet(host=config.HOSTS[0], user=config.HOSTS_USER,
                        password=config.HOSTS_PW,
                        interface=config.HOST_NICS[1],
                        vlan=config.VLAN_ID[1]):
            raise NetworkException("Host %s was updated with VLAN %s, "
                                   "but shouldn't" % (config.HOSTS[0],
                                                      config.VLAN_ID[1]))

    @classmethod
    def teardown_class(cls):
        """
        1) Remove network from setup
        2) Move the Host to the original DC and Cluster
        3)Remove created DCs and Clusters from the setup.
        """

        logger.info("Deactivate host, remove network from Host")
        assert (deactivateHost(True, host=config.HOSTS[0]))

        if not detachHostNic(True, config.HOSTS[0], config.HOST_NICS[1],
                             config.NETWORKS[0]):
            raise NetworkException("Cannot remove network %s from Host" %
                                   config.NETWORKS[0])

        logger.info("move Host back to the original Cluster %s "
                    "and reactivate it", config.CLUSTER_NAME[0])
        if not updateHost(True, host=config.HOSTS[0],
                          cluster=config.CLUSTER_NAME[0]):
            raise NetworkException("Cannot move host to the original DC")

        assert (activateHost(True, host=config.HOSTS[0]))

        logger.info("Removing the DC %s with 3.0 version",
                    config.UNCOMP_DC_NAME)
        if not removeDataCenter(positive=True,
                                datacenter=config.UNCOMP_DC_NAME):
            raise NetworkException("Failed to remove datacenter %s " %
                                   config.UNCOMP_DC_NAME)

        logger.info("Removing the Cluster with %s version", config.VERSION[1])
        if not removeCluster(positive=True,
                             cluster=config.UNCOMP_CL_NAME[1]):
            raise NetworkException("Failed to remove cluster with %s version"
                                   % config.VERSION[1])


@attr(tier=1)
class MultiHostCase13(TestCase):
    """
    1)Check that for unsupported Cluster version multiHost feature is not
    working
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        1) Create a new DC with 3.0 version
        2) Create a Cluster with 3.0 version
        3) Move the Host from the original DC to the newly created DC and
        Cluster 3.0
        4) Create a VM VLAN network on DC/Cluster and Host
        """

        logger.info("Create new DC with version 3.0 in the setup ")
        if not addDataCenter(positive=True, name=config.UNCOMP_DC_NAME,
                             storage_type=config.STORAGE_TYPE,
                             version=config.VERSION[0], local=False):
            raise NetworkException("Couldn't add a new DC with %s version "
                                   "to the setup" % config.VERSION[0])

        logger.info("Create new Cluster with version %s in the setup ",
                    config.VERSION[0])
        if not addCluster(positive=True, name=config.UNCOMP_CL_NAME[0],
                          cpu=config.CPU_NAME, version=config.VERSION[0],
                          data_center=config.UNCOMP_DC_NAME):
            raise NetworkException("Couldn't add a new Cluster with %s "
                                   "version to the setup" % config.VERSION[0])

        logger.info("Deactivate host, move it to the new DC %s and "
                    "reactivate it", config.UNCOMP_DC_NAME)
        assert (deactivateHost(True, host=config.HOSTS[0]))
        if not updateHost(True, host=config.HOSTS[0],
                          cluster=config.UNCOMP_CL_NAME[0]):
            raise NetworkException("Cannot move host to another DC/Cluster")
        assert (activateHost(True, host=config.HOSTS[0]))

        local_dict = {config.VLAN_NETWORKS[0]: {"nic": config.HOST_NICS[1],
                                                "vlan_id": config.VLAN_ID[0],
                                                "required": "false"}}
        logger.info("Attach network %s to DC and Cluster for Cluster "
                    "version %s", config.VLAN_NETWORKS[0], config.VERSION[0])
        if not createAndAttachNetworkSN(data_center=config.UNCOMP_DC_NAME,
                                        cluster=config.UNCOMP_CL_NAME[0],
                                        network_dict=local_dict):
            raise NetworkException("Cannot create and attach network %s" %
                                   config.VLAN_NETWORKS[0])

        logger.info("Adding network %s to NIC %s", config.VLAN_NETWORKS[0],
                    config.HOST_NICS[1])
        if not attachHostNic(True, config.HOSTS[0], config.HOST_NICS[1],
                             config.VLAN_NETWORKS[0]):
            raise NetworkException("Cannot add network %s to Host NIC %s" %
                                   (config.VLAN_NETWORKS[0],
                                    config.HOST_NICS[1]))

    @tcms(12030, 331907)
    def test_move_host_unsupported_cl(self):
        """
        1) Update the network with another VLAN
        2) Make sure the change for the logical network is not projected to
        the Host
        """

        logger.info("Update network with VLAN %s", config.VLAN_ID[1])
        if not updateNetwork(True, network=config.VLAN_NETWORKS[0],
                             data_center=config.UNCOMP_DC_NAME,
                             vlan_id=config.VLAN_ID[1]):
            raise NetworkException("Cannot update network to be tagged with "
                                   "VLAN %s" % config.VLAN_ID[1])

        logger.info("Check that the change is not reflected to Host")
        time.sleep(10)
        if checkVlanNet(host=config.HOSTS[0], user=config.HOSTS_USER,
                        password=config.HOSTS_PW,
                        interface=config.HOST_NICS[1],
                        vlan=config.VLAN_ID[1]):
            raise NetworkException("Host %s was updated with VLAN %s, "
                                   "but shouldn't"
                                   % (config.HOSTS[0], config.VLAN_ID[1]))

    @classmethod
    def teardown_class(cls):
        """
        1) Remove network from setup
        2) Move the Host to the original DC and Cluster
        3)Remove created DCs and Clusters from the setup.
        """

        logger.info("Deactivate host, remove network from Host")
        assert (deactivateHost(True, host=config.HOSTS[0]))
        if not detachHostNic(True, config.HOSTS[0],
                             ".".join([config.HOST_NICS[1],
                                       config.VLAN_ID[0]]),
                             config.VLAN_NETWORKS[0]):
            raise NetworkException("Cannot remove network from Host")

        logger.info("move Host back to the original Cluster %s "
                    "and reactivate it", config.CLUSTER_NAME[0])
        if not updateHost(True, host=config.HOSTS[0],
                          cluster=config.CLUSTER_NAME[0]):
            raise NetworkException("Cannot move host to the original DC")

        assert (activateHost(True, host=config.HOSTS[0]))

        logger.info("Removing the DC %s with 3.0 version",
                    config.UNCOMP_DC_NAME)
        if not removeDataCenter(positive=True,
                                datacenter=config.UNCOMP_DC_NAME):
            raise NetworkException("Failed to remove datacenter %s " %
                                   config.UNCOMP_DC_NAME)

        logger.info("Removing the Cluster with %s version", config.VERSION[0])
        if not removeCluster(positive=True,
                             cluster=config.UNCOMP_CL_NAME[0]):
            raise NetworkException("Failed to remove cluster with %s version"
                                   % config.VERSION[0])
