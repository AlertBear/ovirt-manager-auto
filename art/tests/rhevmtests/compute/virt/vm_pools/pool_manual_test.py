#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Vm pool - Manual pool test - Tests behaviour of manual pools
"""

import copy
import logging

import pytest

import art.rhevm_api.tests_lib.high_level.vms as hl_vms
import config
import helpers
import rhevmtests.compute.virt.helper as virt_helper
import rhevmtests.helpers as gen_helper
from art.rhevm_api.tests_lib.low_level import (
    vms as ll_vms,
    vmpools as ll_vmpools,
    mla as ll_mla,
)
from art.test_handler.tools import polarion
from art.unittest_lib import (
    VirtTest,
    testflow,
    tier2,
)
from fixtures import (
    create_vm_pool, add_user,
    stop_pool_vms_safely_before_removal,
    vm_pool_teardown  # flake8: noqa
)

logger = logging.getLogger("virt.vm_pools.manual_test")


@pytest.mark.usefixtures(create_vm_pool.__name__, add_user.__name__)
class TestManualPoolCannotRecycleVm(VirtTest):
    """
    Checks that in a manual pool once a user allocated a vm from the pool, no
    other user can use the vm unless the permission of the 1st user is removed:

    1. Allocate all the vms in a pool as user1.
    2. Stop one of the vms.
    3. Attempt to allocate the vm with a different user and fail.
    """

    __test__ = True

    pool_name = 'Virt_manual_pool_cannot_recycle_vm'
    pool_params = copy.deepcopy(config.VM_POOLS_PARAMS)
    pool_params['type_'] = config.POOL_TYPE_MANUAL
    pool_params['max_user_vms'] = 2
    users = [config.USER, config.VDC_ADMIN_USER]

    @tier2
    @polarion("RHEVM3-9874")
    def test_manual_pool_cannot_recycle_vm(self):
        testflow.step(
            "Allocating 2 vms from pool: %s as user %s",
            self.pool_name, config.USER
        )
        helpers.allocate_vms_as_user(True, self.pool_name, config.USER, 0, 2)
        stopped_vm = ll_vmpools.get_vms_in_pool_by_name(self.pool_name)[0]
        testflow.step("Stopping vm: %s", stopped_vm)
        helpers.stop_vm_in_pool_as_user(
            positive=True, vm=stopped_vm, user=config.USER, manual=True
        )
        testflow.step(
            "Attempting to allocate a vm from pool: %s with user %s",
            self.pool_name, config.USER
        )
        helpers.allocate_vms_as_user(
            False, self.pool_name, config.VDC_ADMIN_USER, 0, 1
        )


@pytest.mark.usefixtures(
    create_vm_pool.__name__, stop_pool_vms_safely_before_removal.__name__,
    add_user.__name__,
)
class TestManualPoolRememberUser(VirtTest):
    """
    Checks that in manual pool each vm allocated to a certain user stays
    attached to the user after stopping the vm and that the specific stateless
    snapshot created for the vm at allocation persists upon stop -> start:

    1. Allocate 1 vm per each user (in this case 2 users).
    2. Verify each vm got the permission for the correct user.
    3. Create a file in each vm.
    4. Stop both vms - verify that permission for the user and the stateless
    snapshot persist after vm is down.
    5. Start both vms again - verify that permission for the user and the
    stateless snapshot persist after vm is started.
    6. Verify that the files that were created on the vms still exist
    """

    __test__ = True

    pool_name = 'Virt_manual_pool_remember_user'
    pool_params = copy.deepcopy(config.VM_POOLS_PARAMS)
    pool_params['type_'] = config.POOL_TYPE_MANUAL
    users = [config.USER, config.VDC_ADMIN_USER]

    @tier2
    @polarion("RHEVM3-9876")
    def test_manual_pool_remember_user(self):
        vms = {self.users[0]: '', self.users[1]: ''}
        for user in self.users:
            user_name = '%s@%s' % (user, config.USER_DOMAIN)
            testflow.step(
                "Allocating a vm from pool: %s as user %s",
                self.pool_name, user
            )
            helpers.allocate_vms_as_user(
                True, self.pool_name, user, 0, 1, False
            )
            vms[user] = helpers.get_user_vms(
                self.pool_name, user_name, config.USER_ROLE, 1
            )[0]
            ll_vms.wait_for_vm_states(vms[user])
            vm_resource = gen_helper.get_vm_resource(vms[user])
            testflow.step("Creating a file in vm: %s", vms[user])
            virt_helper.create_file_in_vm(vms[user], vm_resource)
            testflow.step("Verifying file exists in vm: %s", vms[user])
            virt_helper.check_if_file_exist(True, vms[user], vm_resource)
            assert helpers.flush_file_system_buffers(vm_resource)
        testflow.step("Stopping all vms in pool: %s", self.pool_name)
        for user in self.users:
            helpers.stop_vm_in_pool_as_user(
                positive=True, vm=vms[user], user=user, manual=True
            )
        testflow.step(
            "Starting vms in pool: %s each with the user which is "
            "permitted to use it", self.pool_name
        )
        for user in self.users:
            helpers.start_vm_in_pool_as_user(
                positive=True, vm=vms[user], user=user,
                check_permission=True, manual=True
            )
            vm_resource = gen_helper.get_vm_resource(vms[user])
            testflow.step("Verifying file still exists on vm: %s", vms[user])
            virt_helper.check_if_file_exist(True, vms[user], vm_resource)


@pytest.mark.usefixtures(
    create_vm_pool.__name__, stop_pool_vms_safely_before_removal.__name__,
    add_user.__name__,
)
class TestManualPoolRecycleVm(VirtTest):
    """
    Checks that a vm in the pool is available for other users and that it's
    stateless snapshot is removed once it's original user's permission is
    removed:

    1. Allocate a vm from the pool as user1.
    2. Verify the vm got the permission for the user and that a stateless
    snapshot is created for it.
    3. Stop the vm - verify the user's permission and the snapshot persist.
    4. Remove the user's permission from the vm.
    5. Verify that the stateless snapshot is removed.
    6. Allocate the vm from the pool with a different user.
    """

    __test__ = True

    pool_name = 'Virt_manual_pool_recycle_vm'
    pool_params = copy.deepcopy(config.VM_POOLS_PARAMS)
    pool_params['size'] = 1
    pool_params['type_'] = config.POOL_TYPE_MANUAL
    users = [config.USER, config.VDC_ADMIN_USER]

    @tier2
    def test_manual_pool_recycle_vm(self):
        testflow.step(
            "Allocating a vm from pool: %s as user %s",
            self.pool_name, config.USER
        )
        helpers.allocate_vms_as_user(True, self.pool_name, config.USER, 0, 1)
        stopped_vm = ll_vmpools.get_vms_in_pool_by_name(self.pool_name)[0]
        testflow.step("Stopping the vm: %s", stopped_vm)
        helpers.stop_vm_in_pool_as_user(
            positive=True, vm=stopped_vm, user=config.USER, manual=True
        )
        testflow.step(
            "Removing permissions for user: %s from vm: %s",
            config.USER_NAME, stopped_vm
        )
        assert ll_mla.removeUserPermissionsFromVm(
            True, stopped_vm, config.USER_NAME
        )
        testflow.step(
            "Waiting for stateless snapshot to be restored for vm: %s",
            stopped_vm
        )
        assert hl_vms.wait_for_restored_stateless_snapshot(stopped_vm)
        testflow.step(
            "Allocating a vm from pool: %s as user %s",
            self.pool_name, config.VDC_ADMIN_USER
        )
        helpers.allocate_vms_as_user(
            True, self.pool_name, config.VDC_ADMIN_USER, 0, 1
        )
