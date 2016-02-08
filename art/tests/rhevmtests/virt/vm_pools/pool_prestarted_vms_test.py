#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
prestarted vms test - features test cases concerning prestarted vm in the pool.
"""

import config
import logging
from rhevmtests.virt.vm_pools import (
    vm_pool_base as base,
    helpers,
)
from art.rhevm_api.tests_lib.high_level import vmpools as hl_vmpools
from art.rhevm_api.tests_lib.low_level import vms as ll_vms
from art.test_handler import exceptions
from art.test_handler.tools import polarion  # pylint: disable=E0611
from art.unittest_lib import attr

logger = logging.getLogger("virt.vm_pools.prestarted_vms")


@attr(tier=2)
class TestAdminStartVmAndPrestartedVms(base.VmPool):
    """
    Tests that the running VMs in the pool amount to VMs started by admin +
    pre-started VMs.
    """
    __test__ = True

    pool_name = 'Virt_admin_start_vm_and_prestarted_vms'
    pool_size = 3
    admin_started_vms = 1
    prestarted_vms = 2

    @polarion("RHEVM-9860")
    def test_add_vm_and_increase_prestarted_vms(self):
        """
        Tests that the running VMs in the pool amount to VMs started by admin +
        pre-started VMs:

        1. Start 1 vm from the pool as admin.
        2. Update vm pool and set the amount of prestarted vms in pool to 2.
        3. Verify that 3 vms are running in pool. 2 (pre started) are stateless
        and 1 is stateful.
        """
        first_vm = base.ll_vmpools.get_vms_in_pool_by_name(self.pool_name)[0]
        self.assertTrue(ll_vms.startVm(True, first_vm))
        helpers.update_prestarted_vms(
            self.pool_name, self.prestarted_vms, self.admin_started_vms
        )


class TestPoolSizeMoreThanPrestartedUserTakeVms(base.VmPoolWithUser):
    """
    This test checks the scenario where we have X vms in the pool, Y of them
    are prestarted s.t. X > Y. User takes U <= Y vms then at the end we should
    have U vms running with user permissions + min{X - U, Y} prestarted
    """

    __test__ = True

    pool_name = "Virt_pool_size_more_than_prestarted_user_take_vms"
    pool_size = 5
    max_vms_per_user = pool_size
    prestarted_vms = 2
    user_vms = 2

    @polarion("RHEVM-9861")
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
        hl_vmpools.wait_for_prestarted_vms(vm_pool=self.pool_name)
        helpers.allocate_vms_as_user(
            True, self.pool_name, config.USER, 0, self.user_vms
        )
        hl_vmpools.wait_for_prestarted_vms(
            vm_pool=self.pool_name, running_vms=self.user_vms
        )


class TestPoolSizeMoreThanPrestartedUserAndAdminTakeVms(base.VmPoolWithUser):
    """
    This test checks the scenario where we have X vms in the pool, Y of them
    are prestarted s.t. X > Y. User takes U <= Y vms. Admin takes A <= Y vms.
    then at the end we should have U vms running with user permissions + A vms
    running with normal permissions + min{X - U - A, Y} prestarted
    """

    __test__ = True

    pool_name = "Virt_pool_size_more_than_prestarted_user_and_admin"
    pool_size = 5
    max_vms_per_user = pool_size
    prestarted_vms = 2
    user_vms = 2
    admin_vms = 1

    @polarion("RHEVM-9862")
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
        hl_vmpools.wait_for_prestarted_vms(vm_pool=self.pool_name)
        helpers.allocate_vms_as_user(
            True, self.pool_name, config.USER, 0, self.user_vms
        )
        hl_vmpools.wait_for_prestarted_vms(
            vm_pool=self.pool_name, running_vms=2
        )
        hl_vmpools.start_vms(self.pool_name, self.admin_vms)
        logger.info(
            "expecting %s prestarted vms + %s user  + %s admin vms running in "
            "pool: %s", self.prestarted_vms, self.user_vms, self.admin_vms,
            self.pool_name
        )
        hl_vmpools.wait_for_prestarted_vms(
            vm_pool=self.pool_name, running_vms=self.user_vms + self.admin_vms
        )


class TestUserTakeAllPrestartedVmsFromPool(base.VmPoolWithUser):
    """
    This test checks the scenario where all the vms in the pool are prestarted.
    User takes all the Vms in the pool. At the end we should verify that
    VmPoolMonitor finds no more available vms for prestarting
    """

    __test__ = True

    pool_name = "Virt_user_take_all_prestarted_vms_from_pool"
    max_vms_per_user = base.VmPoolWithUser.pool_size
    prestarted_vms = 2
    user_vms = 2

    @polarion("RHEVM-9871")
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
        hl_vmpools.wait_for_prestarted_vms(
            vm_pool=self.pool_name, wait_until_up=True
        )
        helpers.allocate_vms_as_user(
            True, self.pool_name, config.USER, 0, self.user_vms
        )
        helpers.wait_for_no_available_prestarted_vms(
            self.pool_name, self.prestarted_vms
        )


class TestUpdatePoolWithPrestartedVms(base.VmPool):
    """
    Tests update of prestarted_vms paramter value in pool.
    """
    __test__ = True

    pool_name = 'Virt_vmpool_update_prestarted'
    pool_size = 3
    prestarted_vms = 2

    @polarion("RHEVM3-9873")
    def test_update_vm_pool_with_prestarted_vms(self):
        """
        Tests update of prestarted_vms paramter value in pool:

        1. Set number of prestarted vms to 2.
        2. Verify 2 vms from the pool were started after VmPoolMonitorInterval.
        """
        helpers.update_prestarted_vms(self.pool_name, self.prestarted_vms)


@attr(tier=2)
class TestUpdatePoolWithTooManyPrestartedVms(base.VmPool):
    """
    Negative - Tests update of prestarted vms parametr with an invalid value.
    """
    __test__ = True

    pool_name = 'Virt_vmpool_invalid_prestarted'
    updated_prestarted_vms = 3

    @polarion("RHEVM3-12740")
    def test_create_pool_with_too_many_prestarted_vms(self):
        """
        Negative - update of prestarted vms parametr with an invalid value:

        1. Attempt to set number of prestarted vms to 3 - should fail (there
        are only 2 vms in the pool).
        """
        if not base.ll_vmpools.updateVmPool(
            False,
            self.pool_name,
            prestarted_vms=self.updated_prestarted_vms
        ):
            raise exceptions.VmPoolException()
