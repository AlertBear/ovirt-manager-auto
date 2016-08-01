#!/usr/bin/env python

# Copyright (C) 2010 Red Hat, Inc.
#
# This is free software; you can redistribute it and/or modify it
# under the terms of the GNU Lesser General Public License as
# published by the Free Software Foundation; either version 2.1 of
# the License, or (at your option) any later version.
#
# This software is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this software; if not, write to the Free
# Software Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA
# 02110-1301 USA, or see the FSF site: http://www.fsf.org.
"""
High-level functions above VM pools
"""
import logging
import art.rhevm_api.utils.test_utils as test_utils
import art.rhevm_api.tests_lib.high_level.vms as hl_vms
from art.rhevm_api.tests_lib.low_level import (
    vms as ll_vms,
    vmpools as ll_vmpools,
)
from art.test_handler.settings import opts
import concurrent.futures as futures
from art.test_handler import exceptions
import utilities.timeout as timeout_api

ENUMS = opts['elements_conf']['RHEVM Enums']

VM_POOL_ACTION_TIMEOUT = 300
VM_POOL_ACTION_SLEEP = 5

logger = logging.getLogger("art.hl_libs.vmpools")


def _control_vms_in_pool(
    positive, vm_pool, action, max_workers=2, threading=False
):
    """
    __Author__ = edolinin, alukiano, slitmano

    Common function for starting, stopping and detaching
    all VMs in a pool.

    :param positive: Determines what is the expected result of the action
    :type positive: bool
    :param vm_pool: Name of the pool
    :type vm_pool: str
    :param action: Action to run on VMs, can be start, stop or detach
    :type action: str
    :param max_workers: Max number of threads to be used
    :type max_workers: int
    :param threading: Determines with to use threads or not
    :type threading: bool
    :return: True if every operation was successful, False otherwise
    :rtype: bool
    """
    if action == ENUMS['start_vm']:
        action_function = ll_vms.startVm
        expected_status = ENUMS['vm_state_up']
    elif action == ENUMS['stop_vm']:
        action_function = ll_vms.stopVm
        expected_status = ENUMS['vm_state_down']
    elif action == ENUMS['detach_vm']:
        action_function = ll_vms.detachVm
        expected_status = ENUMS['vm_state_down']
    else:
        logger.error("Unsupported action given")
        return False

    vms_list = ll_vmpools.get_vms_in_pool_by_name(vm_pool)
    if threading:
        results = list()
        with futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            for vm_name in vms_list:
                results.append(executor.submit(action_function, True, vm_name))
        test_utils.raise_if_exception(results)
    else:
        for vm_name in vms_list:
            if not ll_vms.changeVMStatus(
                positive=positive, vm=vm_name, action=action,
                expectedStatus=expected_status, async='false'
            ):
                logger.error(
                    "Failed to set status: %s for vm: %s",
                    expected_status, vm_name
                )
                return False
        if action == ENUMS['stop_vm']:
            for vm_name in vms_list:
                if not hl_vms.wait_for_restored_stateless_snapshot(vm_name):
                    logger.error(
                        "Vm: %s did not restore to original state", vm_name
                    )
                    return False
        if not ll_vms.waitForVmsStates(
            positive=positive, names=vms_list, states=expected_status
        ):
            logger.error(
                "At least one vm from pool: %s has the wrong state,"
                " expected: %s.", (vm_pool, expected_status)
            )
            return False
    return True


def start_vm_pool(vm_pool, positive=True):
    """
    Wrapper for starting all VMs in a pool.

    :param vm_pool: Name of the pool
    :type vm_pool: str
    :param positive: Positive or negative result expected
    :type positive: bool
    :return: True if every operation was successful, False otherwise
    :rtype: bool
    """
    return _control_vms_in_pool(
        positive=positive, vm_pool=vm_pool, action="start"
    )


def stop_vm_pool(vm_pool, positive=True):
    """
    Wrapper for stopping all VMs in a pool.

    :param vm_pool: Name of the pool
    :type vm_pool: str
    :param positive: Positive or negative result expected
    :type positive: bool
    :return: True if every operation was successful, False otherwise
    :rtype: bool
    """
    return _control_vms_in_pool(
        positive=positive, vm_pool=vm_pool, action="stop"
    )


def detach_vms_from_pool(vm_pool, positive=True):
    """
    Wrapper for detaching all VMs in a pool.

    :param vm_pool: Name of the pool
    :type vm_pool: str
    :param positive: Positive or negative result expected
    :type positive: bool
    :return: True if every operation was successful, False otherwise
    :rtype: bool
    """
    return _control_vms_in_pool(
        positive=positive, vm_pool=vm_pool, action="detach"
    )


def stop_and_detach_vms_from_pool(vm_pool, positive=True):
    """
    Detach vms from pool after stopping all the vms in the pool

    :param vm_pool: Name of the pool
    :type vm_pool: str
    :param positive: Positive or negative result expected
    :type positive: bool
    :return: True if every operation was successful, False otherwise
    :rtype: bool
    """
    ret = _control_vms_in_pool(
        positive=True, vm_pool=vm_pool, action="stop"
    )
    return ret and _control_vms_in_pool(
        positive=positive, vm_pool=vm_pool, action="detach"
    )


def start_vms(vmpool, number_of_vms=1):
    """
    Attempts to starts number_of_vms vms in pool vmpool. Raises exception
    if not enough vms in the pool are available or startVm fails.

    :param vmpool: Name of vm pool
    :type vmpool: str
    :param number_of_vms: Number of vms to start
    :type number_of_vms: int
    :raises: VmPoolException, VmException
    """
    logger.info(
        "Starting %d vms from pool: %s as admin", number_of_vms, vmpool
    )
    free_vms_obj = ll_vmpools.get_vms_in_pool_by_states(
        vmpool=vmpool, states=ENUMS['vm_state_down']
    )
    if not len(free_vms_obj) == number_of_vms:
        raise exceptions.VmPoolException(
            "Not enough free vms in pool: %s" % vmpool
        )
    free_vms_names = [vm.get_name() for vm in free_vms_obj]
    logger.info("Starting VMs: %s", free_vms_names)
    ll_vms.start_vms(vm_list=free_vms_names, wait_for_ip=False)


def wait_for_vms_in_pool_to_start(
    vmpool, timeout=VM_POOL_ACTION_TIMEOUT,
    interval=VM_POOL_ACTION_SLEEP, number_of_vms=0, wait_until_up=False
):
    """
    __Author__ = slitmano

    This function waits until at least {number_of_vms} from vmpool are started.
    This mainly serves for checking that setting prestarted vms for the pool
    has worked. Waiting until the vms are in up state is optional.

    :param vmpool: Name of vm pool
    :type vmpool: str
    :param timeout: Timeout threshold for waiting for prestarted vms to start
    :type timeout: int
    :param interval: Waiting time between each check (in seconds)
    :type interval: int
    :param number_of_vms: The amount of vms in the pool already running.
    :type number_of_vms: int
    :param wait_until_up: True if method has to wait for vms to go up, False
    if powering_up state is also sufficient
    :type wait_until_up: bool
    :return: True if the amount of vms in pool that are up is at least the size
    of prestarted vms defined for the vm pool.
    :rtype: bool
    """

    logger.info(
        'Waiting for at least %s vms from vm pool %s to start',
        number_of_vms, vmpool
    )
    expected_states = None
    if wait_until_up:
        expected_states = [ENUMS['vm_state_up']]
    sampler = timeout_api.TimeoutingSampler(
        timeout, interval, ll_vmpools.get_vms_in_pool_by_states,
        vmpool, expected_states
    )
    timeout_message = (
        "Timeout when waiting for {0} vms in vmPool: '{1}' to start'".format(
            number_of_vms, vmpool
        )
    )
    try:
        for found_vms in sampler:
            if len(found_vms) == number_of_vms:
                return True
    except timeout_api.TimeoutExpiredError:
        logger.error(timeout_message)
    logger.error(
        "Wrong amount of vms are running in pool: %s. Expected %s vms running."
        % (vmpool, number_of_vms)
    )
    return False


def wait_for_prestarted_vms(vm_pool, running_vms=0, wait_until_up=False):
    """
    __Author__ = slitmano

    Waits for prestarted vms in pool to start. takes under consideration the
    other running vms in pool (should be provided by function caller).

    :param vm_pool: Name of vm pool.
    :type vm_pool: str
    :param running_vms: The amount of other running vms in pool.
    :type running_vms: int
    :param wait_until_up: If True, waits for vms to get to state 'up'.
    :type wait_until_up: bool
    :raises: VmPoolException
    """
    prestarted_vms = ll_vmpools.get_vm_pool_number_of_prestarted_vms(vm_pool)
    logger.info(
        'Currently running vms in pool: %d.'
        'Waiting for %d prestarted vms from vm pool %s to start',
        running_vms, prestarted_vms, vm_pool
    )
    if not wait_for_vms_in_pool_to_start(
        vm_pool,
        number_of_vms=prestarted_vms+running_vms,
        wait_until_up=wait_until_up
    ):
        raise exceptions.VmPoolException()


def wait_for_empty_vm_pool(
    vmpool, timeout=VM_POOL_ACTION_TIMEOUT, interval=VM_POOL_ACTION_SLEEP
):
    """
    __Author__ = slitmano

    Waits until vmpool is empty or TIMEOUT exceeds

    :param vmpool: Name of vmpool.
    :type vmpool: str
    :param timeout: Timeout threshold for getting an empty vmpool
    :type timeout: int
    :param interval: Waiting time between each size check
    :type interval: int
    :return: True if vm pool got empty, False otherwise
    :rtype: bool
    """
    logger.info(
        'Waiting for vm pool %s to get empty up to %d seconds,'
        'sampling every %d second.', vmpool, timeout, interval
    )
    sampler = timeout_api.TimeoutingSampler(
        timeout=timeout, sleep=interval,
        func=lambda x: ll_vmpools.get_vm_pool_size(x) == 0,
        x=vmpool
    )
    timeout_message = (
        "Timeout when waiting for vm pool: '{0}' to empty'".format(vmpool)
    )
    try:
        for sample in sampler:
            if sample:
                return True
    except timeout_api.TimeoutExpiredError:
        logger.error(timeout_message)
    return False


def remove_whole_vm_pool(vmpool, remove_vms=True, stop_vms=False):
    """
    Description: Detach vms, remove them and remove vm pool.

    :param vmpool: Name of the VMPool
    :type vmpool: str
    :param remove_vms: Remove all vms in pool
    :type remove_vms: bool
    :param stop_vms: Stop vms before detaching
    :type stop_vms: bool
    :return: True if operation was successful, False otherwise
    :rtype: bool
    """
    vms_in_pool = ll_vmpools.get_vms_in_pool_by_name(vm_pool=vmpool)
    func = stop_and_detach_vms_from_pool if stop_vms else detach_vms_from_pool
    ret = func(vm_pool=vmpool, positive=True)
    if not ret:
        return False
    if not wait_for_empty_vm_pool(vmpool=vmpool):
        return False
    if remove_vms:
        ret = ll_vms.safely_remove_vms(vms=vms_in_pool)
        if not ret:
            logger.error("Failed to remove vms from pool: %s", vmpool)
            return False
    ret = ll_vmpools.removeVmPool(positive=True, vmpool=vmpool)
    return ret


def create_vm_pool(positive, pool_name, pool_params):
    """
    Create a vm pool with given parameters - this method takes under
    consideration that if a pool is created with prestarted vms, the vms status
    after pool creation will not be 'down'.

    :param positive: True if vm pool creation is expected to succeed,
    False otherwise
    :type positive: bool
    :param pool_name: Name of vm pool
    :type pool_name: str
    :param pool_params: A dictionary with vm pool parameters and their values
    :type pool_params: dict
    :raises: VmPoolException
    """
    wait = not bool(pool_params['prestarted_vms'])
    pool_params['name'] = pool_name
    if not ll_vmpools.addVmPool(positive, wait=wait, **pool_params):
        raise exceptions.VmPoolException()
    if not wait:
        possible_states = [
            ENUMS['vm_state_up'],
            ENUMS['vm_state_down'],
            ENUMS['vm_state_powering_up'],
            ENUMS['vm_state_wait_for_launch']
        ]
        vms = ll_vmpools.get_vms_in_pool_by_name(pool_name)
        for vm in vms:
            ll_vms.wait_for_vm_states(vm, possible_states)
