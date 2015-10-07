"""
Testing MultiHost feature.
1 DC, 1 Cluster, 2 Hosts and 2 VMs will be created for testing.
MultiHost will be tested for untagged, tagged, MTU, VM/non-VM and bond
scenarios.
"""

import logging
import time
from art.unittest_lib import attr
from art.test_handler.tools import polarion  # pylint: disable=E0611
from rhevmtests.networking import config
from art.unittest_lib import NetworkTest as TestCase
from art.rhevm_api.utils.test_utils import checkMTU
from art.test_handler.exceptions import NetworkException
from art.core_api.apis_utils import TimeoutingSampler
from art.rhevm_api.tests_lib.high_level.networks import(
    createAndAttachNetworkSN, remove_net_from_setup, checkHostNicParameters
)
from art.rhevm_api.tests_lib.low_level.networks import(
    updateNetwork, checkVlanNet, isVmHostNetwork
)
from art.rhevm_api.tests_lib.low_level.hosts import(
    sendSNRequest, deactivateHost, updateHost, activateHost
)
from art.rhevm_api.tests_lib.low_level.vms import addNic, removeNic, updateNic
from art.rhevm_api.tests_lib.low_level.templates import(
    addTemplateNic, removeTemplateNic
)
from art.rhevm_api.tests_lib.low_level.clusters import (
    addCluster, removeCluster
)

logger = logging.getLogger("MultiHost_Cases")
HOST1_NICS, HOST2_NICS = None, None  # filled in setup module
SLEEP = 10

########################################################################

########################################################################
#                             Test Cases                               #
########################################################################


def setup_module():
    """
    obtain host NICs for the first Network Host
    """
    global HOST1_NICS, HOST2_NICS
    HOST1_NICS = config.VDS_HOSTS[0].nics
    HOST2_NICS = config.VDS_HOSTS[1].nics


class TestMultiHostTestCaseBase(TestCase):
    """
    base class which provides teardown class method for each test case
    """

    @classmethod
    def teardown_class(cls):
        """
        Remove networks from the setup.
        """
        logger.info("Starting teardown")
        sample1 = TimeoutingSampler(
            timeout=config.SAMPLER_TIMEOUT,
            sleep=1, func=remove_net_from_setup,
            host=config.VDS_HOSTS[:2], auto_nics=[0],
            data_center=config.DC_NAME[0], all_net=True,
            mgmt_network=config.MGMT_BRIDGE
        )
        if not sample1.waitForFuncStatus(result=True):
            logger.error("Cannot remove networks from setup")


@attr(tier=2)
class TestMultiHostCase01(TestMultiHostTestCaseBase):
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
        local_dict = {
            config.VLAN_NETWORKS[0]: {"nic": 1, "required": "false"}
        }

        logger.info("Attach network to DC/Cluster and Host")
        if not createAndAttachNetworkSN(
            data_center=config.DC_NAME[0], cluster=config.CLUSTER_NAME[0],
            host=config.VDS_HOSTS[0], network_dict=local_dict, auto_nics=[0]
        ):
            raise NetworkException("Cannot create and attach network")

    @polarion("RHEVM3-4067")
    def test_update_with_vlan(self):
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

        logger.info(
            "Update network with VLAN %s", config.VLAN_ID[0]
        )
        if not updateNetwork(
            True, network=config.VLAN_NETWORKS[0],
            data_center=config.DC_NAME[0], vlan_id=config.VLAN_ID[0]
        ):
            raise NetworkException(
                "Cannot update network to be tagged with VLAN %s"
                % config.VLAN_ID[0]
            )

        logger.info("Wait till the Host is updated with the change")
        sample1 = TimeoutingSampler(
            timeout=config.SAMPLER_TIMEOUT,
            sleep=1,
            func=checkHostNicParameters,
            host=config.HOSTS[0],
            nic=HOST1_NICS[1],
            **vlan_dict1
        )
        if not sample1.waitForFuncStatus(result=True):
            raise NetworkException(
                "Couldn't get correct VLAN interface on host"
            )

        logger.info("Check that the change is reflected to Host")
        if not checkVlanNet(
            host=config.HOSTS_IP[0], user=config.HOSTS_USER,
            password=config.HOSTS_PW, interface=HOST1_NICS[1],
            vlan=config.VLAN_ID[0]
        ):
            raise NetworkException(
                "Host %s was not updated with correct VLAN %s"
                % (config.HOSTS[0], config.VLAN_ID[0])
            )

        logger.info("Update network with VLAN %s", config.VLAN_ID[1])
        if not updateNetwork(
            True, network=config.VLAN_NETWORKS[0],
            data_center=config.DC_NAME[0], vlan_id=config.VLAN_ID[1]
        ):
            raise NetworkException(
                "Cannot update network to be tagged with VLAN %s"
                % config.VLAN_ID[1]
            )

        logger.info("Wait till the Host is updated with the change")
        sample2 = TimeoutingSampler(
            timeout=config.SAMPLER_TIMEOUT,
            sleep=1,
            func=checkHostNicParameters,
            host=config.HOSTS[0],
            nic=HOST1_NICS[1],
            **vlan_dict2
        )
        if not sample2.waitForFuncStatus(result=True):
            raise NetworkException(
                "Couldn't get correct VLAN interface on host"
            )

        logger.info("Check that the change is reflected to Host")
        if not checkVlanNet(
            host=config.HOSTS_IP[0], user=config.HOSTS_USER,
            password=config.HOSTS_PW, interface=HOST1_NICS[1],
            vlan=config.VLAN_ID[1]
        ):
            raise NetworkException(
                "Host %s was not updated with correct VLAN %s"
                % (config.HOSTS[0], config.VLAN_ID[1])
            )

        logger.info("Update network to be untagged")
        if not updateNetwork(
            True, network=config.VLAN_NETWORKS[0],
            data_center=config.DC_NAME[0], vlan_id=None
        ):
            raise NetworkException("Cannot update network to be untagged")

        logger.info("Wait till the Host is updated with the change")
        if not sample2.waitForFuncStatus(result=False):
            raise NetworkException(
                "Could get VLAN interface on host but shouldn't"
            )

        logger.info("Check that the change is reflected to Host")
        if checkVlanNet(
            host=config.HOSTS_IP[0], user=config.HOSTS_USER,
            password=config.HOSTS_PW, interface=HOST1_NICS[1],
            vlan=config.VLAN_ID[1]
        ):
            raise NetworkException(
                "Network on Host %s was not updated to be untagged"
                % config.HOSTS[0]
            )


@attr(tier=2)
class TestMultiHostCase02(TestMultiHostTestCaseBase):
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
        dict_dc1 = {
            config.NETWORKS[0]: {"nic": 1, "required": "false"}
        }

        logger.info("Attach network to DC/Cluster/Host")
        if not createAndAttachNetworkSN(
            data_center=config.DC_NAME[0], cluster=config.CLUSTER_NAME[0],
            host=config.VDS_HOSTS[0], network_dict=dict_dc1, auto_nics=[0]
        ):
            raise NetworkException("Cannot create and attach network")

    @polarion("RHEVM3-4080")
    def test_update_with_mtu(self):
        """
        1) Update network with MTU 9000
        2) Check that the Host was updated with MTU 9000
        3) Update network with MTU 1500
        4) Check that the Host was updated with MTU 1500
        """
        mtu_dict1 = {"mtu": config.MTU[0]}
        mtu_dict2 = {"mtu": config.MTU[-1]}

        logger.info("Update network with MTU %s", config.MTU[0])
        if not updateNetwork(
            True, network=config.NETWORKS[0],
            data_center=config.DC_NAME[0], mtu=config.MTU[0]
        ):
            raise NetworkException(
                "Cannot update  network with  MTU %s" % config.MTU[0]
            )

        logger.info("Wait till the Host is updated with the change")
        sample1 = TimeoutingSampler(
            timeout=config.SAMPLER_TIMEOUT,
            sleep=1,
            func=checkHostNicParameters,
            host=config.HOSTS[0],
            nic=HOST1_NICS[1],
            **mtu_dict1
        )
        if not sample1.waitForFuncStatus(result=True):
            raise NetworkException("Couldn't get correct MTU on host")

        logger.info("Check that the change is reflected to Host")
        logger.info(
            "Checking logical layer of bridged network %s on host %s",
            config.NETWORKS[0], config.HOSTS[0]
        )
        if not checkMTU(
            host=config.HOSTS_IP[0], user=config.HOSTS_USER,
            password=config.HOSTS_PW, mtu=config.MTU[0],
            physical_layer=False, network=config.NETWORKS[0],
            nic=HOST1_NICS[1]
        ):
            raise NetworkException(
                "Logical layer: MTU should be %s" % config.MTU[0]
            )

        logger.info(
            "Checking physical layer of bridged network %s on host %s",
            config.NETWORKS[0], config.HOSTS[0]
        )
        if not checkMTU(
            host=config.HOSTS_IP[0], user=config.HOSTS_USER,
            password=config.HOSTS_PW, mtu=config.MTU[0], nic=HOST1_NICS[1]
        ):
            raise NetworkException(
                "Physical layer: MTU should be %s" % config.MTU[0]
            )

        logger.info("Update MTU network with MTU %s", config.MTU[-1])
        if not updateNetwork(
            True, network=config.NETWORKS[0], data_center=config.DC_NAME[0],
            mtu=config.MTU[-1]
        ):
            raise NetworkException(
                "Cannot update network with MTU %s" % config.MTU[-1]
            )

        logger.info("Wait till the Host is updated with the change")
        sample2 = TimeoutingSampler(
            timeout=config.SAMPLER_TIMEOUT,
            sleep=1,
            func=checkHostNicParameters,
            host=config.HOSTS[0],
            nic=HOST1_NICS[1],
            **mtu_dict2
        )
        if not sample2.waitForFuncStatus(result=True):
            raise NetworkException("Couldn't get correct MTU on host")

        logger.info("Check that the change is reflected to Host")
        logger.info(
            "Checking logical layer of bridged network %s on host %s",
            config.NETWORKS[0], config.HOSTS[0]
        )
        if not checkMTU(
            host=config.HOSTS_IP[0], user=config.HOSTS_USER,
            password=config.HOSTS_PW, mtu=config.MTU[-1], physical_layer=False,
            network=config.NETWORKS[0], nic=HOST1_NICS[1]
        ):
            raise NetworkException(
                "Logical layer: MTU should be %s" % config.MTU[0]
            )

        logger.info(
            "Checking physical layer of bridged network %s on host %s"
            % (config.NETWORKS[0], config.HOSTS[0])
        )
        if not checkMTU(
            host=config.HOSTS_IP[0], user=config.HOSTS_USER,
            password=config.HOSTS_PW, mtu=config.MTU[-1], nic=HOST1_NICS[1]
        ):
            raise NetworkException(
                "Physical layer: MTU should be %s" % config.MTU[0]
            )


@attr(tier=2)
class TestMultiHostCase03(TestMultiHostTestCaseBase):
    """
    Update VM network to be non-VM network
    Update non-VM network to be VM network
    """
    __test__ = True
    bz = {"1237032": {"engine": ["rest", "sdk", "java"], "version": ["3.6"]}}

    @classmethod
    def setup_class(cls):
        """
        Create and attach network on DC, Cluster and the host
        """

        dict_dc1 = {
            config.NETWORKS[0]: {"nic": 1, "required": "false"}
        }

        logger.info("Attach network to DC/Cluster/Host")
        if not createAndAttachNetworkSN(
            data_center=config.DC_NAME[0], cluster=config.CLUSTER_NAME[0],
            host=config.VDS_HOSTS[0],  network_dict=dict_dc1, auto_nics=[0]
        ):
            raise NetworkException("Cannot create and attach network")

    @polarion("RHEVM3-4072")
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
                "Cannot update network to be non-VM network")

        logger.info("Wait till the Host is updated with the change")
        sample1 = TimeoutingSampler(
            timeout=config.SAMPLER_TIMEOUT,
            sleep=1,
            func=checkHostNicParameters,
            host=config.HOSTS[0],
            nic=HOST1_NICS[1],
            **bridge_dict1
        )
        if not sample1.waitForFuncStatus(result=True):
            raise NetworkException(
                "Network is VM network and should be Non-VM")

        logger.info("Check that the change is reflected to Host")
        if isVmHostNetwork(
            host=config.HOSTS_IP[0], user=config.HOSTS_USER,
            password=config.HOSTS_PW, net_name=config.NETWORKS[0],
            conn_timeout=45
        ):
            raise NetworkException(
                "Network on host %s was not updated to be non-VM network"
                % config.HOSTS[0]
            )

        logger.info(
            "Update network %s to be VM network", config.NETWORKS[0]
        )
        if not updateNetwork(
            True, network=config.NETWORKS[0], data_center=config.DC_NAME[0],
            usages="vm"
        ):
            raise NetworkException("Cannot update network to be VM network")

        logger.info("Wait till the Host is updated with the change")
        sample2 = TimeoutingSampler(
            timeout=config.SAMPLER_TIMEOUT,
            sleep=1,
            func=checkHostNicParameters,
            host=config.HOSTS[0],
            nic=HOST1_NICS[1],
            **bridge_dict2
        )
        if not sample2.waitForFuncStatus(result=True):
            raise NetworkException("Network is not a VM network but should be")

        logger.info("Check that the change is reflected to Host")
        if not isVmHostNetwork(
            host=config.HOSTS_IP[0], user=config.HOSTS_USER,
            password=config.HOSTS_PW, net_name=config.NETWORKS[0]
        ):
            raise NetworkException(
                "Network on host %s was not updated to be VM network"
                % config.HOSTS[0]
            )


@attr(tier=2)
class TestMultiHostCase04(TestMultiHostTestCaseBase):
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

        dict_dc1 = {
            config.NETWORKS[0]: {"nic": 1, "required": "false"}
        }

        logger.info("Attach network to DC/Cluster/Host")
        if not createAndAttachNetworkSN(
            data_center=config.DC_NAME[0], cluster=config.CLUSTER_NAME[0],
            host=config.VDS_HOSTS[0], network_dict=dict_dc1, auto_nics=[0]
        ):
            raise NetworkException("Cannot create and attach network")

    @polarion("RHEVM3-4079")
    def test_update_net_name(self):
        """
        1) Try to update network name when the network resides on the Host
        2) Try to update network name when the network resides on VM
        3) Try to update network name when the network resides on Template
        All cases should fail being negative cases
        4) Update network name when the network resides only on DC and Cluster
        Test should succeed
        """

        logger.info(
            "Negative: Try to update network name when network resides on host"
        )
        if not updateNetwork(
            False, network=config.NETWORKS[0], data_center=config.DC_NAME[0],
            name=config.NETWORKS[1]
        ):
            raise NetworkException("Could update network name when shouldn't")

        logger.info("Remove network from the Host")
        if not sendSNRequest(
            True, host=config.HOSTS[0],
            auto_nics=[config.VDS_HOSTS[0].nics[0]], check_connectivity="true",
            connectivity_timeout=config.CONNECT_TIMEOUT, force="false"
        ):
            raise NetworkException("Cannot remove Network from Host")

        logger.info("Add network to the non-running VM")
        if not addNic(
            True, config.VM_NAME[1], name="nic2", network=config.NETWORKS[0]
        ):
            raise NetworkException("Cannot add vNIC to VM")

        logger.info(
            "Negative: Try to update network name when network resides on VM"
        )
        if not updateNetwork(
            False, network=config.NETWORKS[0], data_center=config.DC_NAME[0],
            name=config.NETWORKS[1]
        ):
            raise NetworkException("Could update network name when shouldn't")

        logger.info("Remove network from VM")
        if not removeNic(True, config.VM_NAME[1], "nic2"):
            raise NetworkException("Cannot remove NIC from VM")

        logger.info("Put network on the Template")
        if not addTemplateNic(
            True, config.TEMPLATE_NAME[0], name="nic2",
            data_center=config.DC_NAME[0], network=config.NETWORKS[0]
        ):
            raise NetworkException("Cannot add NIC to Template")

        logger.info(
            "Negative: Try to update network name when network resides "
            "on Template"
        )
        if not updateNetwork(
            False, network=config.NETWORKS[0], data_center=config.DC_NAME[0],
            name=config.NETWORKS[1]
        ):
            raise NetworkException("Could update network name when shouldn't")

        logger.info("Remove network from Template")
        if not removeTemplateNic(True, config.TEMPLATE_NAME[0], "nic2"):
            raise NetworkException("Cannot remove nic from Template")

        logger.info(
            "Update network name when network resides only on DC and Cluster"
        )
        if not updateNetwork(
            True, network=config.NETWORKS[0], data_center=config.DC_NAME[0],
            name=config.NETWORKS[1]
        ):
            raise NetworkException("Couldn't update network name when should")


@attr(tier=2)
class TestMultiHostCase05(TestMultiHostTestCaseBase):
    """
    Update network on running/non-running VM:
    1) Positive: Change MTU on net when running VM is using it
    2) Positive: Change VLAN on net when running VM is using it
    3) Positive: Change MTU on net when non-running VM is using it
    4) Positive: Change VLAN on net when non-running VM is using it
    5) Negative: Update non-VM network to be VM network used by non-running VM
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Create and attach network on DC, Cluster,Host, running and
        non-running VMs
        """

        dict_dc1 = {
            config.NETWORKS[0]: {"nic": 1, "required": "false"}
        }

        logger.info("Attach network to DC/Cluster/Host")
        if not createAndAttachNetworkSN(
            data_center=config.DC_NAME[0], cluster=config.CLUSTER_NAME[0],
            host=config.VDS_HOSTS[0], network_dict=dict_dc1, auto_nics=[0]
        ):
            raise NetworkException("Cannot create and attach network")

        logger.info("Add network to running and non-running VMs")
        for i in range(2):
            if not addNic(
                True, config.VM_NAME[i], name="nic2",
                network=config.NETWORKS[0]
            ):
                raise NetworkException(
                    "Cannot add vNIC %s for network to VM %s "
                    % (config.NETWORKS[0], config.VM_NAME[i])
                )

    @polarion("RHEVM3-4074")
    def test_update_net_on_vm(self):
        """
        1) Positive: Change MTU on net when running VM is using it
        2) Positive: Change VLAN on net when running VM is using it
        3) Positive: Change MTU on net when non-running VM is using it
        4) Positive: Change VLAN on net when non-running VM is using it
        5) Negative: Update non-VM network to be VM network used by
        non-running VM
        """

        mtu_dict1 = {"mtu": config.MTU[0]}
        vlan_dict1 = {"vlan_id": config.VLAN_ID[0]}

        logger.info("Update MTU network with MTU %s", config.MTU[0])
        if not updateNetwork(
            positive=True, network=config.NETWORKS[0],
            data_center=config.DC_NAME[0], mtu=config.MTU[0]
        ):
            raise NetworkException(
                "Couldn't update  network with MTU %s when running VM is using"
                " the network" % config.MTU[0]
            )

        logger.info("Wait till the Host is updated with the change")
        sample1 = TimeoutingSampler(
            timeout=config.SAMPLER_TIMEOUT,
            sleep=1,
            func=checkHostNicParameters,
            host=config.HOSTS[0],
            nic=HOST1_NICS[1],
            **mtu_dict1
        )
        if not sample1.waitForFuncStatus(result=True):
            raise NetworkException("Couldn't get correct MTU on host")

        logger.info("Update network with VLAN %s", config.VLAN_ID[0])
        time.sleep(SLEEP)
        if not updateNetwork(
            positive=True, network=config.NETWORKS[0],
            data_center=config.DC_NAME[0], vlan_id=config.VLAN_ID[0]
        ):
            raise NetworkException(
                "Couldn't update network to be tagged with VLAN %s when "
                "running VM is using the network" % config.VLAN_ID[0]
            )

        logger.info("Wait till the Host is updated with the change")
        sample1 = TimeoutingSampler(
            timeout=config.SAMPLER_TIMEOUT,
            sleep=1,
            func=checkHostNicParameters,
            host=config.HOSTS[0],
            nic=HOST1_NICS[1],
            **vlan_dict1
        )
        logger.info(
            "Unplugging NIC with the network in order to be able to update"
            " the Network that reside on that NIC"
        )
        if not sample1.waitForFuncStatus(result=True):
            raise NetworkException("Couldn't get correct MTU on host")

        if not updateNic(
            True, config.VM_NAME[0], "nic2", plugged="false"
        ):
            raise NetworkException("Couldn't unplug NIC")

        logger.info("Update MTU network with MTU %s", config.MTU[0])
        time.sleep(SLEEP)
        if not updateNetwork(
            True, network=config.NETWORKS[0], data_center=config.DC_NAME[0],
            mtu=config.MTU[0]
        ):
            raise NetworkException(
                "Couldn't update  network (with MTU 9000) when Network resides"
                " on non-running VM and unplugged NIC of running VM"
            )

        logger.info("Wait till the Host is updated with the change")
        sample1 = TimeoutingSampler(
            timeout=config.SAMPLER_TIMEOUT,
            sleep=1,
            func=checkHostNicParameters,
            host=config.HOSTS[0],
            nic=HOST1_NICS[1],
            **mtu_dict1
        )
        if not sample1.waitForFuncStatus(result=True):
            raise NetworkException("Couldn't get correct MTU on host")

        logger.info("Check that the change is reflected to Host")
        logger.info("Checking logical layer of bridged network %s on host %s",
                    config.NETWORKS[0], config.HOSTS[0])

        if not checkMTU(
            host=config.HOSTS_IP[0], user=config.HOSTS_USER,
            password=config.HOSTS_PW, mtu=config.MTU[0],
            physical_layer=False, network=config.NETWORKS[0],
            nic=HOST1_NICS[1]
        ):
            raise NetworkException(
                "Logical layer: MTU should be %s" % config.MTU[0]
            )

        logger.info(
            "Checking physical layer of bridged network %s on host %s",
            config.NETWORKS[0], config.HOSTS[0]
        )
        if not checkMTU(
            host=config.HOSTS_IP[0], user=config.HOSTS_USER,
            password=config.HOSTS_PW, mtu=config.MTU[0], nic=HOST1_NICS[1]
        ):
            raise NetworkException(
                "Physical layer: MTU should be %s" % config.MTU[0]
            )

        logger.info("Update network with VLAN %s", config.VLAN_ID[0])
        time.sleep(SLEEP)
        if not updateNetwork(
            True, network=config.NETWORKS[0], data_center=config.DC_NAME[0],
            vlan_id=config.VLAN_ID[0]
        ):
            raise NetworkException(
                "Couldn't update network (to be tagged with VLAN %s) when "
                "Network resides on non-running VM and/or unplugged NIC of"
                "running VM" % config.VLAN_ID[0]
            )

        logger.info("Wait till the Host is updated with the change")
        sample1 = TimeoutingSampler(
            timeout=config.SAMPLER_TIMEOUT,
            sleep=1,
            func=checkHostNicParameters,
            host=config.HOSTS[0],
            nic=HOST1_NICS[1],
            **vlan_dict1
        )
        if not sample1.waitForFuncStatus(result=True):
            raise NetworkException(
                "Couldn't get correct VLAN interface on host"
            )

        logger.info("Check that the change is reflected to Host")
        if not checkVlanNet(
            host=config.HOSTS_IP[0], user=config.HOSTS_USER,
            password=config.HOSTS_PW, interface=HOST1_NICS[1],
            vlan=config.VLAN_ID[0]
        ):
            raise NetworkException(
                "Host %s was not updated with correct VLAN %s"
                % (config.HOSTS[0], config.VLAN_ID[0])
            )

        logger.info(
            "Negative: Update network %s to be non-VM network",
            config.NETWORKS[0]
        )
        if not updateNetwork(
            False, network=config.NETWORKS[0], data_center=config.DC_NAME[0],
            usages=""
        ):
            raise NetworkException(
                "Could update network to be non-VM net though it's attached"
                " to VM"
            )

        logger.info("Check that the change is reflected to Host")
        if not isVmHostNetwork(
            host=config.HOSTS_IP[0], user=config.HOSTS_USER,
            password=config.HOSTS_PW, net_name=config.NETWORKS[0]
        ):
            raise NetworkException(
                "Network on host %s was not updated to be non-VM network"
                % config.HOSTS[0]
            )

    @classmethod
    def teardown_class(cls):
        """
        Update MTU to default
        Remove Network from VMs
        Remove network from Host
        """
        mtu_dict1 = {"mtu": config.MTU[-1]}

        logger.info("Update MTU network with MTU %s", config.MTU[-1])
        if not updateNetwork(
            True, network=config.NETWORKS[0], data_center=config.DC_NAME[0],
            mtu=config.MTU[-1]
        ):
            logger.error(
                "Couldn't update  network with MTU %s ", config.MTU[-1]
            )

        logger.info("Wait till the Host is updated with the change")
        sample1 = TimeoutingSampler(
            timeout=config.SAMPLER_TIMEOUT,
            sleep=1,
            func=checkHostNicParameters,
            host=config.HOSTS[0],
            nic=HOST1_NICS[1],
            **mtu_dict1
        )
        if not sample1.waitForFuncStatus(result=True):
            logger.error("Couldn't update with correct MTU on host")

        logger.info("Remove network from VMs")
        for i in range(2):
            if not removeNic(True, config.VM_NAME[i], "nic2"):
                logger.error(
                    "Cannot remove NIC from VM %s ", config.VM_NAME[i]
                )
        super(TestMultiHostCase05, cls).teardown_class()


@attr(tier=2)
class TestMultiHostCase06(TestMultiHostTestCaseBase):
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

        dict_dc1 = {
            config.NETWORKS[0]: {"nic": 1, "required": "false"}
        }

        logger.info("Attach network to DC/Cluster/Host")
        if not createAndAttachNetworkSN(
            data_center=config.DC_NAME[0], cluster=config.CLUSTER_NAME[0],
            host=config.VDS_HOSTS[0], network_dict=dict_dc1, auto_nics=[0]
        ):
            raise NetworkException("Cannot create and attach network")

        logger.info("Attach NIC to the Template")
        if not addTemplateNic(
            True, config.TEMPLATE_NAME[0], name="nic2",
            data_center=config.DC_NAME[0], network=config.NETWORKS[0]
        ):
            raise NetworkException("Cannot add NIC to Template")

    @polarion("RHEVM3-4073")
    def test_update_net_on_template(self):
        """
        1) Negative: Try to update network from VM to non-VM
        2) Positive: Try to change MTU on net when template is using it
        3) Positive: Try to change VLAN on net when template is using it
        """
        mtu_dict1 = {"mtu": config.MTU[0]}
        vlan_dict1 = {"vlan_id": config.VLAN_ID[0]}

        logger.info(
            "Negative: Try to update network from VM to non-VM when network "
            "resides on Template"
        )
        if not updateNetwork(
            False, network=config.NETWORKS[0], data_center=config.DC_NAME[0],
            usages=""
        ):
            raise NetworkException(
                "Could update network to be non-VM net though it's attached "
                "to Template"
            )

        logger.info("Update network with MTU %s", config.MTU[0])
        if not updateNetwork(
            True, network=config.NETWORKS[0], data_center=config.DC_NAME[0],
            mtu=config.MTU[0]
        ):
            raise NetworkException(
                "Couldn't update  network with MTU %s when network resides "
                "on Template" % config.MTU[0]
            )

        logger.info("Wait till the Host is updated with the change")
        sample1 = TimeoutingSampler(
            timeout=config.SAMPLER_TIMEOUT,
            sleep=1,
            func=checkHostNicParameters,
            host=config.HOSTS[0],
            nic=HOST1_NICS[1],
            **mtu_dict1
        )
        if not sample1.waitForFuncStatus(result=True):
            raise NetworkException("Couldn't get correct MTU on host")

        logger.info("Check that the change is reflected to Host")
        logger.info(
            "Checking logical layer of bridged network %s on host %s"
            % (config.NETWORKS[0], config.HOSTS[0])
        )

        if not checkMTU(
            host=config.HOSTS_IP[0], user=config.HOSTS_USER,
            password=config.HOSTS_PW, mtu=config.MTU[0], physical_layer=False,
            network=config.NETWORKS[0], nic=HOST1_NICS[1]
        ):
            raise NetworkException(
                "Logical layer: MTU should be %s" % config.MTU[0]
            )

        logger.info(
            "Checking physical layer of bridged network %s on host %s",
            config.NETWORKS[0], config.HOSTS[0]
        )
        if not checkMTU(
            host=config.HOSTS_IP[0], user=config.HOSTS_USER,
            password=config.HOSTS_PW, mtu=config.MTU[0], nic=HOST1_NICS[1]
        ):
            raise NetworkException(
                "Physical layer: MTU should be %s" % config.MTU[0]
            )

        logger.info("Update network with VLAN %s", config.VLAN_ID[0])
        if not updateNetwork(
            True, network=config.NETWORKS[0], data_center=config.DC_NAME[0],
            vlan_id=config.VLAN_ID[0]
        ):
            raise NetworkException(
                "Couldn't update network to be tagged with VLAN %s when "
                "network resides on Template" % config.VLAN_ID[0]
            )

        logger.info("Wait till the Host is updated with the change")
        sample1 = TimeoutingSampler(
            timeout=config.SAMPLER_TIMEOUT,
            sleep=1,
            func=checkHostNicParameters,
            host=config.HOSTS[0],
            nic=HOST1_NICS[1],
            **vlan_dict1
        )
        if not sample1.waitForFuncStatus(result=True):
            raise NetworkException(
                "Couldn't get correct VLAN interface on host")

        logger.info("Check that the change is reflected to Host")
        if not checkVlanNet(
            host=config.HOSTS_IP[0], user=config.HOSTS_USER,
            password=config.HOSTS_PW, interface=HOST1_NICS[1],
            vlan=config.VLAN_ID[0]
        ):
            raise NetworkException(
                "Host %s was not updated with correct VLAN %s"
                % (config.HOSTS[0], config.VLAN_ID[0])
            )

    @classmethod
    def teardown_class(cls):
        """
        Update MTU to default
        Remove NIC from Template
        Remove network from the setup.
        """
        mtu_dict1 = {"mtu": config.MTU[-1]}

        logger.info("Update MTU network with MTU %s", config.MTU[-1])
        if not updateNetwork(
            True, network=config.NETWORKS[0], data_center=config.DC_NAME[0],
            mtu=config.MTU[-1]
        ):
            logger.error(
                "Couldn't update  network with MTU %s ", config.MTU[-1]
            )

        logger.info("Wait till the Host is updated with the change")
        sample1 = TimeoutingSampler(
            timeout=config.SAMPLER_TIMEOUT,
            sleep=1,
            func=checkHostNicParameters,
            host=config.HOSTS[0],
            nic=HOST1_NICS[1],
            **mtu_dict1
        )
        if not sample1.waitForFuncStatus(result=True):
            logger.error("Couldn't update with correct MTU on host")

        logger.info("Remove NIC from Template")
        if not removeTemplateNic(
            positive=True, template=config.TEMPLATE_NAME[0],
            nic=config.NIC_NAME[1]
        ):
            logger.error(
                "NIC %s wasn't removed from Template %s", config.NIC_NAME[1],
                config.TEMPLATE_NAME[0]
            )
        super(TestMultiHostCase06, cls).teardown_class()


@attr(tier=2)
class TestMultiHostCase07(TestMultiHostTestCaseBase):
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

        local_dict = {
            config.VLAN_NETWORKS[0]: {"nic": 1, "required": "false"}
        }

        logger.info("Attach network to DC/Cluster and 2 Hosts")
        if not createAndAttachNetworkSN(
            data_center=config.DC_NAME[0], cluster=config.CLUSTER_NAME[0],
            host=config.VDS_HOSTS[:2], network_dict=local_dict, auto_nics=[0]
        ):
            raise NetworkException("Cannot create and attach network")

    @polarion("RHEVM3-4078")
    def test_update_with_vlan_mtu(self):
        """
        1) Update network with VLAN 162
        3) Update network with MTU 9000
        4) Check that the both Hosts were updated with VLAN 162 and MTU 9000
        """

        mtu_dict1 = {"mtu": config.MTU[0]}
        sample1 = []

        logger.info(
            "Update network with VLAN %s and MTU %s ",
            config.VLAN_ID[0], config.MTU[0]
        )
        if not updateNetwork(
            True, network=config.VLAN_NETWORKS[0],
            data_center=config.DC_NAME[0], vlan_id=config.VLAN_ID[0],
            mtu=config.MTU[0]
        ):
            raise NetworkException(
                "Cannot update network to be tagged and to have MTU in one"
                " action"
            )

        logger.info(
            "Check that both Hosts are updated with correct MTU value"
        )
        for host, nic in zip(config.HOSTS[:2], (HOST1_NICS[1], HOST2_NICS[1])):
            sample1.append(
                TimeoutingSampler(
                    timeout=config.SAMPLER_TIMEOUT,
                    sleep=1,
                    func=checkHostNicParameters,
                    host=host,
                    nic=nic,
                    **mtu_dict1
                )
            )
        for i in range(2):
            if not sample1[i].waitForFuncStatus(result=True):
                raise NetworkException("Couldn't get correct MTU on host")

        logger.info("Check that the MTU change is reflected to both Hosts")
        for host, nic in zip(config.HOSTS_IP, (HOST1_NICS[1], HOST2_NICS[1])):
            logger.info(
                "Checking logical layer of bridged network %s on host %s"
                % (config.VLAN_NETWORKS[0], host)
            )

            if not checkMTU(
                host=host, user=config.HOSTS_USER, password=config.HOSTS_PW,
                mtu=config.MTU[0], physical_layer=False,
                network=config.VLAN_NETWORKS[0], nic=nic
            ):
                raise NetworkException(
                    "Logical layer: MTU should be %s" % config.MTU[0]
                )

            logger.info(
                "Checking physical layer of bridged network %s on host %s"
                % (config.NETWORKS[0], host)
            )
            if not checkMTU(
                host=host, user=config.HOSTS_USER, password=config.HOSTS_PW,
                mtu=config.MTU[0], nic=nic
            ):
                raise NetworkException(
                    "Physical layer: MTU should be %s" % config.MTU[0]
                )

        logger.info("Check that the VLAN change is reflected to both Hosts")
        for host, nic in zip(config.HOSTS_IP, (HOST1_NICS[1], HOST2_NICS[1])):
            if not checkVlanNet(
                host=host, user=config.HOSTS_USER, password=config.HOSTS_PW,
                interface=nic, vlan=config.VLAN_ID[0]
            ):
                raise NetworkException(
                    "Host %s was not updated with correct VLAN %s" %
                    (host, config.VLAN_ID[0])
                )

    @classmethod
    def teardown_class(cls):
        """
        Update MTU to default on both Hosts
        Remove network from the setup.
        """
        mtu_dict1 = {"mtu": config.MTU[-1]}
        sample1 = []

        logger.info("Update MTU network with MTU %s", config.MTU[-1])
        if not updateNetwork(
            True, network=config.VLAN_NETWORKS[0],
            data_center=config.DC_NAME[0], mtu=config.MTU[-1]
        ):
            logger.error(
                "Couldn't update  network with MTU %s ", config.MTU[-1]
            )

        logger.info("Check correct MTU on both Hosts")
        for host, nic in zip(config.HOSTS[:2], (HOST1_NICS[1], HOST2_NICS[1])):
            sample1.append(
                TimeoutingSampler(
                    timeout=config.SAMPLER_TIMEOUT,
                    sleep=1,
                    func=checkHostNicParameters,
                    host=host,
                    nic=nic,
                    **mtu_dict1
                )
            )
        for i in range(2):
            if not sample1[i].waitForFuncStatus(result=True):
                logger.error(
                    "Couldn't get MTU %s on host", config.MTU[-1]
                )
        super(TestMultiHostCase07, cls).teardown_class()


@attr(tier=2)
class TestMultiHostCase08(TestMultiHostTestCaseBase):
    """
    Update untagged network with VLAN and MTU when several hosts reside under
    the same DC, but under different Clusters of the same DC
    Make sure all the changes exist on both Hosts
    """
    __test__ = True
    cl_name2 = "new_CL_case08"

    @classmethod
    def setup_class(cls):
        """
        Move the second Host to different Cluster under the same DC
        Create network on DC/Clusters/Hosts
        """

        logger.info(
            "Add additional Cluster %s under DC %s ",
            cls.cl_name2, config.DC_NAME[0]
        )
        if not addCluster(
            positive=True, name=cls.cl_name2, cpu=config.CPU_NAME,
            data_center=config.DC_NAME[0], version=config.COMP_VERSION
        ):
            raise NetworkException(
                "Cannot add Cluster %s under DC %s " %
                (cls.cl_name2, config.DC_NAME[0])
            )

        logger.info(
            "Deactivate host %s, move it to Cluster %s and reactivate it",
            config.HOSTS[1], cls.cl_name2
        )
        if not deactivateHost(True, host=config.HOSTS[1]):
            raise NetworkException(
                "Cannot deactivate host %s" % config.HOSTS[1]
            )
        if not updateHost(
            True, host=config.HOSTS[1], cluster=cls.cl_name2
        ):
            raise NetworkException(
                "Cannot move host %s to Cluster %s" %
                (config.HOSTS[1], cls.cl_name2)
            )
        if not activateHost(True, host=config.HOSTS[1]):
            raise NetworkException(
                "Cannot activate host %s" % config.HOSTS[1]
            )

        local_dict = {config.VLAN_NETWORKS[0]: {"nic": 1,
                                                "required": "false"}}
        logger.info(
            "Attach network %s to DC %s, Cluster %s, host %s and %s",
            config.VLAN_NETWORKS[0], config.DC_NAME[0],
            config.CLUSTER_NAME[0], config.VDS_HOSTS[0], config.VDS_HOSTS[1]
        )
        if not createAndAttachNetworkSN(
            data_center=config.DC_NAME[0], cluster=config.CLUSTER_NAME[0],
            host=config.VDS_HOSTS[0], network_dict=local_dict, auto_nics=[0]
        ):
            raise NetworkException(
                "Cannot create and attach network %s to host %s" %
                (config.VLAN_NETWORKS[0], config.VDS_HOSTS[0])
            )
        if not createAndAttachNetworkSN(
            cluster=cls.cl_name2, host=config.VDS_HOSTS[1],
            network_dict=local_dict, auto_nics=[0]
        ):
            raise NetworkException(
                "Cannot create and attach network %s to host %s" %
                (config.VLAN_NETWORKS[0], config.VDS_HOSTS[1])
            )

    @polarion("RHEVM3-4077")
    def test_update_with_vlan_mtu(self):
        """
        1) Update network with VLAN 162
        3) Update network with MTU 9000
        4) Check that the both Hosts were updated with VLAN 162 and MTU 9000
        """

        mtu_dict1 = {"mtu": config.MTU[0]}
        sample1 = []

        logger.info(
            "Update network with VLAN %s and MTU %s ",
            config.VLAN_ID[0], config.MTU[0]
        )
        if not updateNetwork(
            True, network=config.VLAN_NETWORKS[0],
            data_center=config.DC_NAME[0], vlan_id=config.VLAN_ID[0],
            mtu=config.MTU[0]
        ):
            raise NetworkException(
                "Cannot update network to be tagged and to have MTU in "
                "one action"
            )

        logger.info(
            "Check that both Hosts are updated with correct MTU value"
        )
        for host, nic in zip(config.HOSTS[:2], (HOST1_NICS[1], HOST2_NICS[1])):
            sample1.append(
                TimeoutingSampler(
                    timeout=config.SAMPLER_TIMEOUT,
                    sleep=1,
                    func=checkHostNicParameters,
                    host=host,
                    nic=nic,
                    **mtu_dict1
                )
            )
        for i in range(2):
            if not sample1[i].waitForFuncStatus(result=True):
                raise NetworkException("Couldn't get correct MTU on host")

        logger.info("Check that the MTU change is reflected to both Hosts")
        for host, nic in zip(config.HOSTS_IP, (HOST1_NICS[1], HOST2_NICS[1])):
            logger.info(
                "Checking logical layer of bridged network %s on host %s",
                config.VLAN_NETWORKS[0], host
            )
            if not checkMTU(
                host=host, user=config.HOSTS_USER, password=config.HOSTS_PW,
                mtu=config.MTU[0], physical_layer=False,
                network=config.VLAN_NETWORKS[0], nic=nic
            ):
                raise NetworkException(
                    "Logical layer: MTU should be %s" % config.MTU[0]
                )

            logger.info(
                "Checking physical layer of bridged network %s on host %s",
                config.NETWORKS[0], host
            )
            if not checkMTU(
                host=host, user=config.HOSTS_USER, password=config.HOSTS_PW,
                mtu=config.MTU[0], nic=nic
            ):
                raise NetworkException(
                    "Physical layer: MTU should be %s" % config.MTU[0]
                )

        logger.info("Check that the VLAN change is reflected to both Hosts")
        for host, nic in zip(config.HOSTS_IP, (HOST1_NICS[1], HOST2_NICS[1])):
            if not checkVlanNet(
                host=host, user=config.HOSTS_USER, password=config.HOSTS_PW,
                interface=nic, vlan=config.VLAN_ID[0]
            ):
                raise NetworkException(
                    "Host %s was not updated with correct VLAN %s" %
                    (host, config.VLAN_ID[0])
                )

    @classmethod
    def teardown_class(cls):
        """
        Update MTU to default on both Hosts
        Remove network from the setup.
        Return Host to original Cluster
        Remove Cluster
        """

        mtu_dict1 = {"mtu": config.MTU[-1]}
        sample1 = []

        logger.info(
            "Update network %s with MTU %s", config.VLAN_NETWORKS[0],
            config.MTU[-1]
        )
        if not updateNetwork(
            True, network=config.VLAN_NETWORKS[0],
            data_center=config.DC_NAME[0], mtu=config.MTU[-1]
        ):
            logger.error(
                "Couldn't update  network with MTU %s ", config.MTU[-1]
            )

        logger.info("Check correct MTU on both Hosts")
        for host, nic in zip(config.HOSTS[:2], (HOST1_NICS[1], HOST2_NICS[1])):
            sample1.append(
                TimeoutingSampler(
                    timeout=config.SAMPLER_TIMEOUT,
                    sleep=1,
                    func=checkHostNicParameters,
                    host=host,
                    nic=nic,
                    **mtu_dict1
                )
            )
        for i in range(2):
            if not sample1[i].waitForFuncStatus(result=True):
                logger.error(
                    "Couldn't get correct MTU (%s) on host %s and %s",
                    config.MTU[-1], config.HOSTS[0], config.HOSTS[1])

        logger.info("Remove network %s from setup", config.VLAN_NETWORKS[0])
        if not remove_net_from_setup(
            host=config.VDS_HOSTS[:2], auto_nics=[0],
            network=[config.VLAN_NETWORKS[0]]
        ):
            logger.error(
                "Cannot remove network %s from setup", config.VLAN_NETWORKS[0]
            )
        logger.info(
            "Deactivate host %s, move it to its original cluster %s and "
            "reactivate it", config.HOSTS[1], config.CLUSTER_NAME[0]
        )
        if not deactivateHost(True, host=config.HOSTS[1]):
            logger.error(
                "Cannot deactivate host %s", config.HOSTS[1]
            )

        if not updateHost(
                True, host=config.HOSTS[1], cluster=config.CLUSTER_NAME[0]):
                logger.error(
                    "Cannot move host %s to Cluster %s",
                    config.HOSTS[1], config.CLUSTER_NAME[0]
                )
        if not activateHost(True, host=config.HOSTS[1]):
            logger.error(
                "Cannot activate host %s in cluster %s",
                config.HOSTS[1], config.CLUSTER_NAME[0])

        if not removeCluster(True, cls.cl_name2):
            logger.error(
                "Cannot remove cluster %s from setup", cls.cl_name2
            )


@attr(tier=2)
class TestMultiHostCase09(TestMultiHostTestCaseBase):
    """
    Update untagged network with VLAN when that network is attached to
    the Host bond
    Update tagged network with another VLAN when that network is attached to
    the Host bond
    Update tagged network to be untagged when that network is attached to
    the Host bond
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Create untagged network on DC/Cluster/Host
        """
        local_dict = {
            config.VLAN_NETWORKS[0]: {
                "nic": config.BOND[0], "slaves": [2, 3], "required": "false"
            }
        }

        logger.info("Attach network to DC/Cluster and bond on Host")
        if not createAndAttachNetworkSN(
            data_center=config.DC_NAME[0], cluster=config.CLUSTER_NAME[0],
            host=config.VDS_HOSTS[0], network_dict=local_dict, auto_nics=[0]
        ):
            raise NetworkException("Cannot create and attach network")

    @polarion("RHEVM3-4069")
    def test_update_with_vlan(self):
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
        if not updateNetwork(
            True, network=config.VLAN_NETWORKS[0],
            data_center=config.DC_NAME[0], vlan_id=config.VLAN_ID[0]
        ):
            raise NetworkException(
                "Cannot update network to be tagged with VLAN %s" %
                config.VLAN_ID[0]
            )

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
            raise NetworkException(
                "Couldn't get correct VLAN interface on host"
            )

        logger.info("Check that the change is reflected to Host")
        if not checkVlanNet(
            host=config.HOSTS_IP[0], user=config.HOSTS_USER,
            password=config.HOSTS_PW, interface=config.BOND[0],
            vlan=config.VLAN_ID[0]
        ):
            raise NetworkException(
                "Host %s was not updated with correct VLAN %s" %
                (config.HOSTS[0], config.VLAN_ID[0])
            )

        logger.info("Update network with VLAN %s", config.VLAN_ID[1])
        if not updateNetwork(
            True, network=config.VLAN_NETWORKS[0],
            data_center=config.DC_NAME[0], vlan_id=config.VLAN_ID[1]
        ):
            raise NetworkException(
                "Cannot update network to be tagged with VLAN %s" %
                config.VLAN_ID[1]
            )

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
            raise NetworkException(
                "Couldn't get correct VLAN interface on host"
            )

        logger.info("Check that the change is reflected to Host")
        if not checkVlanNet(
            host=config.HOSTS_IP[0], user=config.HOSTS_USER,
            password=config.HOSTS_PW, interface=config.BOND[0],
            vlan=config.VLAN_ID[1]
        ):
            raise NetworkException(
                "Host %s was not updated with correct VLAN %s" %
                (config.HOSTS[0], config.VLAN_ID[1])
            )

        logger.info("Update network to be untagged")
        if not updateNetwork(
            True, network=config.VLAN_NETWORKS[0],
            data_center=config.DC_NAME[0], vlan_id=None
        ):
            raise NetworkException("Cannot update network to be untagged")

        logger.info("Wait till the Host is updated with the change")
        if not sample2.waitForFuncStatus(result=False):
            raise NetworkException(
                "Could get VLAN interface on host but shouldn't"
            )

        logger.info("Check that the change is reflected to Host")
        if checkVlanNet(
            host=config.HOSTS_IP[0], user=config.HOSTS_USER,
            password=config.HOSTS_PW, interface=config.BOND[0],
            vlan=config.VLAN_ID[1]
        ):
            raise NetworkException(
                "Network on Host %s was not updated to be untagged" %
                config.HOSTS[0]
            )


@attr(tier=2)
class TestMultiHostCase10(TestMultiHostTestCaseBase):
    """
    Update network with the default MTU to the new MTU when that network
    is attached to the Host bond
    Update network with another MTU value when that network is attached to
    the Host bond
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Create and attach network on DC, Cluster and the host
        """
        local_dict = {
            config.NETWORKS[0]: {
                "nic": config.BOND[0], "slaves": [2, 3], "required": "false"
            }
        }

        logger.info("Attach network to DC/Cluster/Host")
        if not createAndAttachNetworkSN(
            data_center=config.DC_NAME[0], cluster=config.CLUSTER_NAME[0],
            host=config.VDS_HOSTS[0], network_dict=local_dict, auto_nics=[0]
        ):
            raise NetworkException("Cannot create and attach network")

    @polarion("RHEVM3-4068")
    def test_update_with_mtu(self):
        """
        1) Update network with MTU 9000
        2) Check that the Host was updated with MTU 9000
        3) Update network with MTU 1500
        4) Check that the Host was updated with MTU 1500
        """
        mtu_dict1 = {"mtu": config.MTU[0]}
        mtu_dict2 = {"mtu": config.MTU[-1]}

        logger.info("Update network with MTU %s", config.MTU[0])
        if not updateNetwork(
            True, network=config.NETWORKS[0], data_center=config.DC_NAME[0],
            mtu=config.MTU[0]
        ):
            raise NetworkException(
                "Cannot update  network with  MTU %s" % config.MTU[0]
            )

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
        logger.info(
            "Checking logical layer of bridged network %s on host %s"
            % (config.NETWORKS[0], config.HOSTS[0])
        )
        if not checkMTU(
            host=config.HOSTS_IP[0], user=config.HOSTS_USER,
            password=config.HOSTS_PW, mtu=config.MTU[0], physical_layer=False,
            network=config.NETWORKS[0], nic=config.BOND[0]
        ):
            raise NetworkException(
                "Logical layer: MTU should be %s" % config.MTU[0]
            )

        logger.info(
            "Checking physical layer of bridged network %s on host %s"
            % (config.NETWORKS[0], config.HOSTS[0])
        )
        if not checkMTU(
            host=config.HOSTS_IP[0], user=config.HOSTS_USER,
            password=config.HOSTS_PW, mtu=config.MTU[0], nic=config.BOND[0]
        ):
            raise NetworkException(
                "Physical layer: MTU should be %s" % config.MTU[0]
            )

        logger.info("Update MTU network with MTU %s", config.MTU[-1])
        if not updateNetwork(
            True, network=config.NETWORKS[0], data_center=config.DC_NAME[0],
            mtu=config.MTU[-1]
        ):
            raise NetworkException(
                "Cannot update network with MTU %s" % config.MTU[-1]
            )

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
        logger.info(
            "Checking logical layer of bridged network %s on host %s"
            % (config.NETWORKS[0], config.HOSTS[0])
        )
        if not checkMTU(
            host=config.HOSTS_IP[0], user=config.HOSTS_USER,
            password=config.HOSTS_PW, mtu=config.MTU[-1], physical_layer=False,
            network=config.NETWORKS[0], nic=config.BOND[0]
        ):
            raise NetworkException(
                "Logical layer: MTU should be %s" % config.MTU[0]
            )

        logger.info(
            "Checking physical layer of bridged network %s on host %s"
            % (config.NETWORKS[0], config.HOSTS[0])
        )
        if not checkMTU(
            host=config.HOSTS_IP[0], user=config.HOSTS_USER,
            password=config.HOSTS_PW, mtu=config.MTU[-1], nic=config.BOND[0]
        ):
            raise NetworkException(
                "Physical layer: MTU should be %s" % config.MTU[0]
            )


@attr(tier=2)
class TestMultiHostCase11(TestMultiHostTestCaseBase):
    """
    Update VM network to be non-VM network when that network is attached to
    the Host bond
    Update non-VM network to be VM network when that network is attached to
    the Host bond
    """
    __test__ = True
    bz = {"1237032": {"engine": ["rest", "sdk", "java"], "version": ["3.6"]}}

    @classmethod
    def setup_class(cls):
        """
        Create and attach network on DC, Cluster and the host
        """

        local_dict = {
            config.NETWORKS[0]: {
                "nic": config.BOND[0], "slaves": [2, 3], "required": "false"
            }
        }

        logger.info("Attach network to DC/Cluster/Host")
        if not createAndAttachNetworkSN(
            data_center=config.DC_NAME[0], cluster=config.CLUSTER_NAME[0],
            host=config.VDS_HOSTS[0], network_dict=local_dict, auto_nics=[0]
        ):
            raise NetworkException("Cannot create and attach network")

    @polarion("RHEVM3-4081")
    def test_update_with_non_vm_nonvm(self):
        """
        Fails due to existing bug - 1082275
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
                config.HOSTS[0]
            )

        logger.info("Update network %s to be VM network", config.NETWORKS[0])
        time.sleep(SLEEP)
        if not updateNetwork(
            True, network=config.NETWORKS[0], data_center=config.DC_NAME[0],
            usages="vm"
        ):
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
        if not isVmHostNetwork(
            host=config.HOSTS_IP[0], user=config.HOSTS_USER,
            password=config.HOSTS_PW, net_name=config.NETWORKS[0]
        ):
            raise NetworkException(
                "Network on host %s was not updated to be VM network" %
                config.HOSTS[0]
            )
