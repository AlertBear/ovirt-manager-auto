#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
__Author__ = slitmano

Description:
This test module test specific vm_pool features.
Test Plan - https://polarion.engineering.redhat.com/polarion/#/project/
RHEVM3/wiki/Compute/3_5_VIRT_VMPools
"""
import logging
import config
from art.rhevm_api.tests_lib.low_level import (
    vmpools as ll_vmpools,
    mla as ll_mla,
    users as ll_users,
)
import art.rhevm_api.tests_lib.high_level.vmpools as hl_vmpools
from art.test_handler import exceptions
from art.unittest_lib import VirtTest as TestCase, attr
from rhevmtests.virt.vm_pools import helpers

logger = logging.getLogger("virt.vm_pools.base")


@attr(tier=1)
class BaseVmPool(TestCase):
    """
    Base class for all vm pool tests
    """
    __test__ = False

    pool_name = None
    pool_size = 2
    max_vms_per_user = None
    pool_params = {}
    version = config.COMP_VERSION
    prestarted_vms = 0

    @classmethod
    def setup_class(cls):
        """
        Setup class for all vm pool tests
        """
        logger.info("Base setup for VM pool test")
        updated_params = {
            'name': cls.pool_name,
            'size': cls.pool_size,
            'cluster': config.CLUSTER_NAME[0],
            'template': config.TEMPLATE_NAME[0],
            'max_user_vms': cls.max_vms_per_user,
            'prestarted_vms': cls.prestarted_vms,
        }
        cls.pool_params.update(updated_params)

    @classmethod
    def teardown_class(cls):
        """
        Teardown class for all vm pool tests
        """
        logger.info("Base teardown for VM pool test")
        if ll_vmpools.does_vm_pool_exist(cls.pool_name):
            ll_vmpools.updateVmPool(
                True,
                cls.pool_name,
                prestarted_vms=0
            )
            logger.info(
                "Removing vm_pool :%s",
                cls.pool_name
            )
            if cls.version < config.NEW_IMPLEMENTATION_VERSION:
                helpers.wait_for_vm_pool_removed(cls.pool_name)
            else:
                ll_vmpools.removeVmPool(True, cls.pool_name)


class VmPool(BaseVmPool):
    """
    Test class for all cases requires a vm pool already created.
    """
    __test__ = False

    @classmethod
    def setup_class(cls):
        """
        Setup class -> create vm pool
        """
        super(VmPool, cls).setup_class()
        hl_vmpools.create_vm_pool(True, cls.pool_name, cls.pool_params)


@attr(tier=2)
class VmPoolWithUser(VmPool):
    """
    Test class for all cases that requires a vm pool created with permissions
    for user set.
    """
    __test__ = False

    user_name = '%s@%s' % (config.USER, config.USER_DOMAIN)

    @classmethod
    def setup_class(cls):
        """
        Setup class -> create vm pool and add external user to engine.
        """
        super(VmPoolWithUser, cls).setup_class()
        logger.info(
            "Adding user: %s to engine", cls.user_name
        )
        if not ll_users.addExternalUser(
            True, user_name=config.USER, domain=config.USER_DOMAIN
        ):
            raise exceptions.UserException(
                "Failed to add user: %s to engine" % config.USER
                )
        logger.info(
            "Adding %s permissions for user: %s on pool: %s", config.USER_ROLE,
            config.USER, cls.pool_name
        )
        if not ll_mla.addVmPoolPermissionToUser(
            True, config.USER, cls.pool_name, config.USER_ROLE
        ):
            raise exceptions.VmPoolException(
                "Failed to add permission: %s to user: %s on pool: %s" %
                (config.USER_ROLE, config.USER, cls.pool_name)
            )

    @classmethod
    def teardown_class(cls):
        """
        Teardown class -> remove external user from engine.
        """
        ll_users.loginAsUser(
            config.VDC_ADMIN_USER,
            config.INTERNAL_DOMAIN,
            config.VDC_PASSWORD,
            False
        )
        logger.info("Removing user %s from engine", cls.user_name)
        if not ll_users.removeUser(True, config.USER, config.USER_DOMAIN):
            raise exceptions.UserException(
                "Failed to remove user: %s from engine" % config.USER
            )
        super(VmPoolWithUser, cls).teardown_class()
