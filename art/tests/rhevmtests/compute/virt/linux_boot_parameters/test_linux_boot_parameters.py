#! /usr/bin/python
# -*- coding: utf-8 -*-

import shlex

import pytest

import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import rhevmtests.config as config
from art.test_handler.tools import polarion
from art.unittest_lib import (
    VirtTest,
    tier2,
    testflow
)
from fixtures import (
    copy_files_to_iso, clean_vm, attach_iso
)
from rhevmtests import helpers
from rhevmtests.compute.virt.fixtures import create_vm_class


@pytest.mark.usefixtures(
    create_vm_class.__name__,
    attach_iso.__name__,
    copy_files_to_iso.__name__,
    clean_vm.__name__
)
class TestLinuxBootParameters(VirtTest):
    """
    Testing the linux boot parameters
    """
    vm_name = "vm_linux_boot_parameters"
    vm_parameters = {
        'name': vm_name,
        'template': config.TEMPLATE_NAME[0],
        'os_type': config.OS_TYPE,
        'cluster': config.CLUSTER_NAME[0]
    }
    root_device = None

    @pytest.mark.parametrize(
        (
            "action", "initrd", "vm_linuz", "kernel_params",
            "check_os", "positive"
        ),
        [
            # Update VM command
            pytest.param(

                "updateVm", "iso://initramfs.img", "iso://vmlinuz",
                "root=%s", True, True,
                marks=(polarion("RHEVM-21920"))
            ),
            pytest.param(
                "updateVm", "d", "d", "", False, True,
                marks=(polarion("RHEVM-21997"))
            ),
            pytest.param(
                "updateVm", "ab", "ab", "", False, True,
                marks=(polarion("RHEVM-21998"))
            ),

            # Run VM once
            pytest.param(
                "runVmOnce", "iso://initramfs.img", "iso://vmlinuz", "root=%s",
                True, True, marks=(polarion("RHEVM-21999"))
            ),
            pytest.param(
                "runVmOnce", "d", "d", "", False, True,
                marks=(polarion("RHEVM-22000"))
            ),
            pytest.param(
                "runVmOnce", "ab", "ab", "", False, True,
                marks=(polarion("RHEVM-22001"))
            ),
        ]
    )
    @tier2
    def test_update_linux_params(
        self, action, vm_linuz, initrd, kernel_params, check_os, positive
    ):
        """
        Checking the linux boot parameters with different values
        In the actions: Update, Run Once.
        """
        if '%s' in kernel_params:
            kernel_params = kernel_params % self.root_device
        args = {"kernel": vm_linuz, "initrd": initrd, "cmdline": kernel_params}
        method_to_run = getattr(ll_vms, action)
        testflow.step("%s VM with: %s", action, args)
        result = method_to_run(True, self.vm_name, **args)
        assert result if positive else not result
        if check_os:
            testflow.step("Check cmdline on VM %s", self.vm_name)
            vm_resource = helpers.get_vm_resource(vm=self.vm_name)
            rc, out, _ = vm_resource.run_command(
                shlex.split("cat /proc/cmdline")
            )
            assert not rc
            assert out.strip() == kernel_params
