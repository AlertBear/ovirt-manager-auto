#! /usr/bin/python
# -*- coding: utf-8 -*-
"""
Fixtures module for CPU hotplug test
"""
import config
import helpers
import pytest
from art.rhevm_api.tests_lib.high_level import (
    vmpools as hl_vmpools,
)
from art.rhevm_api.tests_lib.low_level import (
    vms as ll_vms,
    vmpools as ll_vmpools,
    users as ll_users,
    mla as ll_mla,
)
from art.unittest_lib import testflow


@pytest.fixture(scope='class')
def vm_pool_teardown(request):
    """
    Base teardown for all vm pool test cases
    """
    pool_name = request.node.cls.pool_name

    def fin():
        """
        base finalizer for all vm pool test cases
        """
        ll_vms.stop_vms_safely([config.CPU_HOTPLUG_VM])
        testflow.teardown("Base teardown for VM pool test")
        if ll_vmpools.does_vm_pool_exist(pool_name):
            ll_vmpools.updateVmPool(
                True,
                pool_name,
                prestarted_vms=0
            )
            if config.COMP_VERSION < config.NEW_IMPLEMENTATION_VERSION:
                helpers.wait_for_vm_pool_removed(pool_name)
            else:
                if not ll_vmpools.removeVmPool(True, pool_name, wait=True):
                    helpers.wait_for_vm_pool_removed(pool_name)
    request.addfinalizer(fin)


@pytest.fixture(scope='class')
def create_vm_pool(request, vm_pool_teardown):
    """
    Create a vm pool for current test case
    """
    pool_name = request.node.cls.pool_name
    pool_params = request.node.cls.pool_params
    testflow.setup("Base setup for VM pool test - creating vm pool")
    hl_vmpools.create_vm_pool(True, pool_name, pool_params)


@pytest.fixture(scope='class')
def add_user(request):
    users = request.node.cls.users
    pool_name = request.node.cls.pool_name

    def fin():
        """
        Login back to engine with user=admin.
        Remove users that were added for the test case.
        """
        ll_users.loginAsUser(
            config.VDC_ADMIN_USER,
            config.INTERNAL_DOMAIN,
            config.VDC_PASSWORD,
            False
        )
        for user in users:
            if user is not config.VDC_ADMIN_USER:
                ll_users.removeUser(
                    True, config.USER, config.USER_DOMAIN
                )
    request.addfinalizer(fin)
    for user in users:
        if user is not config.VDC_ADMIN_USER:
            assert ll_users.addExternalUser(
                True, user_name=config.USER, domain=config.USER_DOMAIN
            )
        assert ll_mla.addVmPoolPermissionToUser(
            True, user, pool_name, config.USER_ROLE
        )
