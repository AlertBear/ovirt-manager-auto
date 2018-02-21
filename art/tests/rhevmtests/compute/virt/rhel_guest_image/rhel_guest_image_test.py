#! /usr/bin/python
# -*- coding: utf-8 -*-
"""
RHEL guest image test plan:
/project/RHEVM3/wiki/Compute/3_5_VIRT_rhel_guest_image_sanity
"""

import pytest

import config
import rhevmtests.compute.virt.virt_executor as executor
from art.test_handler.tools import polarion
from art.unittest_lib import (
    VirtTest,
    tier2,
    testflow
)
from fixtures import (
    class_setup_vm_cases
)


@pytest.mark.skipif(config.PPC_ARCH, reason=config.PPC_SKIP_MESSAGE)
@pytest.mark.skipif(
    not config.NO_HYPERCONVERGED_SUPPORT,
    reason=config.NO_HYPERCONVERGED_SUPPORT_SKIP_MSG
)
@pytest.mark.usefixtures(class_setup_vm_cases.__name__)
class TestGuestImageVMs(VirtTest):
    """
    Testing VM created from guest image templates
    """
    start_vm_parameters = {
        'use_cloud_init': True,
        'wait_for_ip': True
    }
    memory_hotplug_kwargs = {
        "user_name": config.VM_USER_CLOUD_INIT
    }

    cpu_hotplug_kwargs = {
        "user_name": config.VM_USER_CLOUD_INIT
    }
    actions = [
        (config.START_ACTION, start_vm_parameters),
        (config.CLOUD_INIT_CHECK, None),
        (config.MIGRATION_ACTION, None),
        (config.SUSPEND_RESUME, None),
        (config.SNAPSHOT_MEM_ACTION, None),
        (config.START_ACTION, start_vm_parameters),
        (config.CPU_HOTPLUG_ACTION, cpu_hotplug_kwargs),
        (config.MEMORY_HOTPLUG_ACTION, memory_hotplug_kwargs),
        (config.STOP_ACTION, None)
    ]
    tests_params = [
        pytest.param(actions, vm_name) for vm_name in config.TESTED_VMS_NAMES
    ]

    @tier2
    @polarion("RHEVM3-5353")
    @pytest.mark.parametrize(
        ("actions", "vm_name"),
        tests_params, ids=config.TESTED_VMS_NAMES
    )
    def test_guest_image_template(
        self, actions, vm_name
    ):
        """
        Check start, login to VM, suspend resume, stop on rhel guest image vm
        Args:
            actions (list): List of action to invoke on vm
            vm_name (str): VM name
        """

        testflow.step("Check image %s with actions: %s", vm_name, actions)
        for action in actions:
            assert executor.vm_life_cycle_action(
                vm_name=vm_name,
                action_name=action[0],
                func_args=action[1]
            )
