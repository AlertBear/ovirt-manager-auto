#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Vm pool user test - contains test cases regarding user usage of vm pools.
"""

import config
from rhevmtests.virt.vm_pools import (
    vm_pool_base as base,
    helpers,
)
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import art.rhevm_api.tests_lib.high_level.vmpools as hl_vmpools
from art.test_handler import exceptions
from art.test_handler.tools import polarion  # pylint: disable=E0611


class TestUserVmContinuity(base.VmPoolWithUser):
    """
    Tests that after user allocates a vm, when user is disconnected from the vm
    the vm is still up and not shut down
    """

    __test__ = True

    pool_name = "Virt_pools_user_vm_continuity"
    pool_size = 1
    prestarted_vms = 1

    @polarion("RHEVM-9859")
    def test_user_vm_continuity(self):
        """
        Tests that after user allocates a vm, when user is disconnected from
        the vm it is still up and not shut down:

        1. Wait for vm to start (1/1 vms in the pool set as prestarted).
        2. Allocate the vm as user1 - verify user1 got permission for the vm.
        3. Remove user1's permissions from the vm while it is still up.
        4. Verify the vm is still up and does not shut down.
        """
        hl_vmpools.wait_for_prestarted_vms(
            vm_pool=self.pool_name, wait_until_up=True
        )
        helpers.allocate_vms_as_user(
            True, self.pool_name, config.USER, 0, 1, False
        )
        user_vms = helpers.get_user_vms(
            self.pool_name, self.user_name, config.USER_ROLE, 1
        )
        if not user_vms:
            raise exceptions.VmPoolException()
        if not base.ll_mla.removeUserPermissionsFromVm(
            True, user_vms[0], self.user_name
        ):
            raise exceptions.VMException(
                "Failed to remove permission for user: %s on vm: %s" %
                (self.user_name, user_vms[0])
            )
        if not ll_vms.checkVmState(True, user_vms[0], config.VM_UP):
            raise exceptions.VMException(
                "Vm: %s changed status unexpectedly after user: %s "
                "disconnected. Expected state = %s" %
                (user_vms[0], self.user_name, config.VM_UP)
            )


class TestTakeVmFromPoolAsUser(base.VmPoolWithUser):
    """
    Tests vm allocation from pool as user
    """
    __test__ = True

    pool_name = "Virt_user_role_take_vm_from_pool"

    @polarion("RHEVM-9892")
    def test_take_vm_from_pool_as_user(self):
        """
        Tests vm allocation from pool as user:

        1. Allocate a vm from the pool as user1.
        2. Verify user1 gor permissions to the vm and vm is up.
        3. Stop the vm.
        4. After vm is down, verify that user permissions were removed from it.
        """
        helpers.allocate_vms_as_user(
            True, self.pool_name, config.USER, 0, 1, False
        )
        vms = helpers.get_user_vms(
            self.pool_name, self.user_name, config.USER_ROLE, 1
        )
        self.assertTrue(ll_vms.stop_vms_safely(vms))
        helpers.verify_vms_have_no_permissions_for_user(
            vms, self.user_name, config.USER_ROLE)
