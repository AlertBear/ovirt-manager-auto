"""
Testing Topologies feature.
1 DC, 1 Cluster, 1 Hosts and 1 VM will be created for testing.
"""

from networking import config
import logging
from nose.tools import istest
from art.test_handler.tools import tcms
from art.unittest_lib import attr
from art.unittest_lib import NetworkTest as TestCase
from art.rhevm_api.tests_lib.low_level.vms import updateNic, startVm, stopVm, \
    waitForIP
from art.test_handler.exceptions import NetworkException
from art.rhevm_api.tests_lib.high_level.networks import \
    createAndAttachNetworkSN, removeNetFromSetup, checkICMPConnectivity
from art.rhevm_api.tests_lib.low_level.networks import check_bond_mode

logger = logging.getLogger(__name__)

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
        logger.info("Create and attach VLAN network")
        local_dict = {config.VLAN_NETWORKS[0]: {'vlan_id': config.VLAN_ID[0],
                                                'nic': config.HOST_NICS[1],
                                                'required': 'false'}}

        if not createAndAttachNetworkSN(data_center=config.DC_NAME[0],
                                        cluster=config.CLUSTER_NAME[0],
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


@attr(tier=1)
class TopologiesCase02(TestCase):
    """
    Check connectivity to VM with VLAN over BOND mode 1 network
    Check virtIO, e1000 and rtl8139 drivers
    """
    __test__ = len(config.HOST_NICS) > 3

    @classmethod
    def setup_class(cls):
        """
        Create and attach VLAN over BOND mode 1 network to host and VM
        """
        logger.info("Create and attach VLAN over BOND mode 1 network")
        local_dict = {None: {"nic": config.BOND[0],
                             "mode": config.BOND_MODES[1],
                             "slaves": [config.HOST_NICS[2],
                                        config.HOST_NICS[3]]},
                      config.VLAN_NETWORKS[0]: {"nic": config.BOND[0],
                                                "vlan_id": config.VLAN_ID[0],
                                                "required": "false"}}

        if not createAndAttachNetworkSN(data_center=config.DC_NAME[0],
                                        cluster=config.CLUSTER_NAME[0],
                                        host=config.HOSTS[0],
                                        network_dict=local_dict,
                                        auto_nics=[config.HOST_NICS[0]]):
            raise NetworkException("Cannot create and attach network")

        logger.info("Update vNIC to VLAN over BOND mode 1 network on VM")
        if not updateNic(positive=True, vm=config.VM_NAME[0], nic="nic1",
                         network=config.VLAN_NETWORKS[0],
                         vnic_profile=config.VLAN_NETWORKS[0]):
            raise NetworkException("Fail to update vNIC to VLAN over BOND "
                                   "mode 1 network on VM")

        logger.info("Start VM")
        if not startVm(positive=True, vm=config.VM_NAME[0]):
            raise NetworkException("Fail to start VM")

    @istest
    @tcms(4139, 385844)
    def vlan_over_bond_network_01_virtio(self):
        """
        Check connectivity to VLAN over BOND mode 1 network with virtIO driver
        """
        check_vm_connect_and_log(driver=config.NIC_TYPE_VIRTIO, vlan=True,
                                 mode=config.BOND_MODES[1])

    @istest
    @tcms(4139, 386258)
    def vlan_over_bond_network_02_e1000(self):
        """
        Check connectivity to VLAN over BOND mode 1 network with e1000 driver
        """
        if not update_vnic_driver(driver=config.NIC_TYPE_E1000):
            raise NetworkException("Fail to update vNIC to e1000")

        check_vm_connect_and_log(driver=config.NIC_TYPE_E1000, vlan=True,
                                 mode=config.BOND_MODES[1])

    @istest
    @tcms(4139, 386260)
    def vlan_over_bond_network_03_rtl8139(self):
        """
        Check connectivity to VLAN over BOND mode 1 network with rtl8139
        driver
        """
        if not update_vnic_driver(driver=config.NIC_TYPE_RTL8139):
            raise NetworkException("Fail to update vNIC to rtl8139")

        check_vm_connect_and_log(driver=config.NIC_TYPE_RTL8139, vlan=True,
                                 mode=config.BOND_MODES[1])

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


@attr(tier=1)
class TopologiesCase03(TestCase):
    """
    Check connectivity to VM with BOND mode 2 network
    Check virtIO, e1000 and rtl8139 drivers
    """
    __test__ = len(config.HOST_NICS) > 3

    @classmethod
    def setup_class(cls):
        """
        Create and attach BOND mode 2 network to host and VM
        """
        logger.info("Create and attach BOND mode 2 network")
        if not create_and_attach_bond(2):
            raise NetworkException("Cannot create and attach network")

        logger.info("Update vNIC to BOND mode 2 network on VM")
        if not updateNic(positive=True, vm=config.VM_NAME[0], nic="nic1",
                         network=config.NETWORKS[0],
                         vnic_profile=config.NETWORKS[0]):
            raise NetworkException("Fail to update vNIC to BOND mode 2 "
                                   "network on VM")

        logger.info("Start VM")
        if not startVm(positive=True, vm=config.VM_NAME[0]):
            raise NetworkException("Fail to start VM")

    @istest
    @tcms(4139, 385847)
    def bond_network_01_virtio(self):
        """
        Check connectivity to BOND mode 2 network with virtIO driver
        """
        check_vm_connect_and_log(driver=config.NIC_TYPE_VIRTIO,
                                 mode=config.BOND_MODES[2])

    @istest
    @tcms(4139, 386261)
    def bond_network_02_e1000(self):
        """
        Check connectivity to BOND mode 2 network with e1000 driver
        """
        if not update_vnic_driver(driver=config.NIC_TYPE_E1000):
            raise NetworkException("Fail to update vNIC to e1000")

        check_vm_connect_and_log(driver=config.NIC_TYPE_E1000,
                                 mode=config.BOND_MODES[2])

    @istest
    @tcms(4139, 386262)
    def bond_network_03_rtl8139(self):
        """
        Check connectivity to BOND mode 2 network with rtl8139 driver
        """
        if not update_vnic_driver(driver=config.NIC_TYPE_RTL8139):
            raise NetworkException("Fail to update vNIC to rtl8139")

        check_vm_connect_and_log(driver=config.NIC_TYPE_RTL8139,
                                 mode=config.BOND_MODES[2])

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


@attr(tier=1)
class TopologiesCase04(TestCase):
    """
    Check connectivity to VM with BOND mode 4 network
    Check virtIO, e1000 and rtl8139 drivers
    """
    __test__ = len(config.HOST_NICS) > 3

    @classmethod
    def setup_class(cls):
        """
        Create and attach BOND mode 4 network to host and VM
        """
        logger.info("Create and attach BOND mode 4 network")
        if not create_and_attach_bond(4):
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
    @tcms(4139, 385848)
    def bond_network_01_virtio(self):
        """
        Check connectivity to BOND mode 4 network with virtIO driver
        """
        check_vm_connect_and_log(driver=config.NIC_TYPE_VIRTIO,
                                 mode=config.BOND_MODES[4])

    @istest
    @tcms(4139, 386264)
    def bond_network_02_e1000(self):
        """
        Check connectivity to BOND mode 4 network with e1000 driver
        """
        if not update_vnic_driver(driver=config.NIC_TYPE_E1000):
            raise NetworkException("Fail to update vNIC to e1000")

        check_vm_connect_and_log(driver=config.NIC_TYPE_E1000,
                                 mode=config.BOND_MODES[4])

    @istest
    @tcms(4139, 386265)
    def bond_network_03_rtl8139(self):
        """
        Check connectivity to BOND mode 4 network with rtl8139 driver
        """
        if not update_vnic_driver(driver=config.NIC_TYPE_RTL8139):
            raise NetworkException("Fail to update vNIC to rtl8139")

        check_vm_connect_and_log(driver=config.NIC_TYPE_RTL8139,
                                 mode=config.BOND_MODES[4])

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


@attr(tier=1)
class TopologiesCase05(TestCase):
    """
    Check connectivity to VM with BOND mode 3 network
    Check virtIO, e1000 and rtl8139 drivers
    """
    __test__ = len(config.HOST_NICS) > 5

    @classmethod
    def setup_class(cls):
        """
        Create and attach BOND mode 3 network to host and VM
        """
        logger.info("Create and attach BOND mode 3 network")
        if not create_and_attach_bond(3):
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
    @tcms(4139, 385852)
    def bond_network_01_virtio(self):
        """
        Check connectivity to BOND mode 3 network with virtIO driver
        """
        check_vm_connect_and_log(driver=config.NIC_TYPE_VIRTIO,
                                 mode=config.BOND_MODES[3])

    @istest
    @tcms(4139, 386266)
    def bond_network_02_e1000(self):
        """
        Check connectivity to BOND mode 3 network with e1000 driver
        """
        if not update_vnic_driver(driver=config.NIC_TYPE_E1000):
            raise NetworkException("Fail to update vNIC to e1000")

        check_vm_connect_and_log(driver=config.NIC_TYPE_E1000,
                                 mode=config.BOND_MODES[3])

    @istest
    @tcms(4139, 386267)
    def bond_network_03_rtl8139(self):
        """
        Check connectivity to BOND mode 3 network with rtl8139 driver
        """
        if not update_vnic_driver(driver=config.NIC_TYPE_RTL8139):
            raise NetworkException("Fail to update vNIC to rtl8139")

        check_vm_connect_and_log(driver=config.NIC_TYPE_RTL8139,
                                 mode=config.BOND_MODES[3])

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


@attr(tier=1)
class TopologiesCase06(TestCase):
    """
    Check connectivity to BOND mode 0 network
    This is non-VM network test, we check connectivity from host to
    red-vds1.qa.lab.tlv.redhat.com IP 172.16.200.2.
    If this case fail check that red-vds1.qa.lab.tlv.redhat.com is up and eth1
    configured with IP 172.16.200.2
    """
    __test__ = len(config.HOST_NICS) > 3

    @classmethod
    def setup_class(cls):
        """
        Create and attach BOND mode 0 network to host
        """
        logger.info("Create and attach BOND mode 0 network")
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
        if not removeNetFromSetup(host=config.HOSTS[0],
                                  auto_nics=[config.HOST_NICS[0]],
                                  network=[config.NETWORKS[0]]):
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
    __test__ = len(config.HOST_NICS) > 3

    @classmethod
    def setup_class(cls):
        """
        Create and attach BOND mode 5 network to host
        """
        logger.info("Create and attach BOND mode 5 network")
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
        if not removeNetFromSetup(host=config.HOSTS[0],
                                  auto_nics=[config.HOST_NICS[0]],
                                  network=[config.NETWORKS[0]]):
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
    __test__ = len(config.HOST_NICS) > 3

    @classmethod
    def setup_class(cls):
        """
        Create and attach BOND mode 5 network to host
        """
        logger.info("Create and attach BOND mode 6 network")
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
        if not removeNetFromSetup(host=config.HOSTS[0],
                                  auto_nics=[config.HOST_NICS[0]],
                                  network=[config.NETWORKS[0]]):
            raise NetworkException("Cannot remove network from setup")


def update_vnic_driver(driver):
    """
    Description: Update vNIC driver for VM
    author: myakove
    Parameters:
        *  *driver* - driver to update the vNIC (virtio, e1000, rtl8139)
    """
    logger.info("Unplug vNIC")
    if not updateNic(positive=True, vm=config.VM_NAME[0], nic="nic1",
                     plugged="false"):
        return False

    logger.info("Updating vNIC to %s driver", driver)
    if not updateNic(positive=True, vm=config.VM_NAME[0], nic="nic1",
                     interface=driver, plugged="true"):
        return False
    return True


def check_connectivity(vlan=False, vm=True):
    """
    Description: Check connectivity for VM and non-VM networks
    Parameters:
        *  *vlan* - ping from host if True else ping from engine
        *  *vm* - Check connectivity to VM network if True, False for non-VM

    """
    if vm:
        ip = waitForIP(vm=config.VM_NAME[0], timeout=60)[1]
        if not ip:
            return False

        host = config.VDC if not vlan else config.HOSTS[0]
        return checkICMPConnectivity(host, config.HOSTS_USER,
                                     config.HOSTS_PW, ip["ip"])

    else:
        return checkICMPConnectivity(config.HOSTS[0], config.HOSTS_USER,
                                     config.HOSTS_PW, config.DST_HOST_IP)


def create_and_attach_bond(mode):
    """
    Description: Create and attach BOND.
    Parameters:
        *  *mode* - BOND mode.
    """
    usages, address, netmask, bootproto = "vm", None, None, None

    if mode == config.BOND_MODES[4]:
        slaves = [config.HOST_NICS[4], config.HOST_NICS[5]]

    else:
        slaves = [config.HOST_NICS[2], config.HOST_NICS[3]]

        if (
            mode == config.BOND_MODES[0] or mode == config.BOND_MODES[5] or
            mode == config.BOND_MODES[6]
        ):
            usages = ""
            address = [config.ADDR_AND_MASK[0]]
            netmask = [config.ADDR_AND_MASK[1]]
            bootproto = "static"

    local_dict = {config.NETWORKS[0]: {"nic": config.BOND[0],
                                       "mode": int(mode),
                                       "slaves": slaves,
                                       "usages": usages,
                                       "address": address,
                                       "netmask": netmask,
                                       "bootproto": bootproto,
                                       "required": False}}

    if not createAndAttachNetworkSN(data_center=config.DC_NAME[0],
                                    cluster=config.CLUSTER_NAME[0],
                                    host=config.HOSTS[0],
                                    network_dict=local_dict,
                                    auto_nics=[config.HOST_NICS[0]]):
        return False

    if not check_bond_mode(host=config.HOSTS[0], user=config.HOSTS_USER,
                           password=config.HOSTS_PW, interface=config.BOND[0],
                           mode=mode):
        logger.error("BOND mode should be %s but it's not", mode)
        return False
    return True


def check_connectivity_log(driver=None, mode=None, info=False, error=False,
                           vlan=False):
    """
    Description: Generate string for info/errors.
    Parameters:
        *  *mode* - BOND mode.
        *  *driver* - driver of the interface
        *  *info* - Info string if True
        *  *error* - raise string if True
        *  *vlan* - vlan network in string if True
    """
    output = "info or error not sent, nothing to do"
    interface = "BOND mode %s" % mode if mode else ""
    vlan_info = "VLAN over" if vlan else ""
    driver_info = "with %s driver" % driver if driver else ""
    if info:
        output = (
            "Check connectivity to %s %s network %s"
            % (vlan_info, interface, driver_info)
        )

    if error:
        output = (
            "Connectivity failed to %s %s network %s"
            % (vlan_info, interface, driver_info)
        )

    return output


def check_vm_connect_and_log(driver=None, mode=None, vlan=False, vm=True):
    """
    Description: Check VM connectivity with logger info and raise error if
    fail
    Parameters:
        *  *mode* - BOND mode.
        *  *driver* - driver of the interface
        *  *vlan* - ping from host if True else ping from engine
        *  *vm* - Check connectivity to VM network if True, False for non-VM
    """
    logger.info(check_connectivity_log(mode=mode, driver=driver, info=True,
                                       vlan=vlan))

    if not check_connectivity(vlan=vlan, vm=vm):
        raise NetworkException(check_connectivity_log(mode=mode, driver=driver,
                                                      error=True, vlan=vlan))
    return True
