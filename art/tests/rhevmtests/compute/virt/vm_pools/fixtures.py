#! /usr/bin/python
# -*- coding: utf-8 -*-
"""
Fixtures module for CPU hotplug test
"""
import pytest

import config
import helpers
from art.rhevm_api.tests_lib.high_level import (
    vmpools as hl_vmpools,
    mac_pool as hl_mac_pool
)
from art.rhevm_api.tests_lib.low_level import (
    vms as ll_vms,
    vmpools as ll_vmpools,
    users as ll_users,
    mla as ll_mla,
    mac_pool as ll_mac_pool,
)
from art.unittest_lib import testflow
from utilities.utils import MAC


@pytest.fixture(scope='class')
def vm_pool_teardown(request):
    """
    Base teardown for all vm pool test cases
    """
    pool_name = request.node.cls.pool_name
    pool_name = [pool_name] if isinstance(pool_name, str) else pool_name

    def fin():
        """
        base finalizer for all vm pool test cases
        """
        testflow.teardown("Base teardown for VM pool test")
        for pool in pool_name:
            if ll_vmpools.does_vm_pool_exist(pool):
                if config.COMP_VERSION < config.NEW_IMPLEMENTATION_VERSION:
                    helpers.wait_for_vm_pool_removed(pool)
                else:
                    if not ll_vmpools.removeVmPool(True, pool, wait=True):
                        helpers.wait_for_vm_pool_removed(pool)
    request.addfinalizer(fin)


@pytest.fixture(scope='class')
def stop_pool_vms_safely_before_removal(request):
    """
    Stops the vms in the pool safely before removing the pool.
    This fixture is used when a stateless pool has running vms which require
    a stateless snapshot to be restored when they are stopped
    """
    pool_name = request.node.cls.pool_name

    def fin():
        """
        Stops all vms in the pool safely
        """
        if ll_vmpools.get_vm_pool_number_of_prestarted_vms(
            pool_name
        ):
            testflow.teardown(
                "Canceling prestarted vms setting for pool: %s", pool_name
            )
            assert ll_vmpools.updateVmPool(True, pool_name, prestarted_vms=0)
        testflow.teardown(
            "Removing userRole permissions for user Admin from vms in "
            "pool: %s", pool_name
        )
        if ll_vmpools.get_vm_pool_type(pool_name) == config.POOL_TYPE_MANUAL:
            for vm in helpers.get_user_vms(
                pool_name, config.ADMIN_USER_NAME, config.USER_ROLE
            ):
                assert ll_mla.removeUserRoleFromVm(
                    True, vm, config.ADMIN_USER_NAME, config.USER_ROLE
                )
        testflow.teardown("Stop vms in pool: %s safely", pool_name)
        assert hl_vmpools.stop_vm_pool(pool_name)

    request.addfinalizer(fin)


@pytest.fixture(scope='class')
def create_vm_pool(request, vm_pool_teardown):
    """
    Create a vm pool for current test case
    """
    pool_name = request.node.cls.pool_name
    pool_params = request.node.cls.pool_params
    testflow.setup("Base setup for VM pool test - creating vm pool")
    pool_name = [pool_name] if isinstance(pool_name, str) else pool_name
    for pool in pool_name:
        hl_vmpools.create_vm_pool(True, pool, pool_params)


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
            config.VDC_ADMIN_DOMAIN,
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


@pytest.fixture(scope='class')
def set_cluster_mac_pool(request):
    """
    Set cluster mac pool range to 60 addresses if it has less
    """
    cluster_mac_pool = ll_mac_pool.get_mac_pool_from_cluster(
        config.CLUSTER_NAME[0]
    )
    mac_pool_range = ll_mac_pool.get_mac_range_values(cluster_mac_pool)[0]
    low_mac = MAC(mac_pool_range[0])
    high_mac = MAC(mac_pool_range[1])
    current_mac_pool_size = int(high_mac) - int(low_mac)
    required_mac_pool_size = config.MAC_POOL_SIZE + len(
        ll_vms.get_vms_from_cluster(config.CLUSTER_NAME[0])
    )

    def fin():
        """
        Set cluster mac pool back to it's original range
        """
        if current_mac_pool_size < required_mac_pool_size:
            testflow.teardown(
                "Updating mac pool range back to %s addresses",
                current_mac_pool_size
            )
            assert hl_mac_pool.update_default_mac_pool()
    request.addfinalizer(fin)
    if current_mac_pool_size < required_mac_pool_size:
        testflow.setup(
            "Updating mac pool range to %d addresses", config.MAC_POOL_SIZE
        )
        assert hl_mac_pool.update_ranges_on_mac_pool(
            mac_pool_name=cluster_mac_pool.get_name(),
            range_dict={
                mac_pool_range: (
                    low_mac, high_mac + (
                        required_mac_pool_size - current_mac_pool_size
                    )
                )
            }
        )
