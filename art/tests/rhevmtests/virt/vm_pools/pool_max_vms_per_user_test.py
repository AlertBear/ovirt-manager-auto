#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Max vms per user test - features test cases concerning max_vms_per_user
parameter and behaviour it invokes.
"""

import config
import logging
from rhevmtests.virt.vm_pools import (
    vm_pool_base as base,
    helpers,
)
import art.rhevm_api.tests_lib.high_level.vmpools as hl_vmpools
from art.test_handler import exceptions
from art.test_handler.tools import polarion, bz
from art.unittest_lib import attr

logger = logging.getLogger("virt.vm_pools.max_vms_per_user")


class TestCreatePoolSetNumberOfVmsPerUser(base.BaseVmPool):
    """
    Tests vm pool creation with max_vms_per_user parameter set
    """

    __test__ = True

    pool_name = 'Virt_vmpool_create_max_user_vms'
    max_vms_per_user = 3

    @polarion("RHEVM3-9865")
    def test_create_pool_set_number_of_vms_per_user(self):
        """
        Tests vm pool creation with max_vms_per_user parameter set:
        Create vm with max number of vms per user parameter set to 3.
        """
        hl_vmpools.create_vm_pool(True, self.pool_name, self.pool_params)
        if not (
            self.max_vms_per_user == (
                base.ll_vmpools.get_vm_pool_max_user_vms(
                    self.pool_name
                )
            )
        ):
            raise exceptions.VmPoolException(
                "Expected max number of vms per user to be %d, got %d" % (
                    self.new_max_user_vms,
                    self.max_vms_per_user
                )
            )


@attr(tier=2)
class TestCreatePoolSetInvalidNumberOfVmsPerUser(base.BaseVmPool):
    """
    Negative - tests vm pool creation with invalid max_vms_per_user
    parameter value
    """

    __test__ = True

    max_vms_per_user = -1
    pool_name = 'Virt_vmpool_create_invalid_max_user_vms'

    @polarion("RHEVM3-9864")
    def test_create_pool_set_invalid_number_of_vms_per_user(self):
        """
        Negative - tests vm pool creation with invalid max_vms_per_user
        parameter value
        """
        hl_vmpools.create_vm_pool(False, self.pool_name, self.pool_params)


class TestUpdatePoolNumberOfVmsPerUser(base.VmPool):
    """
    Tests vm pool update max_vms_per_user parameter value
    """

    __test__ = True

    pool_name = 'Virt_vmpool_update_max_user_vms'
    new_max_user_vms = 3

    @polarion("RHEVM3-9866")
    def test_update_pool_number_of_vms_per_user(self):
        """
        Tests vm pool update max_vms_per_user parameter value
        """
        if not base.ll_vmpools.updateVmPool(
            positive=True,
            vmpool=self.pool_name,
            max_user_vms=self.new_max_user_vms
        ):
            raise exceptions.VmPoolException()
        if not (
            self.new_max_user_vms == (
                base.ll_vmpools.get_vm_pool_max_user_vms(
                    self.pool_name
                )
            )
        ):
            raise exceptions.VmPoolException(
                "Expected max number of vms per user to be %d, got %d" % (
                    self.new_max_user_vms,
                    self.max_vms_per_user
                )
            )


@attr(tier=2)
class TestUpdatePoolWithInvalidNumberOfVmsPerUser(base.VmPool):
    """
    Negative - tests vm pool update with invalid max_vms_per_user parameter
    value
    """

    __test__ = True

    pool_name = 'Virt_vmpool_update_invalid_max_user_vms'
    new_max_user_vms = -1

    @polarion("RHEVM3-9867")
    def test_update_pool_with_invalid_number_of_vms_per_user(self):
        """
        Negative - tests vm pool update with invalid max_vms_per_user parameter
        value
        """
        if not base.ll_vmpools.updateVmPool(
            positive=False,
            vmpool=self.pool_name,
            max_user_vms=self.new_max_user_vms
        ):
            raise exceptions.VmPoolException()


class TestMaxVmsPerUserAsUser(base.VmPoolWithUser):
    """
    Tests max_vms_per_user constraint on actual user
    """

    __test__ = True

    pool_name = "Virt_max_vms_per_user_as_user_pool"
    pool_size = 3
    max_vms_per_user = 1
    updated_max_vms_per_user = 2

    @bz({'1342795': {}})
    @polarion("RHEVM-14383")
    def test_max_vms_per_user_as_user(self):
        """
        Tests max_vms_per_user constraint on actual user:

        1. Allocate vm as user1.
        2. Fail to allocate another vm as user1 max_vms_per_user is set to 1.
        3. Update vm pool: set max_vms_per_user to 2.
        4. Allocate a 2nd vm as user1.
        5. Fail to allocate a 3rd vm as user1 max_vms_per_user is set to 2.
        """
        helpers.allocate_vms_as_user(True, self.pool_name, config.USER, 0, 1)
        helpers.allocate_vms_as_user(False, self.pool_name, config.USER, 1, 1)
        if not base.ll_vmpools.updateVmPool(
            positive=True,
            vmpool=self.pool_name,
            max_user_vms=self.updated_max_vms_per_user
        ):
            raise exceptions.VmPoolException()
        helpers.allocate_vms_as_user(True, self.pool_name, config.USER, 1, 1)
        helpers.allocate_vms_as_user(False, self.pool_name, config.USER, 2, 1)
