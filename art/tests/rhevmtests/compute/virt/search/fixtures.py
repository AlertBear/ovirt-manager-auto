
# ! /usr/bin/python
# -*- coding: utf-8 -*-
"""
Fixtures module for search test
"""

import shlex

import pytest

import config
import rhevmtests.helpers as helper
from art.rhevm_api.tests_lib.low_level import (
    vms as ll_vms,
    users as ll_users,
    mla as ll_mla,
    storagedomains as ll_sd
)
from art.unittest_lib import testflow


@pytest.fixture(scope='class')
def add_user(request):
    """
    add user USER1
    """
    def fin():
        """
        Delete user and login as administrator
        """
        testflow.teardown("Login as admin user")
        ll_users.loginAsUser(
            config.VDC_ADMIN_USER,
            config.VDC_ADMIN_DOMAIN,
            config.VDC_PASSWORD,
            False
        )
        testflow.teardown("Delete user %s", config.USER)
        assert ll_users.removeUser(
            positive=True,
            user=config.USER
        )
    request.addfinalizer(fin)
    testflow.setup("Add External User %s", config.USER)

    with config.ENGINE_HOST.executor().session() as session:
        if not session.run_cmd(shlex.split(config.SHOW_USER_CMD))[0]:
            testflow.skip("User %s already exists", config.USER)
        else:
            testflow.setup("Create User %s ", config.USER)
            assert not (
                session.run_cmd(shlex.split(config.ADD_USER_CMD))[0],
                'Failed to add user'
            )
            assert not (
                session.run_cmd(
                    shlex.split(config.RESET_USER_PASSWORD_CMD)
                )[0],
                'Failed to reset password'
            )

    assert ll_users.addExternalUser(
        positive=True,
        user_name=config.USER,
        domain=config.USER_DOMAIN
    )
    testflow.setup("Add permission to External User")
    assert ll_mla.addPermissionsForDataCenter(
        positive=True,
        user=config.USER,
        data_center=config.DC_NAME[0],
        role="VmCreator"
    )


@pytest.fixture(scope='module')
def create_vm_for_search(request):
    """
    Create VM for search tests
    """
    vm_parameters = {
        config.VM_UP_SEARCH_TEST: {
            "description": "{0}_description".format(
                config.VM_UP_SEARCH_TEST),
            "memory": helper.get_gb(2),
            "memory_guaranteed": helper.get_gb(1),
            "os_type": config.VM_OS_TYPE,
            "placement_affinity": config.VM_PINNED,
            "placement_host": config.HOSTS[0],
        },
        config.VM_DOWN_SEARCH_TEST: {
            "description": "{0}_description".format(
                config.VM_DOWN_SEARCH_TEST),
            "memory": helper.get_gb(1),
            "memory_guaranteed": helper.get_gb(1),
            "os_type": config.VM_OS_TYPE,
            "placement_affinity": config.VM_PINNED,
            "placement_host": config.HOSTS[1],
        }
    }

    def fin():
        """
        Login as admin again and remove VMs
        """
        testflow.teardown("Login as admin user")
        ll_users.loginAsUser(
            config.VDC_ADMIN_USER,
            config.VDC_ADMIN_DOMAIN,
            config.VDC_PASSWORD,
            False
        )
        testflow.teardown("Remove VMs:%s", config.VMS_SEARCH_TESTS)
        ll_vms.safely_remove_vms(config.VMS_SEARCH_TESTS)

    request.addfinalizer(fin)
    existing_storages = ll_sd.getStorageDomainNamesForType(
        config.DC_NAME[0], config.STORAGE_TYPE_NFS
    )
    if not existing_storages:
        pytest.skip(
            "Cannot run VM search test, needs at least one NFS storage domain"
        )
    for vm_name in config.VMS_SEARCH_TESTS[:2]:
        testflow.setup(
            "Create VM %s, with parameters %s",
            vm_name, vm_parameters.get(vm_name)
        )
        assert ll_vms.addVm(
            True,
            name=vm_name,
            template=config.TEMPLATE_NAME[0],
            cluster=config.CLUSTER_NAME[0],
            storagedomain=existing_storages[0]
        )
        assert ll_vms.updateVm(
            positive=True, vm=vm_name, **vm_parameters.get(vm_name)
        )
    testflow.setup("Start vm %s", config.VM_UP_SEARCH_TEST)
    assert ll_vms.startVm(
        positive=True, vm=config.VM_UP_SEARCH_TEST, wait_for_ip=True
    )
