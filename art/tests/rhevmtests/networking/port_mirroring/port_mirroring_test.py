#! /usr/bin/python
"""
Test Port mirroring.
using 2 hosts and 5 VMs
"""

from art.rhevm_api.tests_lib.high_level.networks import checkICMPConnectivity
from art.rhevm_api.tests_lib.low_level.hosts import(
    waitForHostsStates, ifdownNic, ifupNic
)
from art.unittest_lib import attr
from art.unittest_lib import NetworkTest as TestCase
import logging
from art.test_handler.exceptions import NetworkException
from art.test_handler.tools import tcms  # pylint: disable=E0611
from art.rhevm_api.tests_lib.low_level.vms import (
    migrateVm, getVmNicPortMirroring,
)
from utils import (
    send_and_capture_traffic, set_port_mirroring, return_vms_to_original_host
)
from rhevmtests.networking import config

logger = logging.getLogger("Port_Mirroring_Cases")

MGMT_IPS = config.MGMT_IPS
NET1_IPS = config.NET1_IPS
NET2_IPS = config.NET2_IPS
VM_NAME = config.VM_NAME

# #######################################################################

########################################################################
#                             Test Cases                               #
########################################################################


@attr(tier=1)
class TestPortMirroringCase01(TestCase):
    """
    Check that mirroring still works after migration
    """
    # BUG: https://bugzilla.redhat.com/show_bug.cgi?id=1159647
    # Testing if bug is not reproduced anymore
    __test__ = True

    @tcms(10475, 302095)
    def test_a1_migrate_mirroring_vm(self):
        """
        Check that mirroring still works after migrating listening VM to
        another host and back
        """
        for dstVM in (2, 3):
            send_and_capture_traffic(
                srcVM=MGMT_IPS[1], srcIP=NET1_IPS[1], dstIP=NET1_IPS[dstVM]
            )

        logger.info(
            "Migrating %s to %s and back to %s", VM_NAME[0], config.HOSTS[1],
            config.HOSTS[0]
        )
        if not migrateVm(True, VM_NAME[0], config.HOSTS[1]):
            raise NetworkException(
                "Failed to migrate %s to %s" %
                (config.VM_NAME[0], config.HOSTS[1])
            )
        if not migrateVm(True, VM_NAME[0], config.HOSTS[0]):
            raise NetworkException(
                "Failed to migrate %s back to %s" %
                (config.VM_NAME[0], config.HOSTS[0])
            )

        for dstVM in (2, 3):
            send_and_capture_traffic(
                srcVM=MGMT_IPS[1], srcIP=NET1_IPS[1], dstIP=NET1_IPS[dstVM]
            )

    @tcms(10475, 302098)
    def test_a2_migrate_all_vms(self):
        """
        Check that mirroring still works after migrating all VM's involved to
        anther host
        """
        for dstVM in (2, 3):
            send_and_capture_traffic(
                srcVM=MGMT_IPS[1], srcIP=NET1_IPS[1], dstIP=NET1_IPS[dstVM]
            )

        logger.info(
            "Migrating all VMs to %s and check if PM still works "
            "afterward", config.HOSTS[1]
        )

        for vmName in VM_NAME[:4]:
            logger.info("Migrating %s to %s", vmName, config.HOSTS[1])
            if not migrateVm(True, vmName, config.HOSTS[1]):
                raise NetworkException(
                    "Failed to migrate %s to %s" % (vmName, config.HOSTS[1])
                )

        for dstVM in (2, 3):
            send_and_capture_traffic(
                srcVM=MGMT_IPS[1], srcIP=NET1_IPS[1], dstIP=NET1_IPS[dstVM]
            )

        logger.info("Migrating VMs back to %s", config.HOSTS[0])
        for vmName in VM_NAME[:4]:
            logger.info("Migrating %s back to %s", vmName, config.HOSTS[0])
            if not migrateVm(True, vmName, config.HOSTS[0]):
                raise NetworkException(
                    "Failed to migrate %s to %s" % (vmName, config.HOSTS[0])
                )

    @classmethod
    def teardown_class(cls):
        """
        Make sure that all the VM's are back on the original host in case
        not all the migrations succeed
        """
        logger.info("Return (migrate) all vms to %s", config.HOSTS[0])
        return_vms_to_original_host()


@attr(tier=1)
class TestPortMirroringCase02(TestCase):
    """
    Replace network on the mirrored VM to a non-mirrored network
    """

    __test__ = True

    @tcms(10475, 302105)
    def test_check_mirroring_after_replacing_network(self):
        """
        Replace the network on a mirrored VM with a non-mirrored network and
        check that its traffic is not mirrored anymore.
        """
        send_and_capture_traffic(
            srcVM=MGMT_IPS[3], srcIP=NET1_IPS[3], dstIP=NET1_IPS[2]
        )

        for vm_name in VM_NAME[2:4]:
            set_port_mirroring(
                vm_name, config.NIC_NAME[1], config.VLAN_NETWORKS[1],
                disableMirroring=True
            )

        send_and_capture_traffic(
            srcVM=MGMT_IPS[3], srcIP=NET1_IPS[3], dstIP=NET1_IPS[2],
            expectTraffic=False
        )

    @classmethod
    def teardown_class(cls):
        for vm_name in VM_NAME[2:4]:
            set_port_mirroring(
                vm_name, config.NIC_NAME[1], config.VLAN_NETWORKS[0],
                disableMirroring=True
            )

########################################################################

########################################################################


########################################################################

########################################################################

@attr(tier=1)
class TestPortMirroringCase03(TestCase):
    """
    Check mirroring when listening on multiple networks on the same machine
    """
    __test__ = True

    @tcms(10475, 302101)
    def test_check_pm_one_machine_multiple_networks(self):
        """
        Check that VM1 gets all traffic on both MGMT network and sw1
        """
        send_and_capture_traffic(
            srcVM=MGMT_IPS[1], srcIP=NET1_IPS[1], dstIP=NET1_IPS[2]
        )
        send_and_capture_traffic(
            srcVM=MGMT_IPS[3], srcIP=MGMT_IPS[3], dstIP=MGMT_IPS[4],
            nic=config.VM_NICS[0]
        )


########################################################################

########################################################################
@attr(tier=1)
class TestPortMirroringCase04(TestCase):
    """
    Check port mirroring when it's enabled on multiple machines.
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Enable port mirroring on nic2 (connected to sw1) on VM2.
        """
        set_port_mirroring(
            config.VM_NAME[1], config.NIC_NAME[1], config.VLAN_NETWORKS[0]
        )

    @tcms(10475, 302100)
    def test_a1_check_pm_two_machines_diff_networks(self):
        """
        Check mirroring when it's enabled on different machines on different
        networks (VM1 is listening to mgmt network and VM2 is listening to sw1)
        """
        logger.info(
            "Sending traffic between VM2 and VM3 on MGMT network to make sure "
            "only VM1 gets this traffic."
        )
        send_and_capture_traffic(
            srcVM=MGMT_IPS[1], srcIP=MGMT_IPS[1], dstIP=MGMT_IPS[2],
            nic='eth0'
        )

        send_and_capture_traffic(
            srcVM=MGMT_IPS[1], srcIP=MGMT_IPS[1], dstIP=MGMT_IPS[2],
            listenVM=VM_NAME[1], expectTraffic=False
        )

        logger.info(
            "Sending traffic between VM1 and VM4 on sw1 to make sure only VM2 "
            "gets this traffic."
        )
        send_and_capture_traffic(
            srcVM=MGMT_IPS[0], srcIP=NET1_IPS[0], dstIP=NET1_IPS[3],
            listenVM=VM_NAME[1]
        )

        send_and_capture_traffic(
            srcVM=MGMT_IPS[0], srcIP=NET1_IPS[0], dstIP=NET1_IPS[3],
            nic='eth0', expectTraffic=False
        )

    @tcms(10475, 302093)
    def test_a2_check_pm_two_machines_same_network(self):
        """
        Check port mirroring when two machines are listening to the same
        network (VM1 and VM2 listening on sw1).
        """
        logger.info(
            "Sending traffic between VM3 and VM4 on sw1 to make sure both "
            "VM1 and VM2 get the traffic."
        )
        for vm in config.VM_NAME[:2]:
            send_and_capture_traffic(
                srcVM=MGMT_IPS[2], srcIP=NET1_IPS[2], dstIP=NET1_IPS[3],
                listenVM=vm
            )

        logger.info(
            "Disabling mirroring on VM2 and checking that VM1 still gets the "
            "traffic while VM2 doesn't"
        )
        set_port_mirroring(
            config.VM_NAME[1], config.NIC_NAME[1], config.VLAN_NETWORKS[0],
            disableMirroring=True
        )

        for vm, expTraffic in zip(config.VM_NAME[:2], (True, False)):
            send_and_capture_traffic(
                srcVM=MGMT_IPS[2], srcIP=NET1_IPS[2], dstIP=NET1_IPS[3],
                listenVM=vm, expectTraffic=expTraffic
            )

    @classmethod
    def teardown_class(cls):
        """
        Make sure port mirroring on nic2 (connected to sw1) on VM2 is disabled
        """
        if getVmNicPortMirroring(
                True, config.VM_NAME[1], config.NIC_NAME[1]
        ):
            set_port_mirroring(
                config.VM_NAME[1], config.NIC_NAME[1],
                config.VLAN_NETWORKS[0], disableMirroring=True
            )


########################################################################

########################################################################
@attr(tier=1)
class TestPortMirroringCase05(TestCase):
    """
    Restart VDSM on host while mirroring is on
    """
    __test__ = True

    @tcms(10475, 302106)
    def test_restart_vdsmd_on_host(self):
        """
        Check that mirroring still occurs after restarting VDSM on the host
        """
        send_and_capture_traffic(
            srcVM=MGMT_IPS[1], srcIP=NET1_IPS[1], dstIP=NET1_IPS[2]
        )
        logger.info(
            "Restarting VDSM to check if mirroring still works afterwards"
        )
        if not (
            config.VDS_HOSTS[0].service("supervdsmd").stop() and
            config.VDS_HOSTS[0].service("vdsmd").restart()
        ):
            raise NetworkException(
                "Failed to restart vdsmd service on %s" % config.HOSTS[0]
            )

        send_and_capture_traffic(
            srcVM=MGMT_IPS[1], srcIP=NET1_IPS[1], dstIP=NET1_IPS[2]
        )

        logger.info("Check that %s is UP", config.HOSTS[0])
        if not waitForHostsStates(positive=True, names=config.HOSTS[0]):
            logger.error("%s status isn't UP", config.HOSTS[0])


@attr(tier=1)
class TestPortMirroringCase06(TestCase):
    """
    Check that mirroring still occurs after down/UP listening bridge on the
    host
    """
    __test__ = True

    def test_restart_networking_on_host(self):
        """
        Check that mirroring still occurs after down/UP listening bridge on the
        host
        """
        logger.info("Check port mirroring traffic before down/up bridge")
        send_and_capture_traffic(
            srcVM=MGMT_IPS[1], srcIP=NET1_IPS[1], dstIP=NET1_IPS[2]
        )

        logger.info(
            "Setting down %s on %s", config.VLAN_NETWORKS[1],
            config.HOSTS[0]
        )
        if not ifdownNic(
                host=config.HOSTS_IP[0], root_password=config.HOSTS_PW,
                nic=config.VLAN_NETWORKS[0]
        ):
            raise NetworkException(
                "Failed to set down %s on %s" % (
                    config.VLAN_NETWORKS[0], config.HOSTS[0])
            )

        if not ifupNic(
                host=config.HOSTS_IP[0], root_password=config.HOSTS_PW,
                nic=config.VLAN_NETWORKS[0]
        ):
            raise NetworkException(
                "Failed to set down %s on %s" % (
                    config.VLAN_NETWORKS[0], config.HOSTS[0])
            )

        logger.info(
            "Checking connectivity between %s to %s to make sure "
            "network is UP", NET1_IPS[1], NET1_IPS[2]
        )
        if not checkICMPConnectivity(
            host=config.MGMT_IPS[1], user=config.VMS_LINUX_USER,
            password=config.VMS_LINUX_PW, ip=NET1_IPS[2]
        ):
            raise NetworkException(
                "No connectivity from %s to %s" % (NET1_IPS[1], NET1_IPS[2])
            )

        logger.info("Check port mirroring traffic down/up bridge")
        send_and_capture_traffic(
            srcVM=MGMT_IPS[1], srcIP=NET1_IPS[1], dstIP=NET1_IPS[2],
            dupCheck=False
        )
