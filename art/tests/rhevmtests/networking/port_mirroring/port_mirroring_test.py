#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Test Port mirroring.
using 2 hosts and 5 VMs
"""

import logging
from art.unittest_lib import attr
from art.unittest_lib import NetworkTest as TestCase
import art.test_handler.exceptions as exceptions
from art.test_handler.tools import polarion  # pylint: disable=E0611
import rhevmtests.networking.config as conf
import art.rhevm_api.tests_lib.high_level.vms as hl_vms
import art.rhevm_api.tests_lib.high_level.networks as hl_networks
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import helper as helper
import art.rhevm_api.tests_lib.low_level.hosts as ll_hosts

logger = logging.getLogger("Port_Mirroring_Cases")

MGMT_IPS = conf.MGMT_IPS
NET1_IPS = conf.NET1_IPS
NET2_IPS = conf.NET2_IPS
VM_NAME = conf.VM_NAME


@attr(tier=2, extra_reqs={'network_hosts': True})
class TestPortMirroringCase01(TestCase):
    """
    Check that mirroring still works after migration
    """
    __test__ = True
    bz = {"1229632": {"engine": None, "version": ["3.6"]}}

    @polarion("RHEVM3-4020")
    def test_a1_migrate_mirroring_vm(self):
        """
        Check that mirroring still works after migrating listening VM to
        another host and back
        """
        for dst_vm in (2, 3):
            helper.send_and_capture_traffic(
                src_vm=MGMT_IPS[1], src_ip=NET1_IPS[1], dst_ip=NET1_IPS[dst_vm]
            )
        logger.info(
            "Migrating %s to %s and back to %s", VM_NAME[0], conf.HOSTS[1],
            conf.HOSTS[0]
        )
        for host in (conf.HOSTS[1], conf.HOSTS[0]):
            if not ll_vms.migrateVm(True, VM_NAME[0], host):
                raise exceptions.NetworkException(
                    "Failed to migrate %s to %s" %
                    (conf.VM_NAME[0], host)
                )
        for dst_vm in (2, 3):
            helper.send_and_capture_traffic(
                src_vm=MGMT_IPS[1], src_ip=NET1_IPS[1], dst_ip=NET1_IPS[dst_vm]
            )

    @polarion("RHEVM3-4017")
    def test_a2_migrate_all_vms(self):
        """
        Check that mirroring still works after migrating all VMs involved to
        another host
        """
        for dst_vm in (2, 3):
            helper.send_and_capture_traffic(
                src_vm=MGMT_IPS[1], src_ip=NET1_IPS[1], dst_ip=NET1_IPS[dst_vm]
            )

        logger.info(
            "Migrating all VMs to %s and check if PM still works ",
            conf.HOSTS[1]
        )
        logger.info("Migrating %s to %s", VM_NAME[:4], conf.HOSTS[1])
        if not hl_vms.migrate_vms(
            vms_list=VM_NAME[:4], src_host=conf.HOSTS[0],
            vm_os_type="rhel", vm_user=conf.VMS_LINUX_USER,
            vm_password=conf.VMS_LINUX_PW, dst_host=conf.HOSTS[1]
        ):
            raise exceptions.NetworkException(
                "Failed to migrate %s to %s" % (VM_NAME[:4], conf.HOSTS[1])
            )
        for dst_vm in (2, 3):
            helper.send_and_capture_traffic(
                src_vm=MGMT_IPS[1], src_ip=NET1_IPS[1], dst_ip=NET1_IPS[dst_vm]
            )

    @classmethod
    def teardown_class(cls):
        """
        Make sure that all the VM's are back on the original host in case
        not all the migrations succeed
        """
        logger.info("Return (migrate) all vms to %s", conf.HOSTS[0])
        helper.return_vms_to_original_host()


@attr(tier=2, extra_reqs={'network_hosts': True})
class TestPortMirroringCase02(TestCase):
    """
    Replace network on the mirrored VM to a non-mirrored network
    """

    __test__ = True

    @polarion("RHEVM3-4010")
    def test_check_mirroring_after_replacing_network(self):
        """
        Replace the network on a mirrored VM with a non-mirrored network and
        check that its traffic is not mirrored anymore.
        """
        helper.send_and_capture_traffic(
            src_vm=MGMT_IPS[3], src_ip=NET1_IPS[3], dst_ip=NET1_IPS[2]
        )
        for vm_name in VM_NAME[2:4]:
            helper.set_port_mirroring(
                vm_name, conf.NIC_NAME[1], conf.VLAN_NETWORKS[1],
                disable_mirroring=True
            )
        helper.send_and_capture_traffic(
            src_vm=MGMT_IPS[3], src_ip=NET1_IPS[3], dst_ip=NET1_IPS[2],
            expect_traffic=False
        )

    @classmethod
    def teardown_class(cls):
        for vm_name in VM_NAME[2:4]:
            helper.set_port_mirroring(
                vm_name, conf.NIC_NAME[1], conf.VLAN_NETWORKS[0],
                disable_mirroring=True, teardown=True
            )


@attr(tier=2, extra_reqs={'network_hosts': True})
class TestPortMirroringCase03(TestCase):
    """
    Check mirroring when listening on multiple networks on the same machine
    """
    __test__ = True

    @polarion("RHEVM3-4014")
    def test_check_pm_one_machine_multiple_networks(self):
        """
        Check that VM1 gets all traffic on both MGMT network and sw1
        """
        helper.send_and_capture_traffic(
            src_vm=MGMT_IPS[1], src_ip=NET1_IPS[1], dst_ip=NET1_IPS[2]
        )
        helper.send_and_capture_traffic(
            src_vm=MGMT_IPS[3], src_ip=MGMT_IPS[3], dst_ip=MGMT_IPS[4],
            nic=conf.VM_NICS[0]
        )


@attr(tier=2, extra_reqs={'network_hosts': True})
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
        helper.set_port_mirroring(
            conf.VM_NAME[1], conf.NIC_NAME[1], conf.VLAN_NETWORKS[0]
        )

    @polarion("RHEVM3-4015")
    def test_a1_check_pm_two_machines_diff_networks(self):
        """
        Check mirroring when it's enabled on different machines on different
        networks (VM1 is listening to mgmt network and VM2 is listening to sw1)
        """
        logger.info(
            "Sending traffic between VM2 and VM3 on MGMT network to make sure "
            "only VM1 gets this traffic."
        )
        helper.send_and_capture_traffic(
            src_vm=MGMT_IPS[1], src_ip=MGMT_IPS[1], dst_ip=MGMT_IPS[2],
            nic=conf.VM_NICS[0]
        )
        helper.send_and_capture_traffic(
            src_vm=MGMT_IPS[1], src_ip=MGMT_IPS[1], dst_ip=MGMT_IPS[2],
            expect_traffic=False, listen_vm=VM_NAME[1]
        )
        logger.info(
            "Sending traffic between VM1 and VM4 on sw1 to make sure only VM2 "
            "gets this traffic."
        )
        helper.send_and_capture_traffic(
            src_vm=MGMT_IPS[0], src_ip=NET1_IPS[0], dst_ip=NET1_IPS[3],
            listen_vm=VM_NAME[1]
        )
        helper.send_and_capture_traffic(
            src_vm=MGMT_IPS[0], src_ip=NET1_IPS[0], dst_ip=NET1_IPS[3],
            expect_traffic=False, nic=conf.VM_NICS[0]
        )

    @polarion("RHEVM3-4006")
    def test_a2_check_pm_two_machines_same_network(self):
        """
        Check port mirroring when two machines are listening to the same
        network (VM1 and VM2 listening on sw1).
        """
        logger.info(
            "Sending traffic between VM3 and VM4 on sw1 to make sure both "
            "VM1 and VM2 get the traffic."
        )
        for vm in conf.VM_NAME[:2]:
            helper.send_and_capture_traffic(
                src_vm=MGMT_IPS[2], src_ip=NET1_IPS[2], dst_ip=NET1_IPS[3],
                listen_vm=vm
            )
        logger.info(
            "Disabling mirroring on VM2 and checking that VM1 still gets the "
            "traffic while VM2 doesn't"
        )
        helper.set_port_mirroring(
            conf.VM_NAME[1], conf.NIC_NAME[1], conf.VLAN_NETWORKS[0],
            disable_mirroring=True
        )
        for vm, expTraffic in zip(conf.VM_NAME[:2], (True, False)):
            helper.send_and_capture_traffic(
                src_vm=MGMT_IPS[2], src_ip=NET1_IPS[2], dst_ip=NET1_IPS[3],
                listen_vm=vm, expect_traffic=expTraffic
            )

    @classmethod
    def teardown_class(cls):
        """
        Make sure port mirroring on nic2 (connected to sw1) on VM2 is disabled
        """
        if ll_vms.getVmNicPortMirroring(
                True, conf.VM_NAME[1], conf.NIC_NAME[1]
        ):
            helper.set_port_mirroring(
                conf.VM_NAME[1], conf.NIC_NAME[1],
                conf.VLAN_NETWORKS[0], disable_mirroring=True, teardown=True
            )


@attr(tier=2, extra_reqs={'network_hosts': True})
class TestPortMirroringCase05(TestCase):
    """
    Restart VDSM on host while mirroring is on
    """
    __test__ = True

    @polarion("RHEVM3-4009")
    def test_restart_vdsmd_on_host(self):
        """
        Check that mirroring still occurs after restarting VDSM on the host
        """
        helper.send_and_capture_traffic(
            src_vm=MGMT_IPS[1], src_ip=NET1_IPS[1], dst_ip=NET1_IPS[2]
        )
        logger.info(
            "Restarting VDSM to check if mirroring still works afterwards"
        )
        if not (
            conf.VDS_HOSTS[0].service("supervdsmd").stop() and
            conf.VDS_HOSTS[0].service("vdsmd").restart()
        ):
            raise exceptions.NetworkException(
                "Failed to restart vdsmd service on %s" % conf.HOSTS[0]
            )
        helper.send_and_capture_traffic(
            src_vm=MGMT_IPS[1], src_ip=NET1_IPS[1], dst_ip=NET1_IPS[2]
        )
        logger.info("Check that %s is UP", conf.HOSTS[0])
        if not ll_hosts.waitForHostsStates(positive=True, names=conf.HOSTS[0]):
            raise exceptions.NetworkException(
                "%s status isn't UP" % conf.HOSTS[0]
            )


@attr(tier=2, extra_reqs={'network_hosts': True})
class TestPortMirroringCase06(TestCase):
    """
    Check that mirroring still occurs after down/UP listening bridge on the
    host
    """
    __test__ = True

    def test_if_up_down_bridge(self):
        """
        Check that mirroring still occurs after down/UP listening bridge on the
        host
        """
        logger.info("Check port mirroring traffic before down/up bridge")
        helper.send_and_capture_traffic(
            src_vm=MGMT_IPS[1], src_ip=NET1_IPS[1], dst_ip=NET1_IPS[2]
        )
        logger.info(
            "Setting down %s on %s", conf.VLAN_NETWORKS[1],
            conf.HOSTS[0]
        )
        if not ll_hosts.ifdownNic(
                host=conf.HOSTS_IP[0], root_password=conf.HOSTS_PW,
                nic=conf.VLAN_NETWORKS[0]
        ):
            raise exceptions.NetworkException(
                "Failed to set down %s on %s" %
                (conf.VLAN_NETWORKS[0], conf.HOSTS[0])
            )
        if not ll_hosts.ifupNic(
                host=conf.HOSTS_IP[0], root_password=conf.HOSTS_PW,
                nic=conf.VLAN_NETWORKS[0]
        ):
            raise exceptions.NetworkException(
                "Failed to set down %s on %s" %
                (conf.VLAN_NETWORKS[0], conf.HOSTS[0])
            )
        logger.info(
            "Checking connectivity between %s to %s to make sure "
            "network is UP", NET1_IPS[1], NET1_IPS[2]
        )
        if not hl_networks.checkICMPConnectivity(
            host=conf.MGMT_IPS[1], user=conf.VMS_LINUX_USER,
            password=conf.VMS_LINUX_PW, ip=NET1_IPS[2]
        ):
            raise exceptions.NetworkException(
                "No connectivity from %s to %s" % (NET1_IPS[1], NET1_IPS[2])
            )
        logger.info("Check port mirroring traffic down/up bridge")
        helper.send_and_capture_traffic(
            src_vm=MGMT_IPS[1], src_ip=NET1_IPS[1], dst_ip=NET1_IPS[2],
            dup_check=False
        )
