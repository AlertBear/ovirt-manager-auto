#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Test Port mirroring.
using 2 hosts and 5 VMs
"""

import logging

import pytest

import art.rhevm_api.tests_lib.high_level.vms as hl_vms
import art.rhevm_api.tests_lib.low_level.hosts as ll_hosts
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import helper
import rhevmtests.helpers as global_helper
import rhevmtests.networking.config as conf
import rhevmtests.networking.helper as network_helper
from art.core_api import apis_utils
from art.test_handler.tools import polarion
from art.unittest_lib import NetworkTest
from art.unittest_lib import attr
from fixtures import (
    port_mirroring_prepare_setup, case01_fixture, case02_fixture,
    case04_fixture
)

logger = logging.getLogger("Port_Mirroring_Cases")

MGMT_IPS = conf.MGMT_IPS
NET1_IPS = conf.NET1_IPS
NET2_IPS = conf.NET2_IPS
VM_NAME = conf.VM_NAME


@attr(tier=2)
@pytest.mark.usefixtures(port_mirroring_prepare_setup.__name__)
@pytest.mark.skipif(
    conf.NOT_4_NICS_HOSTS, reason=conf.NOT_4_NICS_HOST_SKIP_MSG
)
class Base(NetworkTest):
    pass


@pytest.mark.usefixtures(case01_fixture.__name__)
class TestPortMirroringCase01(Base):
    """
    Check that mirroring still works after migration
    """
    __test__ = True

    @polarion("RHEVM3-4020")
    def test_a1_migrate_mirroring_vm(self):
        """
        Check that mirroring still works after migrating listening VM to
        another host and back
        """
        for dst_vm in (2, 3):
            helper.check_traffic_during_icmp(
                src_ip=NET1_IPS[1], dst_ip=NET1_IPS[dst_vm], src_vm=MGMT_IPS[1]
            )

        logger.info(
            "Migrating %s to %s and back to %s", VM_NAME[0], conf.HOSTS[1],
            conf.HOSTS[0]
        )
        for host in (conf.HOSTS[1], conf.HOSTS[0]):
            sample = apis_utils.TimeoutingSampler(
                timeout=conf.SAMPLER_TIMEOUT, sleep=1, func=ll_vms.migrateVm,
                positive=True, vm=VM_NAME[0], host=host
            )
            if not sample.waitForFuncStatus(result=True):
                raise conf.NET_EXCEPTION(
                    "Failed to migrate %s to %s" % (VM_NAME[0], host)
                )

        for dst_vm in (2, 3):
            helper.check_traffic_during_icmp(
                src_ip=NET1_IPS[1], dst_ip=NET1_IPS[dst_vm], src_vm=MGMT_IPS[1]
            )

    @polarion("RHEVM3-4017")
    def test_a2_migrate_all_vms(self):
        """
        Check that mirroring still works after migrating all VMs involved to
        another host
        """
        for dst_vm in (2, 3):
            helper.check_traffic_during_icmp(
                src_ip=NET1_IPS[1], dst_ip=NET1_IPS[dst_vm], src_vm=MGMT_IPS[1]
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
            raise conf.NET_EXCEPTION(
                "Failed to migrate %s to %s" % (VM_NAME[:4], conf.HOSTS[1])
            )

        for dst_vm in (2, 3):
            helper.check_traffic_during_icmp(
                src_ip=NET1_IPS[1], dst_ip=NET1_IPS[dst_vm], src_vm=MGMT_IPS[1]
            )


@pytest.mark.usefixtures(case02_fixture.__name__)
class TestPortMirroringCase02(Base):
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
        helper.check_traffic_during_icmp(
            src_ip=NET1_IPS[3], dst_ip=NET1_IPS[2], src_vm=MGMT_IPS[3]
        )

        for vm_name in VM_NAME[2:4]:
            helper.set_port_mirroring(
                vm_name, conf.NIC_NAME[1], conf.PM_NETWORK[1],
                disable_mirroring=True
            )

        helper.check_traffic_during_icmp(
            src_ip=NET1_IPS[3], dst_ip=NET1_IPS[2], src_vm=MGMT_IPS[3],
            positive=False
        )


class TestPortMirroringCase03(Base):
    """
    Check mirroring when listening on multiple networks on the same machine
    """
    __test__ = True

    @polarion("RHEVM3-4014")
    def test_check_pm_one_machine_multiple_networks(self):
        """
        Check that VM1 gets all traffic on both MGMT network and sw1
        """
        helper.check_traffic_during_icmp(
            src_ip=NET1_IPS[1], dst_ip=NET1_IPS[2], src_vm=MGMT_IPS[1]
        )

        helper.check_traffic_during_icmp(
            nic=conf.NIC_NAME[0], src_ip=MGMT_IPS[3], dst_ip=MGMT_IPS[4],
            src_vm=MGMT_IPS[3]
        )


@pytest.mark.usefixtures(case04_fixture.__name__)
class TestPortMirroringCase04(Base):
    """
    Check port mirroring when it's enabled on multiple machines.
    """
    __test__ = True

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
        helper.check_traffic_during_icmp(
            nic=conf.NIC_NAME[0], src_ip=MGMT_IPS[1], dst_ip=MGMT_IPS[2],
            src_vm=MGMT_IPS[1]
        )

        helper.check_traffic_during_icmp(
            src_ip=MGMT_IPS[1], dst_ip=MGMT_IPS[2],
            src_vm=MGMT_IPS[1], listen_vm=VM_NAME[1], positive=False
        )

        logger.info(
            "Sending traffic between VM1 and VM4 on sw1 to make sure only VM2 "
            "gets this traffic."
        )
        helper.check_traffic_during_icmp(
            src_ip=NET1_IPS[0], dst_ip=NET1_IPS[3],
            src_vm=MGMT_IPS[0], listen_vm=VM_NAME[1]
        )

        helper.check_traffic_during_icmp(
            src_ip=NET1_IPS[0], dst_ip=NET1_IPS[3],
            src_vm=MGMT_IPS[0], nic=conf.NIC_NAME[0], positive=False
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
            helper.check_traffic_during_icmp(
                src_ip=NET1_IPS[2], dst_ip=NET1_IPS[3],
                src_vm=MGMT_IPS[2], listen_vm=vm
            )

        logger.info(
            "Disabling mirroring on VM2 and checking that VM1 still gets the "
            "traffic while VM2 doesn't"
        )
        helper.set_port_mirroring(
            conf.VM_NAME[1], conf.NIC_NAME[1], conf.PM_NETWORK[0],
            disable_mirroring=True
        )

        for vm, expTraffic in zip(conf.VM_NAME[:2], (True, False)):
            helper.check_traffic_during_icmp(
                src_ip=NET1_IPS[2], dst_ip=NET1_IPS[3],
                src_vm=MGMT_IPS[2], listen_vm=vm, positive=expTraffic
            )


class TestPortMirroringCase05(Base):
    """
    Restart VDSM on host while mirroring is on
    """
    __test__ = True

    @polarion("RHEVM3-4009")
    def test_restart_vdsmd_on_host(self):
        """
        Check that mirroring still occurs after restarting VDSM on the host
        """
        helper.check_traffic_during_icmp(
            src_ip=NET1_IPS[1], dst_ip=NET1_IPS[2], src_vm=MGMT_IPS[1],
        )

        logger.info(
            "Restarting VDSM to check if mirroring still works afterwards"
        )
        if not (
            conf.VDS_HOSTS[0].service("supervdsmd").stop() and
            conf.VDS_HOSTS[0].service("vdsmd").restart()
        ):
            raise conf.NET_EXCEPTION(
                "Failed to restart vdsmd service on %s" % conf.HOSTS[0]
            )

        helper.check_traffic_during_icmp(
            src_ip=NET1_IPS[1], dst_ip=NET1_IPS[2], src_vm=MGMT_IPS[1],
        )

        logger.info("Check that %s is UP", conf.HOSTS[0])
        if not ll_hosts.waitForHostsStates(positive=True, names=conf.HOSTS[0]):
            raise conf.NET_EXCEPTION(
                "%s status isn't UP" % conf.HOSTS[0]
            )


class TestPortMirroringCase06(Base):
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
        helper.check_traffic_during_icmp(
            src_ip=NET1_IPS[1], dst_ip=NET1_IPS[2], src_vm=MGMT_IPS[1],
        )

        logger.info(
            "Setting down %s on %s", conf.PM_NETWORK[1],
            conf.HOSTS[0]
        )
        if not conf.VDS_HOSTS[0].network.if_down(nic=conf.PM_NETWORK[0]):
            raise conf.NET_EXCEPTION(
                "Failed to set down %s on %s" %
                (conf.PM_NETWORK[0], conf.HOSTS[0])
            )

        if not conf.VDS_HOSTS[0].network.if_up(nic=conf.PM_NETWORK[0]):
            raise conf.NET_EXCEPTION(
                "Failed to set up %s on %s" %
                (conf.PM_NETWORK[0], conf.HOSTS[0])
            )
        vm_resource = global_helper.get_host_resource(
            ip=conf.MGMT_IPS[1], password=conf.VMS_LINUX_PW
        )
        network_helper.send_icmp_sampler(
            host_resource=vm_resource, dst=NET1_IPS[2]
        )
        logger.info("Check port mirroring traffic down/up bridge")
        helper.check_traffic_during_icmp(
            src_ip=NET1_IPS[1], dst_ip=NET1_IPS[2], src_vm=MGMT_IPS[1],
        )
