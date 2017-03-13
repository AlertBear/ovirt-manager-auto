#! /usr/bin/python
# -*- coding: utf-8 -*-

import pytest
from art.test_handler.tools import polarion
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
from art.unittest_lib import attr, VirtTest, testflow
from rhevmtests.virt.reg_vms.fixtures import (
    change_cpu_limitations, default_cpu_settings,
    create_vm_for_vcpu, make_sure_vm_is_down
)
from rhevmtests.virt.fixtures import create_dc
import config


@pytest.mark.usefixtures(
    default_cpu_settings.__name__,
    make_sure_vm_is_down.__name__
)
@attr(tier=2)
class TestVcpu(VirtTest):
    """
    VCPU cases
    """

    comp_version = config.COMP_VERSION
    vm_name = config.VM_NAME[0]

    @attr(tier=1)
    @polarion("RHEVM3-17327")
    def test_update_vm_cpu_to_max(self):
        """
        Positive: Update VM cpu to maximum (288 cpu's)
        """
        testflow.step(
            "Positive: Update VM %s cpu total to 288", config.VM_NAME[0]
        )
        assert ll_vms.updateVm(
            positive=True,
            vm=self.vm_name,
            cpu_cores=16,
            cpu_socket=9,
            cpu_threads=2
        )

    @polarion("RHEVM3-17328")
    def test_negative_update_vm_cpu_to_more_then_max(self):
        """
        Negative: Update vm cpu to maximum (300 cpu's)
        """
        testflow.step(
            "Negative: Update VM  %s cpu total to 300", config.VM_NAME[0]
        )
        assert not ll_vms.updateVm(
            positive=True,
            vm=self.vm_name,
            cpu_cores=15,
            cpu_socket=10,
            cpu_threads=2
        )

    @pytest.mark.usefixtures(change_cpu_limitations.__name__)
    @polarion("RHEVM3-10623")
    def test_check_cpu_hotplug_over_limit(self):
        """
        Positive + Negative: Change limitation of cpu to 10 and test it
        """
        testflow.step(
            "Positive: Update VM %s cpu total to 10", config.VM_NAME[0]
        )
        assert ll_vms.updateVm(
            positive=True,
            vm=self.vm_name,
            cpu_cores=5,
            cpu_socket=2,
            cpu_threads=1
        )
        testflow.step(
            "Negative: Update VM %s cpu total to 11", config.VM_NAME[0]
        )
        assert not ll_vms.updateVm(
            positive=True,
            vm=self.vm_name,
            cpu_cores=3,
            cpu_socket=4,
            cpu_threads=1

        )


@attr(tier=2)
@pytest.mark.usefixtures(default_cpu_settings.__name__)
class TestVcpuVersion40(VirtTest):
    """
    VCPU cases for 4.0 cluster
    """

    vm_name = "vcpu_vm"
    host_index = 2
    comp_version = "4.0"
    cluster = "Cluster_%s" % comp_version.replace(".", "_")

    @polarion("RHEVM3-11267")
    @pytest.mark.usefixtures(
        create_dc.__name__,
        create_vm_for_vcpu.__name__
    )
    def test_vcpu_on_40(self):
        """
        Positive: change VM CPU'S to maximum value and
        negative: change VM CPU's to value bigger then maximum
        """
        testflow.step(
            "Positive: Update VM %s to maximum value %s",
            self.vm_name, config.VCPU_4_0
        )
        assert ll_vms.updateVm(
            positive=True,
            vm=self.vm_name,
            cpu_cores=16,
            cpu_socket=15,
            cpu_threads=1
        )
        testflow.step(
            "Negative: Update VM %s cpu value bigger then maximum 250",
            self.vm_name
        )
        assert not ll_vms.updateVm(
            positive=True,
            vm=self.vm_name,
            cpu_cores=10,
            cpu_socket=5,
            cpu_threads=5

        )
