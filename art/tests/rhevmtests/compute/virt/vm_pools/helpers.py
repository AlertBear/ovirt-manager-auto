#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
__Author__ = slitmano
This is a helpers module with helper functions dedicated for vm_pool_test.py
"""
import logging
from datetime import datetime

import config
import art.core_api.timeout as timeout_api
from art.rhevm_api.tests_lib.high_level import (
    vmpools as hl_vmpools,
)
from art.rhevm_api.tests_lib.low_level import (
    vms as ll_vms,
    vmpools as ll_vmpools,
    mla as ll_mla,
    users as ll_users,
)
from art.rhevm_api.utils import test_utils
from art.test_handler import exceptions

logger = logging.getLogger("virt.vm_pools.helpers")


def generate_vms_name_list_from_pool(pool_name, size):
    """
    This function parses the name of pool VMs according to pool name.
    if pool name is foo:
    VMs name will be foo-i (i in range (1, pool_vms_num +1))
    if pool name contains a number of consecutive '?' e.g foo-???-bar:
    Vms name will be foo-001-bar, foo-002-bar....

    :param pool_name: The name of the pool
    :type pool_name: str
    :param size: Size of the pool
    :type size: int
    :return: The list of vms according to pool's name
    """
    vm_list = []
    index_len = pool_name.count("?")
    for i in range(1, size + 1):
        if index_len:
            vm_number = ('{:0%d}' % index_len).format(i)
            vm_list.append(pool_name.replace("?" * index_len, vm_number))
        else:
            vm_list.append("%s-%d" % (pool_name, i))
    return vm_list


def wait_for_vm_pool_removed(vmpool, timeout=60, interval=5):
    """
    This function serves as WA for two existing bugs in remove vmPool flow.
    It is necessary for test cases' teardown.
    First bz: 1246886 - Remove vm-pool fails if vms are running.
    Second bz: 1245630 -  [RFE] VM.delete() should wait for snapshot deletion.

    :param vmpool: Name of the vm pool to be removed
    :type vmpool: str
    :param timeout: Total waiting time for removeVmPool to succeed
    :type timeout: int
    :param interval: Intervals between each sample of removeVmPool call
    :type interval: int
    """
    if ll_vmpools.does_vm_pool_exist(vmpool):
        pool_type = ll_vmpools.get_vm_pool_type(vmpool)
        user_names = [
            "%s@%s" % (user, config.USER_DOMAIN) for user in [
                config.USER, config.VDC_ADMIN_USER
            ]
        ]
        if pool_type == 'manual':
            vms_in_pool = ll_vmpools.get_vms_in_pool_by_name(vmpool)
            for vm in vms_in_pool:
                if not ll_mla.removeUsersPermissionsFromVm(
                    True, vm, user_names
                ):
                    logger.error("Failed to remove permission from vm: %s", vm)
        logger.info("Stopping all vms in pool: %s", vmpool)
        if not hl_vmpools.stop_vm_pool(vmpool):
            logger.error(
                "Failed to stop vms in pool: %s", vmpool
            )
        sampler = timeout_api.TimeoutingSampler(
            timeout, interval, ll_vmpools.removeVmPool, True, vmpool
        )
        timeout_message = (
            "Timeout waiting for vms in Pool: '{0}' to restore snapshots "
            "before deleting the pool'".format(vmpool)
        )
        sampler.timeout_exc_args = timeout_message
        try:
            for sampleOk in sampler:
                if sampleOk and not ll_vmpools.does_vm_pool_exist(vmpool):
                    break
        except timeout_api.TimeoutExpiredError:
            logger.error(timeout_message)
    # TODO: remove this iteration after bz 1245630 is resolved
    pool_vms_names = generate_vms_name_list_from_pool(
        vmpool, config.MAX_VMS_IN_POOL_TEST
    )
    for vm in pool_vms_names:
        if ll_vms.does_vm_exist(vm):
            logger.error(
                "Remove vm pool did not remove vm: %s after detaching it due "
                "to bz: 1245630. applying WA", vm
            )
            ll_vms.removeVm(True, vm)


def update_prestarted_vms(vm_pool, prestarted_vms, other_running_vms=0):
    """
    Add prestarted vms to pool and take to account vms in pool which were
    started by admin or taken by user.

    :param vm_pool: Name of vm pool
    :type vm_pool: str
    :param prestarted_vms: Amount of prestarted vms in the pool
    :type prestarted_vms: int
    :param other_running_vms: Amount of already started vms
    :type other_running_vms: size
    :raises: VmPoolException
    """
    if not ll_vmpools.updateVmPool(
        True,
        vm_pool,
        prestarted_vms=prestarted_vms
    ):
        raise exceptions.VmPoolException(
            "couldn't update pool: %s and set %d prestarted vms" % (
                vm_pool, prestarted_vms
            )
        )
    hl_vmpools.wait_for_prestarted_vms(
        vm_pool=vm_pool, running_vms=other_running_vms
    )


def allocate_vms_as_user(
    positive, pool_name, user, user_vms, new_vms, verify=True
):
    """
    Attempts to allocate number_of_vms from the pool with user.
    Should fail and raise exception according to positive parameter and result
    Function logs in engine with the specific user, then verifies that the user
    got the number_of_vms which were allocated.
    Logs in back as admin at the end.

    :param positive: Expected result
    :type positive: bool
    :param pool_name: Name of the pool to allocate vm from
    :type pool_name: str
    :param user: Name of user (first name not to be confused with user_name)
    :type user: str
    :param user_vms: Number of vms allocated previously by user
    :type user_vms: int
    :param new_vms: Number of additional vms to allocate for user
    :type new_vms: int
    :param verify: Verify that user got permission for user_vms + new_vms at
    the end of the flow if True, otherwise skip step.
    :type verify: bool
    :raises: VmPoolExecption
    """
    user_name = '%s@%s' % (user, config.USER_DOMAIN)
    if user == config.USER:
        ll_users.loginAsUser(
            user, config.VDC_ADMIN_DOMAIN, config.VDC_PASSWORD, True
        )
    for i in range(new_vms):
        logger.info(
            "allocating vm from pool: %s as user: %s", pool_name, user
        )
        message = config.ALLOCATE_VM_POSITIVE_MSG if positive else (
            config.ALLOCATE_VM_NEGETIVE_MSG
        )
        if not ll_vmpools.allocateVmFromPool(positive, pool_name):
            raise exceptions.VmPoolException(
                message % (pool_name, user)
            )
    if user == config.USER:
        ll_users.loginAsUser(
            config.VDC_ADMIN_USER, config.VDC_ADMIN_DOMAIN,
            config.VDC_PASSWORD, False
        )
    if positive and verify:
        if get_user_vms(
            pool_name, user_name, config.USER_ROLE, user_vms + new_vms
        ) is None:
            raise exceptions.VmPoolException(
                "Couldn't find %d vms in pool: %s with permissions"
                " for user: %s " % (user_vms + new_vms, pool_name, user_name)
            )


def get_user_vms(pool_name, user_name, user_role, number_of_vms=-1):
    """
    Verifies that a vm from the pool is allocated to the user and that user was
    given user_role permissions on the vm. Returns the list of vms for the pool
    that belong to the user.

    :param pool_name: Name of the pool from which vms were taken
    :type pool_name: str
    :param user_name: Full user_name of the user (e.g. user@domain.com)
    :type user_name: str
    :param user_role: The expected role that user has permissions for on pool
    :type user_role: str
    :param number_of_vms: Number of vms that should be allocated for the user
    :type number_of_vms: int
    :returns: User_vms - a list of the vms from the pool attached to the user
    :rtype: list
    """
    logger.info(
        "Verifying that user: %s got %d from the pool: %s", user_name,
        number_of_vms, pool_name
    )
    pool_vms = ll_vmpools.get_vms_in_pool(
        ll_vmpools.get_vm_pool_object(pool_name)
    )
    user_vms = []
    for vm in pool_vms:
        if ll_mla.has_user_permissions_on_object(user_name, vm, user_role):
            logger.info(
                "User : %s successfully took vm: %s and got permission: %s "
                "for it", user_name, vm.get_name(), user_role
            )
            user_vms.append(vm)
            ll_vms.wait_for_vm_states(vm.get_name())
    if number_of_vms == -1 or len(user_vms) == number_of_vms:
        return [vm.get_name() for vm in user_vms]
    else:
        logger.error("User got an unexpected number of vms: %d", len(user_vms))
        return []


def verify_vms_have_no_permissions_for_user(vms, user_name, user_role):
    """
    Verifies that the a user doesn't have permissions for a list of vms.
    This should be the state after a user stopped a vm it took from the pool.

    :param vms: List of vm names
    :type vms: list
    :param user_name: Full user_name of the user (e.g. user@domain.com)
    :type user_name: str
    :param user_role: The expected role that user has permissions for on pool
    :type user_role: str
    :raises: VmPoolExecption
    """
    logger.info(
        "Verifying that user: %s has lost permission to vms: %s",
        user_name, vms
    )
    vm_objects = [ll_vms.get_vm(vm) for vm in vms]
    for vm in vm_objects:
        if ll_mla.has_user_permissions_on_object(user_name, vm, user_role):
            raise exceptions.VmPoolException(
                "user: %s still has permission for vm: %s" % (
                    user_name, vm.get_name()
                )
            )


def wait_for_no_available_prestarted_vms(vmpool, prestarted_vms):
    """
    This function verifies in engine.log that when all vms in a pool are taken
    no prestarted vms can run. VmPoolMonitor checks if there are prestarted vms
    missing every 'VmPoolMonitorIntervalInMinutes', if so it attempt to start
    the correct amount of vms. If there are no available vms to start in the
    pool it should produce the correct message.
    This function checks that the two messages are produced one after the other
    for the specific vm_pool_id.

    :param vmpool: Name of vm pool
    :type vmpool: str
    :param prestarted_vms: Amount of prestarted vms in the pool
    :type prestarted_vms: int
    :raises: VmPoolException
    """
    engine_executor = config.ENGINE.host.executor()
    vmpool_id = ll_vmpools.UTIL.find(vmpool).get_id()
    logger.info("vm pool ID is: %s", vmpool_id)
    no_more_vms_cmd = [
        "grep", "-i", config.NO_AVAILABLE_VMS_MSG, config.ENGINE_LOG, "|",
        "grep", "-o", config.TIME_PATTERN, "|", "tail", "-1"
    ]
    missing_prestarted_cmd = [
        "grep", "-i",
        config.MISSING_PRESTARTED_MSG % (vmpool_id, prestarted_vms),
        config.ENGINE_LOG, "|", "grep", "-o", config.TIME_PATTERN, "|", "tail",
        "-1"
    ]
    sampler = timeout_api.TimeoutingSampler(
        config.PRESTARTED_VMS_TIMEOUT, config.VM_POOL_ACTION_SLEEP,
        engine_executor.run_cmd, missing_prestarted_cmd
    )
    try:
        logger.info("running cmd: %s", missing_prestarted_cmd)
        for rc_1, out_1, error_1 in sampler:
            if out_1:
                delta = 100
                logger.info("running cmd: %s", no_more_vms_cmd)
                rc_2, out_2, error_2 = engine_executor.run_cmd(
                    no_more_vms_cmd
                )
                if out_2:
                    delta = (
                        datetime.strptime(out_2.strip(), "%H:%M") -
                        datetime.strptime(out_1.strip(), "%H:%M")
                    ).seconds
                if delta <= 60:
                    break
    except timeout_api.TimeoutExpiredError:
        raise exceptions.VmPoolException(
            "Failed to verify that VmPoolMonitor finds no available vms to"
            "to prestart in pool: %s " % vmpool
        )


def set_vm_pool_monitor_interval(interval):
    """
    Sets a value for 'VmPoolMonitorIntervalInMinutes' parameter via
    engine-config (value is in minutes).

    :param interval: VmPoolMonitorIntervalInMinutes value
    :type interval: int
    :raises: RHEVMEntityException
    """
    logger.info(
        "setting 'VmPoolMonitorIntervalInMinutes' parameter to %d "
        "via engine-config", interval
    )
    param = "VmPoolMonitorIntervalInMinutes=%d" % interval
    if not config.ENGINE.engine_config(action='set', param=param).get(
        'results'
    ):
        raise exceptions.RHEVMEntityException(
            "Failed to set value of parameter: VmPoolMonitorIntervalInMinutes "
            "to %d via engine-config" % interval
        )


def get_vm_pool_monitor_interval():
    """
    Gets the value for 'VmPoolMonitorIntervalInMinutes' parameter via
    engine-config (value is in minutes).

    :return: value of param VmPoolMonitorIntervalInMinutes
    :rtype: int
    """
    logger.info(
        "Get 'VmPoolMonitorIntervalInMinutes' parameter value "
        "via engine-config"
    )
    param = "VmPoolMonitorIntervalInMinutes"
    value, version = test_utils.get_engine_properties(
        config.ENGINE.host, param
    )
    res = config.ENGINE.engine_config(action='get', param=param)
    if res.get('results', {}).get(param, {}).get('value') is None:
        logger.error(
            "Failed to get value of parameter: VmPoolMonitorIntervalInMinutes "
            "via engine-config"
        )
    return value


def stop_vm_in_pool_as_user(positive, vm, user, manual=False):
    """
    Attempt to stop a vm from a pool as user with User Role on the pool.
    If the pool type is manual permission for the user on the vm should persist
    after vm is down, if pool is automatic permission is removed.

    :param positive: True if stop action should succeed
    :type positive: bool
    :param vm: Name of the vm
    :type vm: str
    :param user: User name
    :type user: str
    :param manual: True if pool type is manual, False if automatic (default)
    :return: True if action succeeded and permission was handled according to
    the pool type, False otherwise
    """
    user_name = '%s@%s' % (user, config.USER_DOMAIN)
    if user == config.USER:
        ll_users.loginAsUser(
            user, config.VDC_ADMIN_DOMAIN, config.VDC_PASSWORD, True
        )
    if not ll_vms.stopVm(positive, vm):
        return False
    if user == config.USER:
        ll_users.loginAsUser(
            config.VDC_ADMIN_USER, config.VDC_ADMIN_DOMAIN,
            config.VDC_PASSWORD, False
        )
    logger.info("Checking permissions of user: %s on vm: %s", user, vm)
    user_has_permission = ll_mla.has_user_permissions_on_object(
        user_name, ll_vms.get_vm(vm), config.USER_ROLE
    )
    if manual:
        ll_vms.wait_for_vm_snapshots(
            vm, config.ENUMS['snapshot_state_ok'],
            config.ENUMS['snapshot_stateless_description']
        )
    if user_has_permission and not manual:
        logger.error(
            "User role persisted for vm: %s in automatic pool after "
            "stopping the vm"
        )
        return False
    if not user_has_permission and manual:
        logger.error(
            "User role for vm: %s in manual pool removed after stopping the vm"
        )
        return False
    return True


def start_vm_in_pool_as_user(
    positive, vm, user, check_permission=False, manual=False
):
    """
    Attempt to start a vm from a pool as user with User Role on the pool.

    :param positive: True if stop action should succeed
    :type positive: bool
    :param vm: Name of the vm
    :type vm: str
    :param user: User name
    :type user: str
    :param check_permission: True if we like to check that the vm has
    a permission set for user, False if we like to ignore this check
    :type check_permission: bool
    :param manual: True if pool type is manual, False if automatic (default)
    :type manual: bool
    :return: True if action succeeded and permission was handled according to
    the pool type, False otherwise
    """
    user_name = '%s@%s' % (user, config.USER_DOMAIN)
    if user == config.USER:
        ll_users.loginAsUser(
            user, config.VDC_ADMIN_DOMAIN, config.VDC_PASSWORD, True
        )
    if not ll_vms.startVm(positive, vm):
        return False
    if user == config.USER:
        ll_users.loginAsUser(
            config.VDC_ADMIN_USER, config.VDC_ADMIN_DOMAIN,
            config.VDC_PASSWORD, False
        )
    if manual:
        ll_vms.wait_for_vm_snapshots(
            vm, config.ENUMS['snapshot_state_ok'],
            config.ENUMS['snapshot_stateless_description']
        )
    if check_permission:
        logger.info("Checking permissions of user: %s on vm: %s", user, vm)
        if not ll_mla.has_user_permissions_on_object(
            user_name, ll_vms.get_vm(vm), config.USER_ROLE
        ):
            logger.error(
                "User: %s does not have %s permission for vm: %s",
                user_name, config.USER_ROLE, vm
            )
            return False
    return True


def flush_file_system_buffers(vm_resource):
    """
    Calls sync to flush file system buffers. This call is invoked to makes sure
    That the new file written will persist after vm reboot.

    :param vm_resource: Host resource object of the vm.
    :type vm_resource: Host resource.
    :return: True if action sync succeeded, False otherwise.
    :rtype: bool
    """
    return vm_resource.run_command(['sync'])[0] == 0
