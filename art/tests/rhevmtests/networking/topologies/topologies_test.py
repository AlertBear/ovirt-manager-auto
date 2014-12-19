"""
Testing Topologies feature.
1 DC, 1 Cluster, 1 Hosts and 1 VM will be created for testing.
"""
import logging
from nose.tools import istest
from rhevmtests.networking import config
from art.test_handler.tools import tcms  # pylint: disable=E0611
from art.unittest_lib import attr
from art.unittest_lib import NetworkTest as TestCase
from art.rhevm_api.tests_lib.high_level.vms import start_vm_on_specific_host
from art.rhevm_api.tests_lib.low_level.vms import (
    updateNic, startVm, stopVm
)
from art.test_handler.exceptions import NetworkException
from art.rhevm_api.tests_lib.high_level.networks import (
    createAndAttachNetworkSN, remove_net_from_setup
)
from rhevmtests.networking.topologies.helper import(
    check_vm_connect_and_log, update_vnic_driver, create_and_attach_bond
)

logger = logging.getLogger("topologies_cases")

########################################################################

########################################################################
#                             Test Cases                               #
########################################################################


@attr(tier=1)
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
        logger.info("Create and attach VLAN network %s",
                    config.VLAN_NETWORKS[0])
        local_dict = {config.VLAN_NETWORKS[0]: {"vlan_id": config.VLAN_ID[0],
                                                "nic": 1,
                                                "required": False}}

        if not createAndAttachNetworkSN(
            data_center=config.DC_NAME[0], cluster=config.CLUSTER_NAME[0],
            host=config.VDS_HOSTS[0], network_dict=local_dict, auto_nics=[0, 1]
        ):
            raise NetworkException(
                "Cannot create and attach network %s", config.VLAN_NETWORKS[0]
            )

        logger.info("Update vNIC to VLAN network on VM %s", config.VM_NAME[0])
        if not updateNic(
            positive=True, vm=config.VM_NAME[0], nic="nic1",
            network=config.VLAN_NETWORKS[0],
            vnic_profile=config.VLAN_NETWORKS[0]
        ):
            raise NetworkException(
                "Fail to update vNIC to VLAN network on VM %s" %
                config.VM_NAME[0]
            )

        if not start_vm_on_specific_host(
            vm=config.VM_NAME[0], host=config.HOSTS[0]
        ):
            raise NetworkException(
                "Cannot start VM %s on host %s" %
                (config.VM_NAME[0], config.HOSTS[0])
            )

    @istest
    @tcms(4139, 385829)
    def vlan_network_01_virtio(self):
        """
        Check connectivity to VLAN network with virtIO driver
        """
        check_vm_connect_and_log(driver=config.NIC_TYPE_VIRTIO, vlan=True)

    @istest
    @tcms(4139, 385831)
    def vlan_network_02_e1000(self):
        """
        Check connectivity to VLAN network with e1000 driver
        """
        logger.info("Updating vNIC driver to e1000")
        if not update_vnic_driver(driver=config.NIC_TYPE_E1000):
            raise NetworkException("Fail to update vNIC to e1000")

        check_vm_connect_and_log(driver=config.NIC_TYPE_E1000, vlan=True)

    @istest
    @tcms(4139, 385834)
    def vlan_network_03_rtl8139(self):
        """
        Check connectivity to VLAN network with rtl8139 driver
        """
        logger.info("Updating vNIC driver to rtl8139")
        if not update_vnic_driver(driver=config.NIC_TYPE_RTL8139):
            raise NetworkException("Fail to update vNIC to rtl8139")

        check_vm_connect_and_log(driver=config.NIC_TYPE_RTL8139, vlan=True)

    @classmethod
    def teardown_class(cls):
        """
        Remove network from setup
        """
        logger.info("Stop VM %s", config.VM_NAME[0])
        if not stopVm(positive=True, vm=config.VM_NAME[0]):
            raise NetworkException("Fail to stop VM %s" % config.VM_NAME[0])

        logger.info("Update vNIC to RHEVM network on VM %s", config.VM_NAME[0])
        if not updateNic(
            positive=True, vm=config.VM_NAME[0], nic="nic1",
            network=config.MGMT_BRIDGE, interface="virtio",
            vnic_profile=config.MGMT_BRIDGE
        ):
            raise NetworkException(
                "Fail to update vNIC to RHEVM network on VM %s" %
                config.VM_NAME[0]
            )

        logger.info("Remove network %s from setup", config.VLAN_NETWORKS[0])
        if not remove_net_from_setup(
            host=config.VDS_HOSTS[0], auto_nics=[0],
            network=[config.VLAN_NETWORKS[0]]
        ):
            raise NetworkException(
                "Cannot remove network %s from setup" %
                config.VLAN_NETWORKS[0]
            )


##############################################################################


@attr(tier=1)
class TopologiesCase02(TestCase):
    """
    Check connectivity to VM with VLAN over BOND mode 1 network
    Check virtIO, e1000 and rtl8139 drivers
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Create and attach VLAN over BOND mode 1 network to host and VM
        """
        logger.info("Create and attach VLAN over BOND mode 1 network")
        local_dict = {None: {"nic": config.BOND[0],
                             "mode": config.BOND_MODES[1],
                             "slaves": [2, 3]},
                      config.VLAN_NETWORKS[0]: {"nic": config.BOND[0],
                                                "vlan_id": config.VLAN_ID[0],
                                                "required": False}}

        if not createAndAttachNetworkSN(
            data_center=config.DC_NAME[0], cluster=config.CLUSTER_NAME[0],
            host=config.VDS_HOSTS[0], network_dict=local_dict, auto_nics=[0]
        ):
            raise NetworkException("Cannot create and attach network")

        logger.info("Update vNIC to VLAN over BOND mode 1 network on VM")
        if not updateNic(
            positive=True, vm=config.VM_NAME[0], nic="nic1",
            network=config.VLAN_NETWORKS[0],
            vnic_profile=config.VLAN_NETWORKS[0]
        ):
            raise NetworkException(
                "Fail to update vNIC to VLAN over BOND mode 1 network on VM"
            )

        if not start_vm_on_specific_host(
            vm=config.VM_NAME[0], host=config.HOSTS[0]
        ):
            raise NetworkException(
                "Cannot start VM %s on host %s" %
                (config.VM_NAME[0], config.HOSTS[0])
            )

    @istest
    @tcms(4139, 385844)
    def vlan_over_bond_network_01_virtio(self):
        """
        Check connectivity to VLAN over BOND mode 1 network with virtIO driver
        """
        check_vm_connect_and_log(
            driver=config.NIC_TYPE_VIRTIO, vlan=True,
            mode=config.BOND_MODES[1]
        )

    @istest
    @tcms(4139, 386258)
    def vlan_over_bond_network_02_e1000(self):
        """
        Check connectivity to VLAN over BOND mode 1 network with e1000 driver
        """
        if not update_vnic_driver(driver=config.NIC_TYPE_E1000):
            raise NetworkException("Fail to update vNIC to e1000")

        check_vm_connect_and_log(
            driver=config.NIC_TYPE_E1000, vlan=True,
            mode=config.BOND_MODES[1]
        )

    @istest
    @tcms(4139, 386260)
    def vlan_over_bond_network_03_rtl8139(self):
        """
        Check connectivity to VLAN over BOND mode 1 network with rtl8139
        driver
        """
        if not update_vnic_driver(driver=config.NIC_TYPE_RTL8139):
            raise NetworkException("Fail to update vNIC to rtl8139")

        check_vm_connect_and_log(
            driver=config.NIC_TYPE_RTL8139, vlan=True,
            mode=config.BOND_MODES[1]
        )

    @classmethod
    def teardown_class(cls):
        """
        Remove network from setup
        """
        logger.info("Stop VM %s", config.VM_NAME[0])
        if not stopVm(positive=True, vm=config.VM_NAME[0]):
            raise NetworkException("Failed to stop VM %s" % config.VM_NAME[0])

        logger.info("Update vNIC to RHEVM network on VM")
        if not updateNic(
            positive=True, vm=config.VM_NAME[0], nic="nic1",
            network=config.MGMT_BRIDGE, interface="virtio",
            vnic_profile=config.MGMT_BRIDGE
        ):
            raise NetworkException(
                "Fail to update vNIC to RHEVM network on VM"
            )

        logger.info("Remove network from setup")
        if not remove_net_from_setup(
            host=config.VDS_HOSTS[0], auto_nics=[0],
            network=[config.VLAN_NETWORKS[0]]
        ):
            raise NetworkException("Cannot remove network from setup")


##############################################################################


@attr(tier=1)
class TopologiesCase03(TestCase):
    """
    Check connectivity to VM with BOND mode 2 network
    Check virtIO, e1000 and rtl8139 drivers
    """
    # bond mode 2 requires switch side configuration to work properly ! ! !

    __test__ = False  # disabled until we deal with NIC plugin for 6 NICs hosts

    @classmethod
    def setup_class(cls):
        """
        Create and attach BOND mode 2 network to host and VM
        """
        logger.info("Create and attach BOND mode 2 network")
        if not create_and_attach_bond(2):
            raise NetworkException("Cannot create and attach network")

        logger.info("Update vNIC to BOND mode 2 network on VM")
        if not updateNic(
            positive=True, vm=config.VM_NAME[0], nic="nic1",
            network=config.NETWORKS[0], vnic_profile=config.NETWORKS[0]
        ):
            raise NetworkException(
                "Fail to update vNIC to BOND mode 2 network on VM"
            )

        if not start_vm_on_specific_host(
            vm=config.VM_NAME[0], host=config.HOSTS[0]
        ):
            raise NetworkException(
                "Cannot start VM %s on host %s" %
                (config.VM_NAME[0], config.HOSTS[0])
            )

    @istest
    @tcms(4139, 385847)
    def bond_network_01_virtio(self):
        """
        Check connectivity to BOND mode 2 network with virtIO driver
        """
        check_vm_connect_and_log(
            driver=config.NIC_TYPE_VIRTIO, mode=config.BOND_MODES[2]
        )

    @istest
    @tcms(4139, 386261)
    def bond_network_02_e1000(self):
        """
        Check connectivity to BOND mode 2 network with e1000 driver
        """
        if not update_vnic_driver(driver=config.NIC_TYPE_E1000):
            raise NetworkException("Fail to update vNIC to e1000")

        check_vm_connect_and_log(
            driver=config.NIC_TYPE_E1000, mode=config.BOND_MODES[2]
        )

    @istest
    @tcms(4139, 386262)
    def bond_network_03_rtl8139(self):
        """
        Check connectivity to BOND mode 2 network with rtl8139 driver
        """
        if not update_vnic_driver(driver=config.NIC_TYPE_RTL8139):
            raise NetworkException("Fail to update vNIC to rtl8139")

        check_vm_connect_and_log(
            driver=config.NIC_TYPE_RTL8139, mode=config.BOND_MODES[2]
        )

    @classmethod
    def teardown_class(cls):
        """
        Remove network from setup
        """
        logger.info("Stop VM %s", config.VM_NAME[0])
        if not stopVm(positive=True, vm=config.VM_NAME[0]):
            raise NetworkException("Fail to stop VM %s" % config.VM_NAME[0])

        logger.info("Update vNIC to RHEVM network on VM %s", config.VM_NAME[0])
        if not updateNic(
            positive=True, vm=config.VM_NAME[0], nic="nic1",
            network=config.MGMT_BRIDGE, interface="virtio",
            vnic_profile=config.MGMT_BRIDGE
        ):
            raise NetworkException(
                "Fail to update vNIC to RHEVM network on VM %s" %
                config.VM_NAME[0]
            )

        logger.info("Remove network %s from setup", config.NETWORKS[0])
        if not remove_net_from_setup(
            host=config.VDS_HOSTS[0], auto_nics=[0],
            network=[config.NETWORKS[0]]
        ):
            raise NetworkException(
                "Cannot remove network %s from setup" % config.NETWORKS[0]
            )


@attr(tier=1)
class TopologiesCase04(TestCase):
    """
    Check connectivity to VM with BOND mode 4 network
    Check virtIO, e1000 and rtl8139 drivers
    TODO: bond mode 4 requires switch side configuration disabling case until
     we have swith side support on all hosts including GE
    """
    __test__ = False

    @classmethod
    def setup_class(cls):
        """
        Create and attach BOND mode 4 network to host and VM
        """
        logger.info("Create and attach BOND mode 4 network")
        if not create_and_attach_bond(4):
            raise NetworkException("Cannot create and attach network")

        logger.info("Update vNIC to BOND network on VM")
        if not updateNic(
            positive=True, vm=config.VM_NAME[0], nic="nic1",
            network=config.NETWORKS[0], vnic_profile=config.NETWORKS[0]
        ):
            raise NetworkException(
                "Fail to update vNIC to BOND network on VM"
            )

        logger.info("Start VM %s", config.VM_NAME[0])
        if not startVm(positive=True, vm=config.VM_NAME[0]):
            raise NetworkException("Fail to start VM %s" % config.VM_NAME[0])

    @istest
    @tcms(4139, 385848)
    def bond_network_01_virtio(self):
        """
        Check connectivity to BOND mode 4 network with virtIO driver
        """
        check_vm_connect_and_log(
            driver=config.NIC_TYPE_VIRTIO, mode=config.BOND_MODES[4]
        )

    @istest
    @tcms(4139, 386264)
    def bond_network_02_e1000(self):
        """
        Check connectivity to BOND mode 4 network with e1000 driver
        """
        if not update_vnic_driver(driver=config.NIC_TYPE_E1000):
            raise NetworkException("Fail to update vNIC to e1000")

        check_vm_connect_and_log(
            driver=config.NIC_TYPE_E1000, mode=config.BOND_MODES[4]
        )

    @istest
    @tcms(4139, 386265)
    def bond_network_03_rtl8139(self):
        """
        Check connectivity to BOND mode 4 network with rtl8139 driver
        """
        if not update_vnic_driver(driver=config.NIC_TYPE_RTL8139):
            raise NetworkException("Fail to update vNIC to rtl8139")

        check_vm_connect_and_log(
            driver=config.NIC_TYPE_RTL8139, mode=config.BOND_MODES[4]
        )

    @classmethod
    def teardown_class(cls):
        """
        Remove network from setup
        """
        logger.info("Stop VM %s", config.VM_NAME[0])
        if not stopVm(positive=True, vm=config.VM_NAME[0]):
            raise NetworkException("Failed to stop VM %s" % config.VM_NAME[0])

        logger.info("Update vNIC to RHEVM network on VM")
        if not updateNic(
            positive=True, vm=config.VM_NAME[0], nic="nic1",
            network=config.MGMT_BRIDGE, interface="virtio",
            vnic_profile=config.MGMT_BRIDGE
        ):
            raise NetworkException(
                "Fail to update vNIC to RHEVM network on VM"
            )

        logger.info("Remove network from setup")
        if not remove_net_from_setup(
            host=config.VDS_HOSTS[0], auto_nics=[0],
            network=[config.NETWORKS[0]]
        ):
            raise NetworkException("Cannot remove network from setup")


@attr(tier=1)
class TopologiesCase05(TestCase):
    """
    Check connectivity to BOND mode 3 network
    This is non-VM network test, we check connectivity from host to
    red-vds1.qa.lab.tlv.redhat.com IP 172.16.200.2.
    If this case fail check that red-vds1.qa.lab.tlv.redhat.com is up and eth1
    configured with IP 172.16.200.2
    !!! NOTE: bond mode 3 is officially not supported with VM networks!!!
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Create and attach BOND mode 3 network to host
        """
        logger.info(
            "Create and attach BOND mode %s network", config.BOND_MODES[3]
        )
        if not create_and_attach_bond(config.BOND_MODES[3]):
            raise NetworkException("Cannot create and attach network")

    @istest
    @tcms(4139, 385855)
    def bond_non_vm_network(self):
        """
        Check connectivity to BOND mode 3 network
        """
        check_vm_connect_and_log(mode=config.BOND_MODES[3], vm=False)

    @classmethod
    def teardown_class(cls):
        """
        Remove network from setup
        """
        logger.info("Remove network from setup")
        if not remove_net_from_setup(
            host=config.VDS_HOSTS[0], auto_nics=[0],
            network=[config.NETWORKS[0]]
        ):
            raise NetworkException("Cannot remove network from setup")


@attr(tier=1)
class TopologiesCase06(TestCase):
    """
    Check connectivity to BOND mode 0 network
    This is non-VM network test, we check connectivity from host to
    red-vds1.qa.lab.tlv.redhat.com IP 172.16.200.2.
    If this case fail check that red-vds1.qa.lab.tlv.redhat.com is up and eth1
    configured with IP 172.16.200.2
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Create and attach BOND mode 0 network to host
        """
        logger.info(
            "Create and attach BOND mode %s network", config.BOND_MODES[0]
        )
        if not create_and_attach_bond(config.BOND_MODES[0]):
            raise NetworkException("Cannot create and attach network")

    @istest
    @tcms(4139, 385855)
    def bond_non_vm_network(self):
        """
        Check connectivity to BOND mode 0 network
        """
        check_vm_connect_and_log(mode=config.BOND_MODES[0], vm=False)

    @classmethod
    def teardown_class(cls):
        """
        Remove network from setup
        """
        logger.info("Remove network from setup")
        if not remove_net_from_setup(
            host=config.VDS_HOSTS[0], auto_nics=[0],
            network=[config.NETWORKS[0]]
        ):
            raise NetworkException("Cannot remove network from setup")


@attr(tier=1)
class TopologiesCase07(TestCase):
    """
    Check connectivity to BOND mode 5 network
    This is non-VM network test, we check connectivity from host to
    red-vds1.qa.lab.tlv.redhat.com IP 172.16.200.2.
    If this case fail check that red-vds1.qa.lab.tlv.redhat.com is up and eth1
    configured with IP 172.16.200.2
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Create and attach BOND mode 5 network to host
        """
        logger.info(
            "Create and attach BOND mode %s network", config.BOND_MODES[5]
        )
        if not create_and_attach_bond(config.BOND_MODES[5]):
            raise NetworkException("Cannot create and attach network")

    @istest
    @tcms(4139, 385856)
    def bond_non_vm_network(self):
        """
        Check connectivity to BOND mode 5 network
        """
        check_vm_connect_and_log(mode=config.BOND_MODES[5], vm=False)

    @classmethod
    def teardown_class(cls):
        """
        Remove network from setup
        """
        logger.info("Remove network from setup")
        if not remove_net_from_setup(
            host=config.VDS_HOSTS[0], auto_nics=[0],
            network=[config.NETWORKS[0]]
        ):
            raise NetworkException("Cannot remove network from setup")


@attr(tier=1)
class TopologiesCase08(TestCase):
    """
    Check connectivity to BOND mode 6 network
    This is non-VM network test, we check connectivity from host to
    red-vds1.qa.lab.tlv.redhat.com IP 172.16.200.2.
    If this case fail check that red-vds1.qa.lab.tlv.redhat.com is up and eth1
    configured with IP 172.16.200.2
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Create and attach BOND mode 6 network to host
        """
        logger.info(
            "Create and attach BOND mode %s network", config.BOND_MODES[6]
        )
        if not create_and_attach_bond(config.BOND_MODES[6]):
            raise NetworkException("Cannot create and attach network")

    @istest
    @tcms(4139, 385857)
    def bond_non_vm_network(self):
        """
        Check connectivity to BOND mode 6 network
        """
        check_vm_connect_and_log(mode=config.BOND_MODES[6], vm=False)

    @classmethod
    def teardown_class(cls):
        """
        Remove network from setup
        """
        logger.info("Remove network from setup")
        if not remove_net_from_setup(
            host=config.VDS_HOSTS[0], auto_nics=[0],
            network=[config.NETWORKS[0]]
        ):
            raise NetworkException("Cannot remove network from setup")
