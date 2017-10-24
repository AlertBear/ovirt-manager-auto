#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Max vms per user test - features test cases concerning max_vms_per_user
parameter and behaviour it invokes.
"""

import copy
import logging

import pytest

import art.rhevm_api.tests_lib.high_level.vmpools as hl_vmpools
import art.rhevm_api.tests_lib.low_level.vmpools as ll_vmpools
import config
from art.test_handler import exceptions
from art.test_handler.tools import polarion
from art.unittest_lib import VirtTest, testflow
from art.unittest_lib import (
    tier1,
    tier2,
    tier3,
)
from fixtures import (
    create_vm_pool, add_user, vm_pool_teardown
)
import helpers

logger = logging.getLogger("virt.vm_pools.max_vms_per_user")


@pytest.mark.usefixtures(vm_pool_teardown.__name__)
class TestCreatePoolSetNumberOfVmsPerUser(VirtTest):
    """
    Tests vm pool creation with max_vms_per_user parameter set
    """

    __test__ = True

    pool_name = 'Virt_vmpool_create_max_user_vms'
    pool_params = copy.deepcopy(config.VM_POOLS_PARAMS)
    pool_params['max_user_vms'] = 3

    @tier1
    @polarion("RHEVM3-9865")
    def test_create_pool_set_number_of_vms_per_user(self):
        """
        Tests vm pool creation with max_vms_per_user parameter set:
        Create vm with max number of vms per user parameter set to 3.
        """
        testflow.step("Creating vm pool: %s", self.pool_name)
        hl_vmpools.create_vm_pool(True, self.pool_name, self.pool_params)
        testflow.step(
            "Checking that vm pool was created with the correct value for "
            "max_user_vms. Expecting: %s", self.pool_params['max_user_vms']
        )
        actual_max_user_vms = ll_vmpools.get_vm_pool_max_user_vms(
            self.pool_name
        )
        if not self.pool_params['max_user_vms'] == actual_max_user_vms:
            raise exceptions.VmPoolException(
                "Expected max number of vms per user to be %d, got %d" % (
                    self.max_vms_per_user, actual_max_user_vms
                )
            )


@pytest.mark.usefixtures(vm_pool_teardown.__name__)
class TestCreatePoolSetInvalidNumberOfVmsPerUser(VirtTest):
    """
    Negative - tests vm pool creation with invalid max_vms_per_user
    parameter value
    """

    __test__ = True

    pool_name = 'Virt_vmpool_create_invalid_max_user_vms'
    pool_params = copy.deepcopy(config.VM_POOLS_PARAMS)
    pool_params['max_user_vms'] = -1

    @tier3
    @polarion("RHEVM3-9864")
    def test_create_pool_set_invalid_number_of_vms_per_user(self):
        """
        Negative - tests vm pool creation with invalid max_vms_per_user
        parameter value
        """
        testflow.step(
            "Attempting to create a vm pool with an invalid value for "
            "max_user_vms"
        )
        hl_vmpools.create_vm_pool(False, self.pool_name, self.pool_params)


@pytest.mark.usefixtures(create_vm_pool.__name__)
class TestUpdatePoolNumberOfVmsPerUser(VirtTest):
    """
    Tests vm pool update max_vms_per_user parameter value
    """

    __test__ = True

    pool_name = 'Virt_vmpool_update_max_user_vms'
    pool_params = copy.deepcopy(config.VM_POOLS_PARAMS)
    new_max_user_vms = 3

    @tier1
    @polarion("RHEVM3-9866")
    def test_update_pool_number_of_vms_per_user(self):
        """
        Tests vm pool update max_vms_per_user parameter value
        """
        testflow.step("Updating the value of max_user_vms in the vm pool")
        assert ll_vmpools.updateVmPool(
            positive=True,
            vmpool=self.pool_name,
            max_user_vms=self.new_max_user_vms
        )
        testflow.step(
            "Checking that vm pool was updated with the correct value for "
            "max_user_vms. Expecting: %s", self.pool_params['max_user_vms']
        )
        actual_max_user_vms = ll_vmpools.get_vm_pool_max_user_vms(
            self.pool_name
        )
        if not self.new_max_user_vms == actual_max_user_vms:
            raise exceptions.VmPoolException(
                "Expected max number of vms per user to be %d, got %d" % (
                    self.new_max_user_vms,
                    actual_max_user_vms
                )
            )


@pytest.mark.usefixtures(create_vm_pool.__name__)
class TestUpdatePoolWithInvalidNumberOfVmsPerUser(VirtTest):
    """
    Negative - tests vm pool update with invalid max_vms_per_user parameter
    value
    """

    __test__ = True

    pool_name = 'Virt_vmpool_update_invalid_max_user_vms'
    pool_params = copy.deepcopy(config.VM_POOLS_PARAMS)
    new_max_user_vms = -1

    @tier3
    @polarion("RHEVM3-9867")
    def test_update_pool_with_invalid_number_of_vms_per_user(self):
        """
        Negative - tests vm pool update with invalid max_vms_per_user parameter
        value
        """
        testflow.step(
            "Updating the value of max_user_vms in the vm pool with an "
            "invalid value"
        )
        if not ll_vmpools.updateVmPool(
            positive=False,
            vmpool=self.pool_name,
            max_user_vms=self.new_max_user_vms
        ):
            raise exceptions.VmPoolException()


@pytest.mark.usefixtures(
    create_vm_pool.__name__, add_user.__name__
)
class TestMaxVmsPerUserAsUser(VirtTest):
    """
    Tests max_vms_per_user constraint on actual user
    """

    __test__ = True

    pool_name = "Virt_max_vms_per_user_as_user_pool"
    pool_params = copy.deepcopy(config.VM_POOLS_PARAMS)
    pool_params['max_user_vms'] = 1
    pool_params['size'] = 3
    updated_max_vms_per_user = 2
    users = [config.USER]

    @tier2
    @polarion("RHEVM3-14383")
    def test_max_vms_per_user_as_user(self):
        """
        Tests max_vms_per_user constraint on actual user:

        1. Allocate vm as user1.
        2. Fail to allocate another vm as user1 max_vms_per_user is set to 1.
        3. Update vm pool: set max_vms_per_user to 2.
        4. Allocate a 2nd vm as user1.
        5. Fail to allocate a 3rd vm as user1 max_vms_per_user is set to 2.
        """
        testflow.step(
            "Allocating 1 vm from pool: %s as user %s",
            self.pool_name, config.USER
        )
        helpers.allocate_vms_as_user(True, self.pool_name, config.USER, 0, 1)
        testflow.step(
            "Attempting to allocate another vm from pool: %s as user %s."
            "Should fail as max_user_vms value in the pool is 1",
            self.pool_name, config.USER
        )
        helpers.allocate_vms_as_user(False, self.pool_name, config.USER, 1, 1)
        testflow.step(
            "Updating the value of max_user_vms in the vm pool to: %s",
            self.updated_max_vms_per_user
        )
        if not ll_vmpools.updateVmPool(
            positive=True,
            vmpool=self.pool_name,
            max_user_vms=self.updated_max_vms_per_user
        ):
            raise exceptions.VmPoolException()
        testflow.step(
            "Attempting to allocate another vm from pool: %s as user %s.",
            self.pool_name, config.USER
        )
        helpers.allocate_vms_as_user(True, self.pool_name, config.USER, 1, 1)
        testflow.step(
            "Attempting to allocate another vm from pool: %s as user %s."
            "Should fail as max_user_vms value in the pool is %s",
            self.pool_name, config.USER, self.updated_max_vms_per_user
        )
        helpers.allocate_vms_as_user(False, self.pool_name, config.USER, 2, 1)
