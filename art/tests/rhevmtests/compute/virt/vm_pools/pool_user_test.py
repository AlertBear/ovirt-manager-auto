#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Vm pool user test - contains test cases regarding user usage of vm pools.
"""

import copy

import pytest

import config
from art.rhevm_api.tests_lib.high_level import (
    vmpools as hl_vmpools,
    vms as hl_vms,
)
from art.rhevm_api.tests_lib.low_level import (
    vms as ll_vms,
    mla as ll_mla,
    vmpools as ll_vmpools,
)
from art.test_handler import exceptions
from art.test_handler.tools import polarion
from art.unittest_lib import (
    VirtTest,
    testflow,
    tier2,
    tier3,
)
from fixtures import (
    create_vm_pool, add_user,
    stop_pool_vms_safely_before_removal,
    vm_pool_teardown  # flake8: noqa
)
import helpers


@pytest.mark.usefixtures(
    create_vm_pool.__name__, stop_pool_vms_safely_before_removal.__name__,
    add_user.__name__,
)
class TestUserVmContinuity(VirtTest):
    """
    Tests that after user allocates a vm, when user is disconnected from the vm
    the vm is still up and not shut down
    """

    __test__ = True

    pool_name = "Virt_pools_user_vm_continuity"
    pool_params = copy.deepcopy(config.VM_POOLS_PARAMS)
    pool_params['size'] = 1
    pool_params['prestarted_vms'] = 1
    users = [config.USER]

    @tier2
    @polarion("RHEVM3-9859")
    def test_user_vm_continuity(self):
        """
        Tests that after user allocates a vm, when user is disconnected from
        the vm it is still up and not shut down:

        1. Wait for vm to start (1/1 vms in the pool set as prestarted).
        2. Allocate the vm as user1 - verify user1 got permission for the vm.
        3. Remove user1's permissions from the vm while it is still up.
        4. Verify the vm is still up and does not shut down.
        """
        testflow.step(
            "Waiting for %s prestarted vms in pool: %s to start",
            self.pool_params['prestarted_vms'], self.pool_name
        )
        hl_vmpools.wait_for_prestarted_vms(
            vm_pool=self.pool_name, wait_until_up=True
        )
        testflow.step("Allocate the prestarted vm as user: %s", config.USER)
        helpers.allocate_vms_as_user(
            True, self.pool_name, config.USER, 0, 1, False
        )
        user_vms = helpers.get_user_vms(
            self.pool_name, config.USER_NAME, config.USER_ROLE, 1
        )
        if not user_vms:
            raise exceptions.VmPoolException()
        testflow.step(
            "Removing permissions for user: %s on vm: %s - vm should return "
            "to pool and stay up", config.USER, user_vms[0]
        )
        if not ll_mla.removeUserPermissionsFromVm(
            True, user_vms[0], config.USER_NAME
        ):
            raise exceptions.VMException()
        testflow.step("Verifying that status is 'up' for vm: %s", user_vms[0])
        if not ll_vms.checkVmState(True, user_vms[0], config.VM_UP):
            raise exceptions.VMException(
                "Vm: %s changed status unexpectedly after user: %s "
                "disconnected. Expected state = %s" %
                (user_vms[0], config.USER_NAME, config.VM_UP)
            )


@pytest.mark.usefixtures(create_vm_pool.__name__, add_user.__name__)
class TestTwoUsersTakeVmFromPool(VirtTest):
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
    pool_params = copy.deepcopy(config.VM_POOLS_PARAMS)
    users = [config.USER, config.VDC_ADMIN_USER]

    @tier2
    @polarion("RHEVM3-9891")
    def test_two_users_take_vm_from_pool(self):
        testflow.step(
            "Allocating a vm from pool: %s as user %s",
            self.pool_name, config.USER
        )
        helpers.allocate_vms_as_user(True, self.pool_name, config.USER, 0, 1)
        testflow.step(
            "Allocating a vm from pool: %s as user %s",
            self.pool_name, config.VDC_ADMIN_USER
        )
        helpers.allocate_vms_as_user(
            True, self.pool_name, config.VDC_ADMIN_USER, 0, 1
        )
        testflow.step("Stopping all vms in pool: %s", self.pool_name)
        assert hl_vmpools.stop_vm_pool(self.pool_name)
        vms = ll_vmpools.get_vms_in_pool_by_name(self.pool_name)
        testflow.step(
            "Verify that the users permissions on the vms from the previous "
            "sessions is gone as pool is an automatic pool"
        )
        helpers.verify_vms_have_no_permissions_for_user(
            vms, config.USER_NAME, config.USER_ROLE
        )
        helpers.verify_vms_have_no_permissions_for_user(
            vms, config.ADMIN_USER_NAME, config.USER_ROLE
        )


@pytest.mark.usefixtures(create_vm_pool.__name__, add_user.__name__)
class TestNoAvailableVmsForUser(VirtTest):
    """
    Negative case - user fails to allocate vm after admin started all vms in
    the pool
    """
    __test__ = True

    pool_name = "Virt_no_available_vms_for_user"
    pool_params = copy.deepcopy(config.VM_POOLS_PARAMS)
    users = [config.USER]

    @tier3
    @polarion("RHEVM3-9881")
    def test_no_available_vms_for_user(self):
        testflow.step("Start the only vm in pool: %s as admin", self.pool_name)
        hl_vmpools.start_vm_pool(self.pool_name)
        testflow.step(
            "Attempt to allocate the vm as user: %s - should fail as vm is "
            "used by admin", config.USER
        )
        helpers.allocate_vms_as_user(False, self.pool_name, config.USER, 0, 1)


@pytest.mark.usefixtures(
    create_vm_pool.__name__, stop_pool_vms_safely_before_removal.__name__,
    add_user.__name__,
)
class TestCannotStealVmFromOtherUser(VirtTest):
    """
    Negative case - user fails to allocate a vm from the pool after all vms
    were allocated by another user
    """
    __test__ = True

    pool_name = "Virt_cannot_steal_vm_from_another_user"
    pool_params = copy.deepcopy(config.VM_POOLS_PARAMS)
    pool_params['size'] = 1
    users = [config.USER, config.VDC_ADMIN_USER]

    @tier3
    @polarion("RHEVM3-9883")
    def test_cannot_steal_vm_from_another_user(self):
        testflow.step(
            "Allocate the only vm in pool: %s as user: %s",
            self.pool_name, config.VDC_ADMIN_USER
        )
        helpers.allocate_vms_as_user(
            True, self.pool_name, config.VDC_ADMIN_USER, 0, 1
        )
        testflow.step(
            "Attempt to allocate the vm as user: %s - should fail as vm is "
            "used by admin", config.USER
        )
        helpers.allocate_vms_as_user(False, self.pool_name, config.USER, 0, 1)


@pytest.mark.usefixtures(
    create_vm_pool.__name__, stop_pool_vms_safely_before_removal.__name__,
    add_user.__name__,
)
class TestVmReturnsToPoolAfterUse(VirtTest):
    """
    Basic test for Automatic Pools - allocate a vm from the pool with user1
    stop the vm with user1, login with user2 and allocate a vm from the pool
    with user2 (tested with 1 vm pool)
    """
    __test__ = True

    pool_name = "Virt_vm_returns_to_pool_after_use"
    pool_params = copy.deepcopy(config.VM_POOLS_PARAMS)
    pool_params['size'] = 1
    users = [config.USER, config.VDC_ADMIN_USER]

    @tier2
    @polarion("RHEVM3-9882")
    def test_vm_returns_to_pool_after_use(self):
        testflow.step(
            "Allocate the only vm in pool: %s as user: %s",
            self.pool_name, config.VDC_ADMIN_USER
        )
        helpers.allocate_vms_as_user(
            True, self.pool_name, config.VDC_ADMIN_USER, 0, 1
        )
        testflow.step("Stop the vm")
        hl_vms.stop_stateless_vm(
            ll_vmpools.get_vms_in_pool_by_name(self.pool_name)[0]
        )
        testflow.step(
            "Attempt to allocate the vm as user: %s - should succeed as pool "
            "is automatic and previous session was done", config.USER
        )
        helpers.allocate_vms_as_user(True, self.pool_name, config.USER, 0, 1)
