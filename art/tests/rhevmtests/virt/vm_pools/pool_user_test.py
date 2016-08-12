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
from art.rhevm_api.tests_lib.high_level import (
    vmpools as hl_vmpools,
    vms as hl_vms,
)
from art.test_handler import exceptions
from art.test_handler.tools import polarion, bz


class TestUserVmContinuity(base.VmPoolWithUser):
    """
    Tests that after user allocates a vm, when user is disconnected from the vm
    the vm is still up and not shut down
    """

    __test__ = True

    pool_name = "Virt_pools_user_vm_continuity"
    pool_size = 1
    prestarted_vms = 1

    @bz({'1342795': {}})
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


class TestTwoUsersTakeVmFromPool(base.VmPoolWithUser):
    """
    Tests vm allocation from pool as user + allocating remaining vm with
    another user:

    1. Allocate a vm from the pool as user1.
    2. Allocate the remaining vm in the pool as user2
    2. Verify each user got permissions to one vm and vms are up.
    3. Stop the vms.
    4. After vms are down, verify that user's permissions were removed from it.
    """
    __test__ = True

    pool_name = "Virt_user_role_take_vm_from_pool"

    @bz({'1342795': {}})
    @polarion("RHEVM-9891")
    def test_two_users_take_vm_from_pool(self):
        helpers.allocate_vms_as_user(True, self.pool_name, config.USER, 0, 1)
        helpers.allocate_vms_as_user(
            True, self.pool_name, config.VDC_ADMIN_USER, 0, 1
        )
        assert hl_vmpools.stop_vm_pool(self.pool_name)
        vms = base.ll_vmpools.get_vms_in_pool_by_name(self.pool_name)
        helpers.verify_vms_have_no_permissions_for_user(
            vms, self.user_name, config.USER_ROLE
        )
        helpers.verify_vms_have_no_permissions_for_user(
            vms, self.admin_user_name, config.USER_ROLE
        )


class TestNoAvailableVmsForUser(base.VmPoolWithUser):
    """
    Negative case - user fails to allocate vm after admin started all vms in
    the pool
    """
    __test__ = True

    pool_name = "Virt_no_available_vms_for_user"

    @polarion("RHEVM-9881")
    def test_no_available_vms_for_user(self):
        hl_vmpools.start_vm_pool(self.pool_name)
        helpers.allocate_vms_as_user(False, self.pool_name, config.USER, 0, 1)


class TestCannotStealVmFromOtherUser(base.VmPoolWithUser):
    """
    Negative case - user fails to allocate a vm from the pool after all vms
    were allocated by another user
    """
    __test__ = True

    pool_name = "Virt_cannot_steal_vm_from_another_user"
    pool_size = 1

    @bz({'1342795': {}})
    @polarion("RHEVM-9883")
    def test_cannot_steal_vm_from_another_user(self):
        helpers.allocate_vms_as_user(
            True, self.pool_name, config.VDC_ADMIN_USER, 0, 1
        )
        helpers.allocate_vms_as_user(False, self.pool_name, config.USER, 0, 1)


class TestVmReturnsToPoolAfterUse(base.VmPoolWithUser):
    """
    Basic test for Automatic Pools - allocate a vm from the pool with user1
    stop the vm with user1, login with user2 and allocate a vm from the pool
    with user2 (tested with 1 vm pool)
    """
    __test__ = True

    pool_name = "Virt_vm_returns_to_pool_after_use"
    pool_size = 1

    @bz({'1342795': {}})
    @polarion("RHEVM-9882")
    def test_vm_returns_to_pool_after_use(self):
        helpers.allocate_vms_as_user(
            True, self.pool_name, config.VDC_ADMIN_USER, 0, 1
        )
        hl_vms.stop_stateless_vm(
            base.ll_vmpools.get_vms_in_pool_by_name(self.pool_name)[0]
        )
        helpers.allocate_vms_as_user(True, self.pool_name, config.USER, 0, 1)
