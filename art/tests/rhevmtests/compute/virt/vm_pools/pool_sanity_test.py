#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Vm pools sanity test - contains basic test cases covering base functionality of
vm pools.
"""

import copy
import logging

import pytest

import config
import rhevmtests.compute.virt.helper as helper
import rhevmtests.helpers as gen_helper
from art.rhevm_api.tests_lib.high_level import (
    vmpools as hl_vmpools,
    vms as hl_vms,
)
from art.rhevm_api.tests_lib.low_level import (
    vms as ll_vms,
    vmpools as ll_vmpools,
)
from art.test_handler import exceptions
from art.test_handler.tools import polarion
from art.unittest_lib import VirtTest, testflow
from art.unittest_lib import (
    tier1,
    tier2,
)
from fixtures import (
    vm_pool_teardown, create_vm_pool, add_user, set_cluster_mac_pool,
    stop_pool_vms_safely_before_removal
)
import helpers

logger = logging.getLogger("virt.vm_pools.sanity")


@pytest.mark.usefixtures(vm_pool_teardown.__name__)
class TestFullCreateRemovePoolCycle(VirtTest):
    """
    This test covers the basic vm pool flow not using the deleteVmPool
    function which handles stop vms -> detach vms -> delete vms -> delete pool
    in engine, but doing this process step by step.
    """

    __test__ = True

    pool_name = 'Virt_vmpool_full_cycle'
    pool_params = copy.deepcopy(config.VM_POOLS_PARAMS)

    @tier1
    @polarion("RHEVM3-13976")
    def test_full_create_remove_pool_cycle(self):
        """
        This test covers the basic vm pool flow: create pool -> start vms in
        pool -> stop vms in pool -> detach vms from pool -> delete vms ->
        delete pool.
        """
        testflow.step(
            "Creating a vm pool with params: %s", self.pool_params
        )
        hl_vmpools.create_vm_pool(True, self.pool_name, self.pool_params)
        testflow.step("Starting all vms in pool: %s", self.pool_name)
        if not hl_vmpools.start_vm_pool(self.pool_name):
            raise exceptions.VmPoolException()
        testflow.step("Removing pool: %s", self.pool_name)
        if not hl_vmpools.remove_whole_vm_pool(
            self.pool_name, stop_vms=True
        ):
            raise exceptions.VmPoolException()


@pytest.mark.usefixtures(create_vm_pool.__name__)
class TestAddVmsToPool(VirtTest):
    """
    Tests add vm to pool by updating pool and increasing pool size.
    """
    __test__ = True

    pool_name = 'Virt_vmpool_add_to_pool'
    pool_params = copy.deepcopy(config.VM_POOLS_PARAMS)
    new_pool_size = 3

    @tier1
    @polarion("RHEVM3-9870")
    def test_add_vms_to_pool(self):
        """
        Tests add vm to pool by updating pool and increasing pool size.
        """
        testflow.step("Updating number of vms in pool: %s", self.pool_name)
        if not ll_vmpools.updateVmPool(
            True,
            self.pool_name,
            size=self.new_pool_size
        ):
            raise exceptions.VmPoolException()
        vms_in_pool = helpers.generate_vms_name_list_from_pool(
            self.pool_name,
            self.new_pool_size
        )
        testflow.step("Searching for the new vm: %s", vms_in_pool[-1])
        ll_vms.get_vm(vms_in_pool[-1])
        if not ll_vms.waitForVmsStates(
            True,
            vms_in_pool[-1],
            states=config.VM_DOWN
        ):
            raise exceptions.VMException(
                "vm: %s has wrong status after creation. Expected: %s" %
                (vms_in_pool[-1], config.VM_DOWN)
            )


@pytest.mark.usefixtures(create_vm_pool.__name__)
class TestAdminStartedVmNotStateless(VirtTest):
    """
    Test case verifies that a vm from pool started by admin is stateful.
    """
    __test__ = True

    pool_name = "Virt_pool_admin_started_vm_not_stateless"
    pool_params = copy.deepcopy(config.VM_POOLS_PARAMS)

    @tier2
    @polarion("RHEVM3-9880")
    def test_admin_started_vm_not_stateless(self):
        """
        Test case verifies that a vm from pool started by admin is stateful.
        """
        vm = ll_vmpools.get_vms_in_pool_by_name(self.pool_name)[0]
        testflow.step("Start a vm from pool: %s", self.pool_name)
        assert ll_vms.startVm(True, vm)
        vm_resource = gen_helper.get_vm_resource(vm)
        testflow.step("Create a file in the vm")
        helper.create_file_in_vm(vm, vm_resource)
        testflow.step("Make sure the file exists in the vm's disk")
        helper.check_if_file_exist(True, vm, vm_resource)
        assert helpers.flush_file_system_buffers(vm_resource)
        testflow.step("Restart the vm (shutdown and start again)")
        assert ll_vms.stop_vms_safely([vm])
        assert ll_vms.startVm(True, vm, wait_for_status=config.VM_UP)
        vm_resource = gen_helper.get_vm_resource(vm)
        testflow.step("Verify that file exists after vm restart")
        helper.check_if_file_exist(True, vm, vm_resource)


@pytest.mark.usefixtures(
    create_vm_pool.__name__, stop_pool_vms_safely_before_removal.__name__,
    add_user.__name__,
)
class TestUserStartedVmIsStateless(VirtTest):
    """
    Test case verifies that a vm from pool started by a user with pool user
    permissions is stateless.
    """
    __test__ = True

    pool_name = "Virt_pool_user_started_vm_is_stateless"
    pool_params = copy.deepcopy(config.VM_POOLS_PARAMS)
    pool_params['size'] = 1
    users = [config.USER, config.VDC_ADMIN_USER]
    pool_size = 1

    @tier2
    @polarion("RHEVM3-9878")
    def test_user_started_vm_is_stateless(self):
        """
        Test case verifies that a vm from pool started by a user with pool user
        permissions is stateless.
        """
        testflow.step(
            "Allocating a vm from pool: %s as user %s",
            self.pool_name, config.USER
        )
        helpers.allocate_vms_as_user(True, self.pool_name, config.USER, 0, 1)
        vm = ll_vmpools.get_vms_in_pool_by_name(self.pool_name)[0]
        vm_resource = gen_helper.get_vm_resource(vm)
        testflow.step("Creating a file in vm: %s", vm)
        helper.create_file_in_vm(vm, vm_resource)
        testflow.step("Verifying file exists in vm: %s", vm)
        helper.check_if_file_exist(True, vm, vm_resource)
        testflow.step("Stopping vm: %s", vm)
        hl_vms.stop_stateless_vm(vm)
        testflow.step(
            "Allocating vm: %s from pool: %s as user %s",
            vm, self.pool_name, config.USER
        )
        helpers.allocate_vms_as_user(
            True, self.pool_name, config.VDC_ADMIN_USER, 0, 1
        )
        vm_resource = gen_helper.get_vm_resource(vm)
        testflow.step(
            "Verifying that the file created in the previous session does not "
            "exist as vm is stateless"
        )
        helper.check_if_file_exist(False, vm, vm_resource)


@pytest.mark.usefixtures(
    set_cluster_mac_pool.__name__, create_vm_pool.__name__
)
class TestNoMacAddressDuplicationBetweenPools(VirtTest):
    """
    Test case is basd on bug#1395462 and verifies that different vm pools
    don't cause duplication of mac address between vms
    """

    __test__ = True

    pool_name = ["Virt_pool_%s_same_mac" % i for i in range(1, 4)]
    pool_params = copy.deepcopy(config.VM_POOLS_PARAMS)
    pool_params['size'] = 20

    @tier2
    @polarion("RHEVM-18288")
    def test_no_mac_address_duplication_between_pools(self):
        """
        Test case is basd on bug#1395462 and verifies that different vm pools
        don't cause duplication of mac address between vms
        """
        testflow.step(
            "Getting all mac addresses from vms created within vm pools: %s",
            self.pool_name
        )
        all_mac_from_pool_vms = [
            ll_vms.get_vm_nic_mac_address(vm) for pool in self.pool_name
            for vm in ll_vmpools.get_vms_in_pool_by_name(pool)
            ]
        testflow.step("Verifying that no mac address appears more than once")
        for mac in all_mac_from_pool_vms:
            assert not all_mac_from_pool_vms.count(mac) > 1
