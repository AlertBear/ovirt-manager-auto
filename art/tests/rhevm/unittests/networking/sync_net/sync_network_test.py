'''
Testing Sync Network feature.
2 DCs, 2 Clusters, 1 Host will be created for testing.
Sync Network will be tested for untagged, tagged, bond scenarios.
It will cover scenarios for VM/non-VM networks.
'''

from nose.tools import istest
from art.unittest_lib import attr
from art.unittest_lib import NetworkTest as TestCase
import logging
from networking import config
from art.rhevm_api.utils.test_utils import get_api
from art.test_handler.settings import opts
from art.test_handler.tools import tcms
from art.core_api.apis_utils import TimeoutingSampler
from art.test_handler.exceptions import NetworkException
from art.rhevm_api.tests_lib.high_level.networks import\
    createAndAttachNetworkSN, removeNetFromSetup, removeNetwork, \
    checkHostNicParameters
from art.rhevm_api.tests_lib.low_level.networks import updateNetwork
from art.rhevm_api.tests_lib.low_level.hosts import genSNNic, sendSNRequest, \
    deactivateHost, activateHost, updateHost

HOST_API = get_api('host', 'hosts')
VM_API = get_api('vm', 'vms')
logger = logging.getLogger(__name__)
ENUMS = opts['elements_conf']['RHEVM Enums']

########################################################################

########################################################################
#                             Test Cases                               #
########################################################################


@attr(tier=1)
class SyncCase01(TestCase):
    """
    Detach and Attach sync network
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Create untagged network on DC/Cluster/Host
        Update network with VLAN
        """
        local_dict = {config.VLAN_NETWORKS[0]: {'nic': config.HOST_NICS[1],
                                                'required': 'false'}}

        logger.info("Attach network to DC/Cluster and Host")
        if not createAndAttachNetworkSN(data_center=config.DC_NAME[0],
                                        cluster=config.CLUSTER_NAME[0],
                                        host=config.HOSTS[0],
                                        network_dict=local_dict,
                                        auto_nics=[config.HOST_NICS[0]]):
            raise NetworkException("Cannot create and attach network")

    @istest
    @tcms(6665, 205933)
    def sync_networks(self):
        """
        Remove network from host and reattach to the same NIC
        """
        vlan_dict = {"vlan_id": config.VLAN_ID[0]}

        logger.info('Update network with VLAN')
        if not updateNetwork(True, network=config.VLAN_NETWORKS[0],
                             data_center=config.DC_NAME[0],
                             vlan_id=config.VLAN_ID[0]):
            raise NetworkException("Cannot update network to be tagged")

        sample = TimeoutingSampler(timeout=60, sleep=1,
                                   func=checkHostNicParameters,
                                   host=config.HOSTS[0],
                                   nic=config.HOST_NICS[1], **vlan_dict)

        if not sample.waitForFuncStatus(result=True):
            raise NetworkException("Couldn't get correct vlan interface on "
                                   "host")

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
class SyncCase02(TestCase):
    """
    Moving host from DC to DC with different VLAN
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Create and attach network with VLAN to DC with host
        Create network without VLAN on DC without the host
        Deactivate host, move it to other DC and reactivate it
        """
        dict_dc1 = {config.VLAN_NETWORKS[0]: {'vlan_id':
                                              config.VLAN_ID[0],
                                              'nic': config.HOST_NICS[1],
                                              'required': 'false'}}
        dict_dc2 = {config.VLAN_NETWORKS[0]: {'nic': config.HOST_NICS[1],
                                              'required': 'false'}}
        logger.info("Create network without VLAN on DC without the host")
        if not createAndAttachNetworkSN(data_center=config.DC_NAME[1],
                                        cluster=config.CLUSTER_NAME[1],
                                        network_dict=dict_dc2,
                                        auto_nics=[config.HOST_NICS[0],
                                                   config.HOST_NICS[1]]):
            raise NetworkException("Cannot create and attach untagged network")
        logger.info("Create and attach network with VLAN to DC with host")
        if not createAndAttachNetworkSN(data_center=config.DC_NAME[0],
                                        cluster=config.CLUSTER_NAME[0],
                                        host=config.HOSTS[0],
                                        network_dict=dict_dc1,
                                        auto_nics=[config.HOST_NICS[0],
                                                   config.HOST_NICS[1]]):
            raise NetworkException("Cannot create and attach tagged network")

        logger.info("Deactivate host, move it to other DC and reactivate it")
        assert(deactivateHost(True, host=config.HOSTS[0]))
        if not updateHost(True, host=config.HOSTS[0],
                          cluster=config.CLUSTER_NAME[1]):
            raise NetworkException("Cannot move host to another Cluster")
        assert(activateHost(True, host=config.HOSTS[0]))

    @istest
    @tcms(6665, 185336)
    def sync_new_dcs_network(self):
        """
        Sync vlan network on new DC
        """

        logger.info("Sync VLAN network on new DC")
        logger.info("Generating network object for SetupNetwork ")
        net_obj = []
        rc, out = genSNNic(nic=config.HOST_NICS[1],
                           network=config.VLAN_NETWORKS[0],
                           override_configuration=True)
        if not rc:
            raise NetworkException("Cannot generate SNNIC object")
        net_obj.append(out['host_nic'])
        if not sendSNRequest(True, host=config.HOSTS[0], nics=net_obj,
                             auto_nics=[config.HOST_NICS[0]],
                             check_connectivity='true',
                             connectivity_timeout=60, force='false'):
            raise NetworkException("Cannot sync network on new DC")

    @classmethod
    def teardown_class(cls):
        """
        Remove networks from the setup.
        Put the host on the primary DC
        """
        logger.info("Remove networks from setup")
        if not removeNetwork(True, config.VLAN_NETWORKS[0],
                             data_center=config.DC_NAME[0]):
            raise NetworkException("Remove network from DC1 failed")
        if not removeNetFromSetup(host=config.HOSTS[0],
                                  auto_nics=[config.HOST_NICS[0]],
                                  network=[config.VLAN_NETWORKS[0]]):
            raise NetworkException("Remove network from DC2/CL2/Host failed")
        logger.info("Put the host on the DC1")
        assert(deactivateHost(True, host=config.HOSTS[0]))
        if not updateHost(True, host=config.HOSTS[0],
                          cluster=config.CLUSTER_NAME[0]):
            raise NetworkException("Cannot move host to another Cluster")
        assert(activateHost(True, host=config.HOSTS[0]))


@attr(tier=1)
class SyncCase03(TestCase):
    """
    Moving host from DC to DC with different MTU value
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Create and attach network with MTU 9000 to DC with the host
        Create network with default MTU on DC without the host
        Deactivate host, move it to other DC and reactivate it
        """
        dict_dc1 = {config.NETWORKS[0]: {'mtu': 9000,
                                         'nic': config.HOST_NICS[1],
                                         'required': 'false'}}
        dict_dc2 = {config.NETWORKS[0]: {'mtu': 5000,
                                         'nic': config.HOST_NICS[1],
                                         'required': 'false'}}
        logger.info("Attach network with MTU 9000 on DC with host")
        if not createAndAttachNetworkSN(data_center=config.DC_NAME[0],
                                        cluster=config.CLUSTER_NAME[0],
                                        host=config.HOSTS[0],
                                        network_dict=dict_dc1,
                                        auto_nics=[config.HOST_NICS[0]]):
            raise NetworkException("Cannot create and attach network")
        logger.info("Create network with MTU 5000 on DC without the host")
        if not createAndAttachNetworkSN(data_center=config.DC_NAME[1],
                                        cluster=config.CLUSTER_NAME[1],
                                        network_dict=dict_dc2,
                                        auto_nics=[config.HOST_NICS[0],
                                                   config.HOST_NICS[1]]):
            raise NetworkException("Cannot create and attach network")
        logger.info("Deactivate host, move it to other DC and reactivate it")
        assert(deactivateHost(True, host=config.HOSTS[0]))
        if not updateHost(True, host=config.HOSTS[0],
                          cluster=config.CLUSTER_NAME[1]):
            raise NetworkException("Cannot move host to another Cluster")
        assert(activateHost(True, host=config.HOSTS[0]))

    @istest
    @tcms(6665, 185337)
    def sync_new_dcs_network(self):
        """
        Sync network with correct MTU
        """
        logger.info("Sync network with correct MTU")
        logger.info("Generating network object for SetupNetwork ")
        net_obj = []
        rc, out = genSNNic(nic=config.HOST_NICS[1],
                           network=config.NETWORKS[0],
                           override_configuration=True)
        if not rc:
            raise NetworkException("Cannot generate SNNIC object")
        net_obj.append(out['host_nic'])
        if not sendSNRequest(True, host=config.HOSTS[0], nics=net_obj,
                             auto_nics=[config.HOST_NICS[0]],
                             check_connectivity='true',
                             connectivity_timeout=60, force='false'):
            raise NetworkException("Cannot sync network on new DC")

    @classmethod
    def teardown_class(cls):
        """
        Update MTU to 1500
        Sync network
        Remove networks from the setup.
        Put the host on the primary DC
        """
        mtu_dict = {"mtu": "1500"}
        logger.info("Update host with MTU 1500")
        if not updateNetwork(True, network=config.NETWORKS[0],
                             data_center=config.DC_NAME[1], mtu=1500):
            raise NetworkException("Cannot update network")

        sample = TimeoutingSampler(timeout=60, sleep=1,
                                   func=checkHostNicParameters,
                                   host=config.HOSTS[0],
                                   nic=config.HOST_NICS[1],
                                   **mtu_dict)

        if not sample.waitForFuncStatus(result=True):
            raise NetworkException("Couldn't get correct MTU on "
                                   "host")

        if not removeNetwork(True, config.NETWORKS[0],
                             data_center=config.DC_NAME[0]):
            raise NetworkException("Remove network from DC1 failed")

        if not removeNetFromSetup(host=config.HOSTS[0],
                                  auto_nics=[config.HOST_NICS[0]],
                                  network=[config.NETWORKS[0]]):
            raise NetworkException("Remove network from DC2/CL2/Host failed")

        logger.info("Put the host on the DC1")
        assert(deactivateHost(True, host=config.HOSTS[0]))
        if not updateHost(True, host=config.HOSTS[0],
                          cluster=config.CLUSTER_NAME[0]):
            raise NetworkException("Cannot move host to another Cluster")

        assert(activateHost(True, host=config.HOSTS[0]))


@attr(tier=1)
class SyncCase04(TestCase):
    """
    Moving host from DC with VM net to DC with non-VM net
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Create and attach VM network to the DC with the host
        Create non-VM network on the DC without the host
        Deactivate host, move it to other DC and reactivate it
        """
        dict_dc1 = {config.NETWORKS[0]: {'nic': config.HOST_NICS[1],
                                         'required': 'false'}}
        dict_dc2 = {config.NETWORKS[0]: {'nic': config.HOST_NICS[1],
                                         'required': 'false',
                                         'usages': ''}}
        logger.info("Attach network with VM network on DC with host")
        if not createAndAttachNetworkSN(data_center=config.DC_NAME[0],
                                        cluster=config.CLUSTER_NAME[0],
                                        host=config.HOSTS[0],
                                        network_dict=dict_dc1,
                                        auto_nics=[config.HOST_NICS[0]]):
            raise NetworkException("Cannot create and attach network")
        logger.info("Create network with non-VM network on DC2")
        if not createAndAttachNetworkSN(data_center=config.DC_NAME[1],
                                        cluster=config.CLUSTER_NAME[1],
                                        network_dict=dict_dc2,
                                        auto_nics=[config.HOST_NICS[0],
                                                   config.HOST_NICS[1]]):
            raise NetworkException("Cannot create and attach network")
        logger.info("Deactivate host, move it to other DC and reactivate it")
        assert(deactivateHost(True, host=config.HOSTS[0]))
        if not updateHost(True, host=config.HOSTS[0],
                          cluster=config.CLUSTER_NAME[1]):
            raise NetworkException("Cannot move host to another Cluster")
        assert(activateHost(True, host=config.HOSTS[0]))

    @istest
    @tcms(6665, 185370)
    def sync_new_dcs_network(self):
        """
        Sync original VM network on the new DC
        """
        logger.info("Sync VM network")
        logger.info("Generating network object for SetupNetwork ")
        net_obj = []
        rc, out = genSNNic(nic=config.HOST_NICS[1],
                           network=config.NETWORKS[0],
                           override_configuration=True)
        if not rc:
            raise NetworkException("Cannot generate SNNIC object")
        net_obj.append(out['host_nic'])
        if not sendSNRequest(True, host=config.HOSTS[0], nics=net_obj,
                             auto_nics=[config.HOST_NICS[0]],
                             check_connectivity='true',
                             connectivity_timeout=60, force='false'):
            raise NetworkException("Cannot sync network on new DC")

    @classmethod
    def teardown_class(cls):
        """
        Remove networks from the setup.
        Putting host on primary DC
        """
        logger.info("Remove networks from setup")
        if not removeNetwork(True, config.NETWORKS[0],
                             data_center=config.DC_NAME[0]):
            raise NetworkException("Remove network from DC1 failed")
        if not removeNetFromSetup(host=config.HOSTS[0],
                                  auto_nics=[config.HOST_NICS[0]],
                                  network=[config.NETWORKS[0]]):
            raise NetworkException("Remove network from DC2/CL2/Host failed")
        logger.info("Put the host on the DC1")
        assert(deactivateHost(True, host=config.HOSTS[0]))
        if not updateHost(True, host=config.HOSTS[0],
                          cluster=config.CLUSTER_NAME[0]):
            raise NetworkException("Cannot move host to another Cluster")
        assert(activateHost(True, host=config.HOSTS[0]))


@attr(tier=1)
class SyncCase05(TestCase):
    """
    Moving host from DC with non-VM net to DC with VM net
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Create and attach VM network to the DC with the host
        Create network with non-VM network on DC without the host
        Deactivate host, move it to other DC and reactivate it
        """
        dict_dc1 = {config.NETWORKS[0]: {'nic': config.HOST_NICS[1],
                                         'required': 'false',
                                         'usages': ''}}
        dict_dc2 = {config.NETWORKS[0]: {'nic': config.HOST_NICS[1],
                                         'required': 'false'}}
        logger.info("Attach network with VM network on DC with host")
        if not createAndAttachNetworkSN(data_center=config.DC_NAME[0],
                                        cluster=config.CLUSTER_NAME[0],
                                        host=config.HOSTS[0],
                                        network_dict=dict_dc1,
                                        auto_nics=[config.HOST_NICS[0]]):
            raise NetworkException("Cannot create and attach network")
        logger.info("Create network with non-VM network on DC2")
        if not createAndAttachNetworkSN(data_center=config.DC_NAME[1],
                                        cluster=config.CLUSTER_NAME[1],
                                        network_dict=dict_dc2,
                                        auto_nics=[config.HOST_NICS[0],
                                                   config.HOST_NICS[1]]):
            raise NetworkException("Cannot create and attach network")
        logger.info("Deactivate host, move it to other DC and reactivate")
        assert(deactivateHost(True, host=config.HOSTS[0]))
        if not updateHost(True, host=config.HOSTS[0],
                          cluster=config.CLUSTER_NAME[1]):
            raise NetworkException("Cannot move host to another Cluster")

    @istest
    @tcms(6665, 185374)
    def sync_new_dcs_network(self):
        """
        Sync original non-VM network on the new DC
        """
        logger.info("Sync non-VM network on the new DC")
        logger.info("Generating network object for SetupNetwork ")
        net_obj = []
        rc, out = genSNNic(nic=config.HOST_NICS[1],
                           network=config.NETWORKS[0],
                           override_configuration=True)
        if not rc:
            raise NetworkException("Cannot generate SNNIC object")
        net_obj.append(out['host_nic'])
        if not sendSNRequest(True, host=config.HOSTS[0], nics=net_obj,
                             auto_nics=[config.HOST_NICS[0]],
                             check_connectivity='true',
                             connectivity_timeout=60, force='false'):
            raise NetworkException("Cannot sync network on new DC")
        assert(activateHost(True, host=config.HOSTS[0]))

    @classmethod
    def teardown_class(cls):
        """
        Remove networks from the setup.
        Putting host on primary DC
        """
        logger.info("Remove networks from setup")
        if not removeNetwork(True, config.NETWORKS[0],
                             data_center=config.DC_NAME[0]):
            raise NetworkException("Remove network from DC1 failed")
        if not removeNetFromSetup(host=config.HOSTS[0],
                                  auto_nics=[config.HOST_NICS[0]],
                                  network=[config.NETWORKS[0]]):
            raise NetworkException("Remove network from DC2/CL2/Host failed")
        logger.info("Put the host on the DC1")
        assert(deactivateHost(True, host=config.HOSTS[0]))
        if not updateHost(True, host=config.HOSTS[0],
                          cluster=config.CLUSTER_NAME[0]):
            raise NetworkException("Cannot move host to another Cluster")
        assert(activateHost(True, host=config.HOSTS[0]))


@attr(tier=1)
class SyncCase06(TestCase):
    """
    Moving host from DC to DC with different bond configuration
    """
    __test__ = len(config.HOST_NICS) > 3

    @classmethod
    def setup_class(cls):
        """
        Create and attach VM network with VLAN over bond to DC with the host
        Create non-VM network without VLAN on DC without the host
        Deactivate host, move it to other DC and reactivate it
        """

        # Create bond0 with None network as a key
        # Bond will be created without any network
        # The VLAN_NETWORKS[0] will be added to the empty bond
        dict_dc1 = {None: {'nic': 'bond0', 'mode': 1,
                           'slaves': [config.HOST_NICS[2],
                                      config.HOST_NICS[3]]},
                    config.VLAN_NETWORKS[0]: {'nic': 'bond0',
                                              'vlan_id': config.VLAN_ID[0],
                                              'required': 'false'}}

        dict_dc2 = {None: {'nic': 'bond0', 'mode': 1,
                           'slaves': [config.HOST_NICS[2],
                                      config.HOST_NICS[3]]},
                    config.VLAN_NETWORKS[0]: {'nic': 'bond0',
                                              'required': 'false',
                                              'usages': ''}}
        logger.info("Create network without VLAN on DC without the host")
        if not createAndAttachNetworkSN(data_center=config.DC_NAME[1],
                                        cluster=config.CLUSTER_NAME[1],
                                        network_dict=dict_dc2,
                                        auto_nics=[config.HOST_NICS[0],
                                                   config.HOST_NICS[1]]):
            raise NetworkException("Cannot create and attach second network")
        logger.info("Attach network with VLAN on DC with host")
        if not createAndAttachNetworkSN(data_center=config.DC_NAME[0],
                                        cluster=config.CLUSTER_NAME[0],
                                        host=config.HOSTS[0],
                                        network_dict=dict_dc1,
                                        auto_nics=[config.HOST_NICS[0]]):
            raise NetworkException("Cannot create and attach first network")

        logger.info("Deactivate host, move it to other DC and reactivate it")
        assert(deactivateHost(True, host=config.HOSTS[0]))
        if not updateHost(True, host=config.HOSTS[0],
                          cluster=config.CLUSTER_NAME[1]):
            raise NetworkException("Cannot move host to another Cluster")
        assert(activateHost(True, host=config.HOSTS[0]))

    @istest
    @tcms(6665, 240899)
    def sync_new_dcs_network(self):
        """
        Sync VLAN network over bond on new DC
        """
        logger.info("Starting sync func for vlan network over bond")
        logger.info("Generating network object for SetupNetwork ")
        net_obj = []
        rc, out = genSNNic(nic='bond0',
                           network=config.VLAN_NETWORKS[0],
                           slaves=[config.HOST_NICS[2],
                                   config.HOST_NICS[3]],
                           mode=1, override_configuration=True)
        if not rc:
            raise NetworkException("Cannot generate SNBond object")
        net_obj.append(out['host_nic'])
        if not sendSNRequest(True, host=config.HOSTS[0], nics=net_obj,
                             auto_nics=[config.HOST_NICS[0]],
                             check_connectivity='true',
                             connectivity_timeout=60, force='false'):
            raise NetworkException("Cannot sync network on new DC")

    @classmethod
    def teardown_class(cls):
        """
        Remove networks from the setup.
        Putting host on primary DC
        """
        logger.info("Remove networks from setup")
        if not removeNetwork(True, config.VLAN_NETWORKS[0],
                             data_center=config.DC_NAME[0]):
            raise NetworkException("Remove network from DC1 failed")
        if not removeNetFromSetup(host=config.HOSTS[0],
                                  auto_nics=[config.HOST_NICS[0]],
                                  network=[config.VLAN_NETWORKS[0]]):
            raise NetworkException("Remove network from DC2/CL2/Host failed")
        logger.info("Put the host on the DC1")
        assert(deactivateHost(True, host=config.HOSTS[0]))
        if not updateHost(True, host=config.HOSTS[0],
                          cluster=config.CLUSTER_NAME[0]):
            raise NetworkException("Cannot move host to another Cluster")
        assert(activateHost(True, host=config.HOSTS[0]))


@attr(tier=1)
class SyncCase07(TestCase):
    """
    Sync 3 networks on different NICs with
    MTU, VLAN and VM changed
    """
    __test__ = len(config.HOST_NICS) > 3

    @classmethod
    def setup_class(cls):
        """
        Create and attach networks with VLAN, MTU and VM to host
        Update networks with different MTU, VLAN for the first 2 networks
        Update VM network to non-VM network for the 3rd network
        """
        local_dict = {config.VLAN_NETWORKS[0]: {'vlan_id':
                                                config.VLAN_ID[0],
                                                'nic': config.HOST_NICS[1],
                                                'required': 'false'},
                      config.VLAN_NETWORKS[1]: {'mtu': 9000,
                                                'nic': config.HOST_NICS[2],
                                                'required': 'false'},
                      config.VLAN_NETWORKS[2]: {'nic': config.HOST_NICS[3],
                                                'required': 'false'}}

        logger.info("Attach VLAN, MTU and VM networks to the DC/Cluster/Host")
        if not createAndAttachNetworkSN(data_center=config.DC_NAME[0],
                                        cluster=config.CLUSTER_NAME[0],
                                        host=config.HOSTS[0],
                                        network_dict=local_dict,
                                        auto_nics=[config.HOST_NICS[0],
                                                   config.HOST_NICS[1]]):
            raise NetworkException("Cannot create and attach networks")

    @istest
    @tcms(6665, 205919)
    def sync_networks(self):
        """
        Check that the networks synced after update
        """
        vlan_dict = {"vlan_id": "10"}
        mtu_dict = {"mtu": "1500"}
        bridge_dict = {"bridge": False}

        logger.info("Update VM network to be non-VM")
        if not updateNetwork(True, network=config.VLAN_NETWORKS[2],
                             data_center=config.DC_NAME[0], usages=''):
            raise NetworkException("Cannot update network to be non-VM")

        sample1 = TimeoutingSampler(timeout=60, sleep=1,
                                    func=checkHostNicParameters,
                                    host=config.HOSTS[0],
                                    nic=config.HOST_NICS[3],
                                    **bridge_dict)

        if not sample1.waitForFuncStatus(result=True):
            raise NetworkException("Network is VM network and should be "
                                   "Non-VM")

        logger.info("Update VLAN network to VLAN 10")
        if not updateNetwork(True, network=config.VLAN_NETWORKS[0],
                             data_center=config.DC_NAME[0], vlan_id=10):
            raise NetworkException("Cannot update network to be untagged")

        sample2 = TimeoutingSampler(timeout=60, sleep=1,
                                    func=checkHostNicParameters,
                                    host=config.HOSTS[0],
                                    nic=config.HOST_NICS[1],
                                    **vlan_dict)

        if not sample2.waitForFuncStatus(result=True):
            raise NetworkException("Couldn't get correct vlan interface on "
                                   "host")

        logger.info("Update MTU network with MTU 1500")
        if not updateNetwork(True, network=config.VLAN_NETWORKS[1],
                             data_center=config.DC_NAME[0], mtu=1500):
            raise NetworkException("Cannot update network with mtu 1500")

        sample3 = TimeoutingSampler(timeout=60, sleep=1,
                                    func=checkHostNicParameters,
                                    host=config.HOSTS[0],
                                    nic=config.HOST_NICS[2],
                                    **mtu_dict)

        if not sample3.waitForFuncStatus(result=True):
            raise NetworkException("Couldn't get correct MTU on host")

    @classmethod
    def teardown_class(cls):
        """
        Remove networks from the setup.
        """
        logger.info("Remove networks from setup")
        if not removeNetFromSetup(host=config.HOSTS[0],
                                  auto_nics=[config.HOST_NICS[0]],
                                  network=[config.VLAN_NETWORKS[0],
                                           config.VLAN_NETWORKS[1],
                                           config.VLAN_NETWORKS[2]]):
            raise NetworkException("Cannot remove networks from setup")


@attr(tier=1)
class SyncCase08(TestCase):
    """
    Sync 2 networks on the same NIC with
    VLAN and non-VM changed
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Attach networks with VLAN and non-VM to DC/Cluster/Host
        Update networks with different VLAN for the first network
        Update non-VM network to VM network for the second network
        """
        local_dict = {config.VLAN_NETWORKS[0]: {'vlan_id':
                                                config.VLAN_ID[0],
                                                'nic': config.HOST_NICS[1],
                                                'required': 'false'},
                      config.VLAN_NETWORKS[1]: {'usages': '',
                                                'nic': config.HOST_NICS[1],
                                                'required': 'false'}}

        logger.info("Attach network with VM network on DC with host")
        if not createAndAttachNetworkSN(data_center=config.DC_NAME[0],
                                        cluster=config.CLUSTER_NAME[0],
                                        host=config.HOSTS[0],
                                        network_dict=local_dict,
                                        auto_nics=[config.HOST_NICS[0]]):
            raise NetworkException("Cannot create and attach networks")

    @istest
    @tcms(6665, 205932)
    def sync_network(self):
        """
        Sync networks after update
        """
        vlan_dict = {"vlan_id": "10"}
        bridge_dict = {"bridged": "vm"}

        logger.info("Update VLAN network with VLAN 10")
        if not updateNetwork(True, network=config.VLAN_NETWORKS[0],
                             data_center=config.DC_NAME[0], vlan_id=10):
            raise NetworkException("Cannot update network to be untagged")

        sample1 = TimeoutingSampler(timeout=60, sleep=1,
                                    func=checkHostNicParameters,
                                    host=config.HOSTS[0],
                                    nic=config.HOST_NICS[1],
                                    **vlan_dict)

        if not sample1.waitForFuncStatus(result=True):
            raise NetworkException("Couldn't get correct vlan interface on "
                                   "host")

        logger.info("Update non-VM network to be VM network")
        if not updateNetwork(True, network=config.VLAN_NETWORKS[1],
                             data_center=config.DC_NAME[0], usages='vm'):
            raise NetworkException("Cannot update  network to be non-VM")

        sample2 = TimeoutingSampler(timeout=60, sleep=1,
                                    func=checkHostNicParameters,
                                    host=config.HOSTS[0],
                                    nic=config.HOST_NICS[1],
                                    **bridge_dict)

        if not sample2.waitForFuncStatus(result=True):
            raise NetworkException("Network is Non-VM network and should be "
                                   "VM")

    @classmethod
    def teardown_class(cls):
        """
        Remove networks from the setup.
        """
        logger.info("Remove networks from setup")
        if not removeNetFromSetup(host=config.HOSTS[0],
                                  auto_nics=[config.HOST_NICS[0]],
                                  network=[config.VLAN_NETWORKS[0],
                                           config.VLAN_NETWORKS[1]]):
            raise NetworkException("Cannot remove networks from setup")
