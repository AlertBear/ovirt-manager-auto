#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Vm pools sanity test - contains basic test cases covering base functionality of
vm pools.
"""

import config
import logging
from art.rhevm_api.tests_lib.low_level import (
    vms as ll_vms,
)
from art.rhevm_api.tests_lib.high_level import (
    vmpools as hl_vmpools,
    vms as hl_vms,
)
from art.test_handler import exceptions
from art.test_handler.tools import polarion  # pylint: disable=E0611
from rhevmtests.virt.vm_pools import (
    vm_pool_base as base,
    helpers
)
import rhevmtests.helpers as gen_helper

logger = logging.getLogger("virt.vm_pools.sanity")


class TestFullCreateRemovePoolCycle(base.BaseVmPool):
    """
    This test covers the basic vm pool flow not using the deleteVmPool
    function which handles stop vms -> detach vms -> delete vms -> delete pool
    in engine, but doing this process step by step.
    """

    __test__ = True

    pool_name = 'Virt_vmpool_full_cycle'

    @polarion("RHEVM3-13976")
    def test_full_create_remove_pool_cycle(self):
        """
        This test covers the basic vm pool flow: create pool -> start vms in
        pool -> stop vms in pool -> detach vms from pool -> delete vms ->
        delete pool.
        """
        hl_vmpools.create_vm_pool(True, self.pool_name, self.pool_params)
        if not hl_vmpools.start_vm_pool(self.pool_name):
            raise exceptions.VmPoolException()
        if not hl_vmpools.remove_whole_vm_pool(
            self.pool_name, stop_vms=True
        ):
            raise exceptions.VmPoolException(
                "Failed to remove pool: %s and all it's vms" % self.pool_name
            )


class TestAddVmsToPool(base.VmPool):
    """
    Tests add vm to pool by updating pool and increasing pool size.
    """
    __test__ = True

    pool_name = 'Virt_vmpool_add_to_pool'
    new_pool_size = 3

    @polarion("RHEVM3-9870")
    def test_add_vms_to_pool(self):
        """
        Tests add vm to pool by updating pool and increasing pool size.
        """
        if not base.ll_vmpools.updateVmPool(
            True,
            self.pool_name,
            size=self.new_pool_size
        ):
            raise exceptions.VmPoolException()
        self.__class__.pool_size = self.new_pool_size
        vms_in_pool = helpers.generate_vms_name_list_from_pool(
            self.pool_name,
            self.new_pool_size
        )
        logger.info("Searching for new vm: %s", vms_in_pool[-1])
        ll_vms.get_vm(vms_in_pool[-1])
        logger.info(
            "The new vm: %s was successfully added pool %s",
            vms_in_pool[-1],
            self.pool_name
        )
        if not ll_vms.waitForVmsStates(
            True,
            vms_in_pool[-1],
            states=config.VM_DOWN
        ):
            raise exceptions.VMException(
                "vm: %s has wrong status after creation. Expected: %s" %
                (vms_in_pool[-1], config.VM_DOWN)
            )


class TestAdminStartedVmNotStateless(base.VmPool):
    """
    Test case verifies that a vm from pool started by admin is stateful.
    """
    __test__ = True

    pool_name = "Virt_pool_admin_started_vm_not_stateless"

    @polarion("RHEVM-9880")
    def test_admin_started_vm_not_stateless(self):
        """
        Test case verifies that a vm from pool started by admin is stateful.
        """
        vm = base.ll_vmpools.get_vms_in_pool_by_name(self.pool_name)[0]
        self.assertTrue(ll_vms.startVm(True, vm))
        vm_resource = gen_helper.get_vm_resource(vm)
        helpers.create_file_in_vm(vm, vm_resource)
        helpers.check_if_file_exist(True, vm, vm_resource)
        self.assertTrue(helpers.flush_file_system_buffers(vm_resource))
        self.assertTrue(ll_vms.stop_vms_safely([vm]))
        self.assertTrue(ll_vms.startVm(True, vm, wait_for_status=config.VM_UP))
        vm_resource = gen_helper.get_vm_resource(vm)
        helpers.check_if_file_exist(True, vm, vm_resource)


class TestUserStartedVmIsStateless(base.VmPoolWithUser):
    """
    Test case verifies that a vm from pool started by a user with pool user
    permissions is stateless.
    """
    __test__ = True

    pool_name = "Virt_pool_user_started_vm_is_stateless"
    pool_size = 1

    @polarion("RHEVM-9878")
    def test_user_started_vm_is_stateless(self):
        """
        Test case verifies that a vm from pool started by a user with pool user
        permissions is stateless.
        """
        helpers.allocate_vms_as_user(True, self.pool_name, config.USER, 0, 1)
        vm = base.ll_vmpools.get_vms_in_pool_by_name(self.pool_name)[0]
        vm_resource = gen_helper.get_vm_resource(vm)
        helpers.create_file_in_vm(vm, vm_resource)
        helpers.check_if_file_exist(True, vm, vm_resource)
        hl_vms.stop_stateless_vm(vm)
        helpers.allocate_vms_as_user(
            True, self.pool_name, config.VDC_ADMIN_USER, 0, 1
        )
        vm_resource = gen_helper.get_vm_resource(vm)
        helpers.check_if_file_exist(False, vm, vm_resource)
