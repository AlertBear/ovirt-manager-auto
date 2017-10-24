#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
prestarted vms test - features test cases concerning prestarted vm in the pool.
"""

import copy
import logging

import pytest

import config
from art.rhevm_api.tests_lib.high_level import vmpools as hl_vmpools
from art.rhevm_api.tests_lib.low_level import (
    vms as ll_vms,
    vmpools as ll_vmpools,
)
from art.test_handler import exceptions
from art.test_handler.tools import polarion
from art.unittest_lib import (
    VirtTest,
    testflow,
    tier1,
    tier2,
    tier3,
)
from fixtures import (
    create_vm_pool, add_user,
    stop_pool_vms_safely_before_removal,
    vm_pool_teardown  # flake8: noqa
)
import helpers

logger = logging.getLogger("virt.vm_pools.prestarted_vms")


@pytest.mark.usefixtures(
    create_vm_pool.__name__, stop_pool_vms_safely_before_removal.__name__
)
class TestAdminStartVmAndPrestartedVms(VirtTest):
    """
    Tests that the running VMs in the pool amount to VMs started by admin +
    pre-started VMs.
    """
    __test__ = True

    pool_name = 'Virt_admin_start_vm_and_prestarted_vms'
    pool_params = copy.deepcopy(config.VM_POOLS_PARAMS)
    pool_params['size'] = 3
    admin_started_vms = 1
    updated_prestarted = 2

    @tier2
    @polarion("RHEVM3-9860")
    def test_add_vm_and_increase_prestarted_vms(self):
        """
        Tests that the running VMs in the pool amount to VMs started by admin +
        pre-started VMs:

        1. Start 1 vm from the pool as admin.
        2. Update vm pool and set the amount of prestarted vms in pool to 2.
        3. Verify that 3 vms are running in pool. 2 (pre started) are stateless
        and 1 is stateful.
        """
        first_vm = ll_vmpools.get_vms_in_pool_by_name(self.pool_name)[0]
        testflow.step("Start a vm in pool: %s as admin", self.pool_name)
        assert ll_vms.startVm(True, first_vm)
        testflow.step(
            "Update vm pool: %s and set number of prestarted vms to: %s",
            self.pool_name, self.updated_prestarted
        )
        helpers.update_prestarted_vms(
            self.pool_name, self.updated_prestarted, self.admin_started_vms
        )


@pytest.mark.usefixtures(
    create_vm_pool.__name__, stop_pool_vms_safely_before_removal.__name__,
    add_user.__name__,

)
class TestPoolSizeMoreThanPrestartedUserTakeVms(VirtTest):
    """
    This test checks the scenario where we have X vms in the pool, Y of them
    are prestarted s.t. X > Y. User takes U <= Y vms then at the end we should
    have U vms running with user permissions + min{X - U, Y} prestarted
    """

    __test__ = True

    pool_name = "Virt_pool_size_more_than_prestarted_user_take_vms"
    pool_params = copy.deepcopy(config.VM_POOLS_PARAMS)
    pool_params['size'] = 5
    pool_params['max_user_vms'] = pool_params['size']
    pool_params['prestarted_vms'] = 2
    users = [config.USER]
    user_vms = 2

    @tier3
    @polarion("RHEVM3-9861")
    def test_pool_size_more_than_prestarted_user_take_vms(self):
        """
        Checks the scenario where there are less prestarted vms than total
        amount of vms in the pool, and that a new vm is started when a user
        takes one of the prestarted vms:

        1. Vm pool is set to 2 prestarted vms (out of 5 in this case).
        2. Wait for 2 prestarted vms to start.
        3. Allocate 2 vms for user1.
        4. Verify that there are 2 vms for user1 and 2 other prestarted vms.
        """
        testflow.step(
            "Waiting for %s prestarted vms to start from pool: %s",
            self.pool_params['prestarted_vms'], self.pool_name
        )
        hl_vmpools.wait_for_prestarted_vms(vm_pool=self.pool_name)
        testflow.step(
            "Allocating %s vms from pool: %s as user %s",
            self.user_vms, self.pool_name, config.USER
        )
        helpers.allocate_vms_as_user(
            True, self.pool_name, config.USER, 0, self.user_vms
        )
        testflow.step(
            "Waiting for %s prestarted vms to start from pool: %s",
            self.pool_params['prestarted_vms'], self.pool_name
        )
        hl_vmpools.wait_for_prestarted_vms(
            vm_pool=self.pool_name, running_vms=self.user_vms
        )


@pytest.mark.usefixtures(
    create_vm_pool.__name__, stop_pool_vms_safely_before_removal.__name__,
    add_user.__name__,
)
class TestPoolSizeMoreThanPrestartedUserAndAdminTakeVms(VirtTest):
    """
    This test checks the scenario where we have X vms in the pool, Y of them
    are prestarted s.t. X > Y. User takes U <= Y vms. Admin takes A <= Y vms.
    then at the end we should have U vms running with user permissions + A vms
    running with normal permissions + min{X - U - A, Y} prestarted
    """

    __test__ = True

    pool_name = "Virt_pool_size_more_than_prestarted_user_and_admin"
    pool_params = copy.deepcopy(config.VM_POOLS_PARAMS)
    pool_params['size'] = 5
    pool_params['max_user_vms'] = pool_params['size']
    pool_params['prestarted_vms'] = 2
    users = [config.USER]
    user_vms = 2
    admin_vms = 1

    @tier3
    @polarion("RHEVM3-9862")
    def test_pool_size_more_than_prestarted_user_and_admin_take_vms(self):
        """
        Checks the scenario where there are less prestarted vms than total
        amount of vms in the pool, and that a new vm is started when a user
        takes one of the prestarted vms and admin starts another vm:

        1. Vm pool is set to 2 prestarted vms (out of 5 in this case).
        2. Wait for 2 prestarted vms to start.
        3. Allocate 2 vms for user1.
        4. Verify that there are 2 vms for user1 and 2 other prestarted vms.
        5. Start a vm from the pool as admin.
        6. Verify that there are 2 vms for user1, 1 running stateful vm (admin)
        and 2 other prestarted vms (stateless).
        """
        testflow.step(
            "Waiting for %s prestarted vms to start from pool: %s",
            self.pool_params['prestarted_vms'], self.pool_name
        )
        hl_vmpools.wait_for_prestarted_vms(vm_pool=self.pool_name)
        testflow.step(
            "Allocating %s vms from pool: %s as user %s",
            self.user_vms, self.pool_name, config.USER
        )
        helpers.allocate_vms_as_user(
            True, self.pool_name, config.USER, 0, self.user_vms
        )
        hl_vmpools.wait_for_prestarted_vms(
            vm_pool=self.pool_name, running_vms=2
        )
        testflow.step(
            "Starting %s vms from pool: %s as admin",
            self.admin_vms, self.pool_name
        )
        hl_vmpools.start_vms(self.pool_name, self.admin_vms)
        testflow.step(
            "expecting %s prestarted vms + %s user  + %s admin vms running in "
            "pool: %s", self.pool_params['prestarted_vms'], self.user_vms,
            self.admin_vms, self.pool_name
        )
        hl_vmpools.wait_for_prestarted_vms(
            vm_pool=self.pool_name, running_vms=self.user_vms + self.admin_vms
        )


@pytest.mark.usefixtures(
    create_vm_pool.__name__, stop_pool_vms_safely_before_removal.__name__,
    add_user.__name__,
)
class TestUserTakeAllPrestartedVmsFromPool(VirtTest):
    """
    This test checks the scenario where all the vms in the pool are prestarted.
    User takes all the Vms in the pool. At the end we should verify that
    VmPoolMonitor finds no more available vms for prestarting
    """

    __test__ = True

    pool_name = "Virt_user_take_all_prestarted_vms_from_pool"
    pool_params = copy.deepcopy(config.VM_POOLS_PARAMS)
    pool_params['max_user_vms'] = pool_params['size']
    pool_params['prestarted_vms'] = 2
    users = [config.USER]
    user_vms = 2

    @tier2
    @polarion("RHEVM3-9871")
    def test_user_take_all_prestarted_vms_from_pool(self):
        """
        This test checks the scenario where all the vms in the pool are
        prestarted.
        User takes all the Vms in the pool. At the end we should verify that
        VmPoolMonitor finds no more available vms for prestarting:

        1. Vm pools is set with prestarted vms == total vms in pool.
        2. Wait for prestarted vms to start.
        3. Allocate all the vms in the pool.
        4. After VmPoolMonitorInterval minutes verify the correct message is
        issued regarding no available vms to prestart in the pool.

        """
        testflow.step(
            "Waiting for %s prestarted vms to start from pool: %s",
            self.pool_params['prestarted_vms'], self.pool_name
        )
        hl_vmpools.wait_for_prestarted_vms(
            vm_pool=self.pool_name, wait_until_up=True
        )
        testflow.step(
            "Allocating %s vms from pool: %s as user %s",
            self.user_vms, self.pool_name, config.USER
        )
        helpers.allocate_vms_as_user(
            True, self.pool_name, config.USER, 0, self.user_vms
        )
        testflow.step(
            "Waiting for vm pool monitor to recognize no more vms are "
            "avialable to prestart in pool: %s", self.pool_name
        )
        helpers.wait_for_no_available_prestarted_vms(
            self.pool_name, self.pool_params['prestarted_vms']
        )


@pytest.mark.usefixtures(
    create_vm_pool.__name__, stop_pool_vms_safely_before_removal.__name__
)
class TestUpdatePoolWithPrestartedVms(VirtTest):
    """
    Tests update of prestarted_vms paramter value in pool.
    """
    __test__ = True

    pool_name = 'Virt_vmpool_update_prestarted'
    pool_params = copy.deepcopy(config.VM_POOLS_PARAMS)
    pool_params['size'] = 3
    update_prestarted_vms = 2

    @tier1
    @polarion("RHEVM3-9873")
    def test_update_vm_pool_with_prestarted_vms(self):
        """
        Tests update of prestarted_vms parameter value in pool:

        1. Set number of prestarted vms to 2.
        2. Verify 2 vms from the pool were started after VmPoolMonitorInterval.
        """
        testflow.step(
            "Update the number of prestarted vms in pool: %s", self.pool_name
        )
        helpers.update_prestarted_vms(
            self.pool_name, self.update_prestarted_vms
        )


@pytest.mark.usefixtures(create_vm_pool.__name__)
class TestUpdatePoolWithTooManyPrestartedVms(VirtTest):
    """
    Negative - Tests update of prestarted vms parameter with an invalid value.
    """
    __test__ = True

    pool_name = 'Virt_vmpool_invalid_prestarted'
    pool_params = copy.deepcopy(config.VM_POOLS_PARAMS)
    updated_prestarted_vms = 3

    @tier3
    @polarion("RHEVM3-12740")
    def test_create_pool_with_too_many_prestarted_vms(self):
        """
        Negative - update of prestarted vms parameter with an invalid value:

        1. Attempt to set number of prestarted vms to 3 - should fail (there
        are only 2 vms in the pool).
        """
        testflow.step(
            "Update the number of prestarted vms in pool: %s to a value "
            "higher than pool's size", self.pool_name
        )
        if not ll_vmpools.updateVmPool(
            False,
            self.pool_name,
            prestarted_vms=self.updated_prestarted_vms
        ):
            raise exceptions.VmPoolException()
