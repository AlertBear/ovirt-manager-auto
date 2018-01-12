#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Test Port mirroring.
using 2 hosts and 5 VMs
"""

import pytest

import art.rhevm_api.tests_lib.high_level.vms as hl_vms
from art.rhevm_api.tests_lib.low_level import (
    hosts as ll_hosts,
    vms as ll_vms
)
import config as pm_conf
import helper
import rhevmtests.helpers as global_helper
from rhevmtests.networking import config as conf, helper as network_helper
from art.core_api import apis_utils
from art.test_handler.tools import polarion, bz
from art.unittest_lib import (
    tier2,
    NetworkTest,
    testflow,
)
from fixtures import (
    port_mirroring_prepare_setup,
    return_vms_to_original_host,
    disable_port_mirroring,
    set_port_mirroring
)


@pytest.mark.usefixtures(port_mirroring_prepare_setup.__name__)
@pytest.mark.skipif(
    conf.NOT_4_NICS_HOSTS,
    reason=conf.NOT_4_NICS_HOST_SKIP_MSG
)
class Base(NetworkTest):
    pass


@bz({"1496719": {}})
@pytest.mark.incremental
@pytest.mark.usefixtures(return_vms_to_original_host.__name__)
class TestPortMirroringCase01(Base):
    """
    Check that mirroring still works after migration
    """
    # General params
    net1_ips = pm_conf.NET1_IPS
    mgmt_ips = pm_conf.MGMT_IPS
    vm_names = conf.VM_NAME[:4]

    @tier2
    @polarion("RHEVM3-4020")
    def test_a1_migrate_mirroring_vm(self):
        """
        Check that mirroring still works after migrating listening VM to
        another host and back
        """
        testflow.step(
            "Send traffic between VM %s to VM %s and VM %s and make sure "
            "that the traffic is mirroring to VM %s", conf.VM_1,
            conf.VM_NAME[2], conf.VM_NAME[3], conf.VM_0
        )
        for dst_vm in self.net1_ips[2:4]:
            assert helper.check_traffic_during_icmp(
                src_ip=self.net1_ips[1], dst_ip=dst_vm, src_vm=self.mgmt_ips[1]
            )

        for host in (conf.HOST_1_NAME, conf.HOST_0_NAME):
            testflow.step(
                "Migrating %s to host %s", conf.VM_0, host
            )
            sample = apis_utils.TimeoutingSampler(
                timeout=conf.SAMPLER_TIMEOUT, sleep=1, func=ll_vms.migrateVm,
                positive=True, vm=conf.VM_0, host=host
            )
            assert sample.waitForFuncStatus(result=True)

        testflow.step(
            "Check that mirroring still works after migrating listening VM %s"
            "to another host %s and back to %s", conf.VM_0, conf.HOST_1_NAME,
            conf.HOST_0_NAME
        )

        for dst_vm in self.net1_ips[2:4]:
            assert helper.check_traffic_during_icmp(
                src_ip=self.net1_ips[1], dst_ip=dst_vm, src_vm=self.mgmt_ips[1]
            )

    @tier2
    @polarion("RHEVM3-4017")
    def test_a2_migrate_all_vms(self):
        """
        Check that mirroring still works after migrating all VMs involved to
        another host
        """
        testflow.step(
            "Send traffic between VM %s to VM %s and VM %s and make sure "
            "that the traffic is mirroring to VM %s", conf.VM_1,
            conf.VM_NAME[2], conf.VM_NAME[3], conf.VM_0
        )
        for dst_vm in self.net1_ips[2:4]:
            assert helper.check_traffic_during_icmp(
                src_ip=self.net1_ips[1], dst_ip=dst_vm, src_vm=self.mgmt_ips[1]
            )

        testflow.step(
            "Migrating all VMs %s to %s and check if PM still works ",
            self.vm_names, conf.HOST_1_NAME
        )

        assert hl_vms.migrate_vms(
            vms_list=self.vm_names, src_host=conf.HOST_0_NAME,
            vm_os_type="rhel", vm_user=conf.VMS_LINUX_USER,
            vm_password=conf.VMS_LINUX_PW, dst_host=conf.HOST_1_NAME
        )

        for dst_vm in self.net1_ips[2:4]:
            assert helper.check_traffic_during_icmp(
                src_ip=self.net1_ips[1], dst_ip=dst_vm, src_vm=self.mgmt_ips[1]
            )


@pytest.mark.usefixtures(disable_port_mirroring.__name__)
class TestPortMirroringCase02(Base):
    """
    Replace network on the mirrored VM to a non-mirrored network
    """
    # General params
    nic_name_2 = pm_conf.PM_NIC_NAME[0]
    net_1 = pm_conf.PM_NETWORK[1]
    net1_ip2 = pm_conf.NET1_IPS[2]
    net1_ip3 = pm_conf.NET1_IPS[3]
    mgmt_ips = pm_conf.MGMT_IPS

    @tier2
    @polarion("RHEVM3-4010")
    def test_check_mirroring_after_replacing_network(self):
        """
        Replace the network on a mirrored VM with a non-mirrored network and
        check that its traffic is not mirrored anymore.
        """
        testflow.step(
            "Send traffic between VM %s to VM %s make sure "
            "that the traffic is mirroring to VM %s",
            conf.VM_NAME[3], conf.VM_NAME[2], conf.VM_0
        )
        assert helper.check_traffic_during_icmp(
            src_ip=self.net1_ip3, dst_ip=self.net1_ip2, src_vm=self.mgmt_ips[3]
        )

        for vm_name in conf.VM_NAME[2:4]:
            testflow.step(
                "Replace the network %s on a mirrored VM %s with a "
                "non-mirrored network", self.net_1, vm_name
            )
            assert helper.set_port_mirroring(
                vm=vm_name, nic=self.nic_name_2, network=self.net_1,
                disable_mirroring=True
            )
        testflow.step(
            "Send traffic between VM %s to VM %s make sure that the traffic is"
            "not mirrored anymore", conf.VM_NAME[3], conf.VM_NAME[2]
        )
        assert helper.check_traffic_during_icmp(
            src_ip=self.net1_ip3, dst_ip=self.net1_ip2,
            src_vm=self.mgmt_ips[3], positive=False
        )


class TestPortMirroringCase03(Base):
    """
    Check mirroring when listening on multiple networks on the same machine
    """
    # General params
    net1_ip1 = pm_conf.NET1_IPS[1]
    net1_ip2 = pm_conf.NET1_IPS[2]
    nic_name_1 = conf.NIC_NAME[0]
    mgmt_ips = pm_conf.MGMT_IPS

    @tier2
    @polarion("RHEVM3-4014")
    def test_check_pm_one_machine_multiple_networks(self):
        """
        Check that VM1 gets all traffic on both MGMT network and net1
        """
        testflow.step(
            "Check mirroring when listening on multiple networks on the same "
            "machine"
        )
        assert helper.check_traffic_during_icmp(
            src_ip=self.net1_ip1, dst_ip=self.net1_ip2, src_vm=self.mgmt_ips[1]
        )

        assert helper.check_traffic_during_icmp(
            nic=self.nic_name_1, src_ip=self.mgmt_ips[3],
            dst_ip=self.mgmt_ips[4], src_vm=self.mgmt_ips[3]
        )


@pytest.mark.usefixtures(set_port_mirroring.__name__)
@pytest.mark.incremental
class TestPortMirroringCase04(Base):
    """
    Check port mirroring when it's enabled on multiple machines.
    """
    # General params
    nic_name_1 = conf.NIC_NAME[0]
    nic_name_2 = pm_conf.PM_NIC_NAME[0]
    net_1 = pm_conf.PM_NETWORK[0]
    mgmt_ips = pm_conf.MGMT_IPS
    net1_ip = pm_conf.NET1_IPS[0]
    net1_ip2 = pm_conf.NET1_IPS[2]
    net1_ip3 = pm_conf.NET1_IPS[3]

    @tier2
    @bz({"1533778": {}})
    @polarion("RHEVM3-4015")
    def test_a1_check_pm_two_machines_diff_networks(self):
        """
        Check mirroring when it's enabled on different machines on different
        networks (VM1 is listening to mgmt network and VM2 is listening to
        net1)
        """
        testflow.step(
            "Sending traffic between VM %s and VM %s on MGMT network to "
            "make sure only VM %s gets this traffic.", conf.VM_1,
            conf.VM_NAME[2], conf.VM_0
        )
        assert helper.check_traffic_during_icmp(
            nic=self.nic_name_1, src_ip=self.mgmt_ips[1],
            dst_ip=self.mgmt_ips[2], src_vm=self.mgmt_ips[1]
        )

        assert helper.check_traffic_during_icmp(
            src_ip=self.mgmt_ips[1], dst_ip=self.mgmt_ips[2],
            src_vm=self.mgmt_ips[1], listen_vm=conf.VM_1, positive=False
        )

        testflow.step(
            "Sending traffic between VM %s and VM %s on net %s to make sure"
            "only VM %s gets this traffic.", conf.VM_0, conf.VM_NAME[3],
            self.net_1, conf.VM_1
        )
        assert helper.check_traffic_during_icmp(
            src_ip=self.net1_ip, dst_ip=self.net1_ip3, src_vm=self.mgmt_ips[0],
            listen_vm=conf.VM_1
        )

        assert helper.check_traffic_during_icmp(
            src_ip=self.net1_ip, dst_ip=self.net1_ip3, src_vm=self.mgmt_ips[0],
            nic=self.nic_name_1, positive=False
        )

    @tier2
    @polarion("RHEVM3-4006")
    def test_a2_check_pm_two_machines_same_network(self):
        """
        Check port mirroring when two machines are listening to the same
        network (VM1 and VM2 listening on net1).
        """
        testflow.step(
            "Sending traffic between VM %s and VM %s on net %s to make sure "
            "both VM %s and VM %s get the traffic.", conf.VM_NAME[2],
            conf.VM_NAME[3], self.net_1, conf.VM_0, conf.VM_1
        )
        for vm in conf.VM_NAME[:2]:
            assert helper.check_traffic_during_icmp(
                src_ip=self.net1_ip2, dst_ip=self.net1_ip3,
                src_vm=self.mgmt_ips[2], listen_vm=vm
            )

        testflow.step(
            "Disabling mirroring on VM %s", conf.VM_1
        )
        assert helper.set_port_mirroring(
            vm=conf.VM_1, nic=self.nic_name_2, network=self.net_1,
            disable_mirroring=True
        )
        testflow.step(
            "Checking that VM %s still gets the traffic while VM %s doesn't",
            conf.VM_0, conf.VM_1
        )
        for vm, expTraffic in zip(conf.VM_NAME[:2], (True, False)):
            assert helper.check_traffic_during_icmp(
                src_ip=self.net1_ip2, dst_ip=self.net1_ip3,
                src_vm=self.mgmt_ips[2], listen_vm=vm, positive=expTraffic
            )


class TestPortMirroringCase05(Base):
    """
    Restart VDSM on host while mirroring is on
    """
    # General params
    net1_ip1 = pm_conf.NET1_IPS[1]
    net1_ip2 = pm_conf.NET1_IPS[2]
    mgmt_ips = pm_conf.MGMT_IPS

    @tier2
    @polarion("RHEVM3-4009")
    def test_restart_vdsmd_on_host(self):
        """
        Check that mirroring still occurs after restarting VDSM on the host
        """
        assert helper.check_traffic_during_icmp(
            src_ip=self.net1_ip1, dst_ip=self.net1_ip2, src_vm=self.mgmt_ips[1]
        )

        testflow.step(
            "Restarting VDSM to check if mirroring still works afterwards"
        )
        assert (
            conf.VDS_0_HOST.service("supervdsmd").stop() and
            conf.VDS_0_HOST.service("vdsmd").restart()
        ), "Failed to restart vdsmd service on %s" % conf.HOST_0_NAME

        assert helper.check_traffic_during_icmp(
            src_ip=self.net1_ip1, dst_ip=self.net1_ip2, src_vm=self.mgmt_ips[1]
        )

        testflow.step("Check that %s is UP", conf.HOST_0_NAME)
        assert ll_hosts.wait_for_hosts_states(
            positive=True, names=conf.HOST_0_NAME
        )


class TestPortMirroringCase06(Base):
    """
    Check that mirroring still occurs after down/UP listening bridge on the
    host
    """
    # General params
    net1_ip1 = pm_conf.NET1_IPS[1]
    net1_ip2 = pm_conf.NET1_IPS[2]
    net_1 = pm_conf.PM_NETWORK[0]
    mgmt_ips = pm_conf.MGMT_IPS

    @tier2
    @polarion("RHEVM-19154")
    def test_if_up_down_bridge(self):
        """
        Check that mirroring still occurs after down/UP listening bridge on the
        host
        """
        testflow.step("Check port mirroring traffic before down/up bridge")
        assert helper.check_traffic_during_icmp(
            src_ip=self.net1_ip1, dst_ip=self.net1_ip2, src_vm=self.mgmt_ips[1]
        )

        testflow.step(
            "Setting down %s on %s", self.net_1, conf.HOST_0_NAME
        )
        assert conf.VDS_0_HOST.network.if_down(nic=self.net_1)

        assert conf.VDS_0_HOST.network.if_up(nic=self.net_1)

        vm_resource = global_helper.get_host_resource(
            ip=self.mgmt_ips[1], password=conf.VMS_LINUX_PW
        )
        network_helper.send_icmp_sampler(
            host_resource=vm_resource, dst=self.net1_ip2
        )
        testflow.step("Check port mirroring traffic down/up bridge")
        assert helper.check_traffic_during_icmp(
            src_ip=self.net1_ip1, dst_ip=self.net1_ip2, src_vm=self.mgmt_ips[1]
        )
