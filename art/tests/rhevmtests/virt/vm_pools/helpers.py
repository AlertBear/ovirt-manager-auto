"""
__Author__ = slitmano
This is a helpers module with helper functions dedicated for vm_pool_test.py
"""
import logging
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import art.rhevm_api.tests_lib.low_level.vmpools as ll_vmpools
import utilities.timeout as timeout_api
from rhevmtests.virt import config

logger = logging.getLogger(__name__)

PRESTARTED_VMS_TIMEOUT = 300
VM_POOL_ACTION_TIMEOUT = 300
VM_POOL_ACTION_SLEEP = 5


def wait_for_prestarted_vms(
    vmpool, timeout=PRESTARTED_VMS_TIMEOUT, interval=5
):
    """
    __Author__ = slitmano
    :param vmpool: name of vm pool
    :type vmpool: str
    :param timeout: timeout threshold for waiting for prestarted vms to start
    :type timeout: int
    :param interval: waiting time between each check
    :type interval: int
    :return: True if the amount of vms in pool that are up is at least the size
    of prestarted vms defined for the vm pool.
    :rtype: bool
    """
    prestarted_vms = ll_vmpools.get_vm_pool_number_of_prestarted_vms(vmpool)
    logger.info(
        'Waiting for at least %d vms from vm pool %s to start',
        prestarted_vms, vmpool
    )
    expected_states = [
        config.ENUMS['vm_state_up'], config.ENUMS['vm_state_powering_up']
    ]
    sampler = timeout_api.TimeoutingSampler(
        timeout, interval, ll_vmpools.get_vms_in_pool_by_states,
        vmpool, expected_states
    )
    timeout_message = (
        "Timeout when waiting for {0} vms in vmPool: '{1}' to start'".format(
            prestarted_vms, vmpool
        )
    )
    try:
        for found_vms in sampler:
            if len(found_vms) >= prestarted_vms:
                return True
    except timeout_api.TimeoutExpiredError:
        logger.error(timeout_message)
    return False


def generate_vms_name_list_from_pool(pool_name, size):
    """
    This function parses the name of pool VMs according to pool name.
    if pool name is foo:
    VMs name will be foo-i (i in range (1, pool_vms_num +1))
    if pool name contains a number of consecutive '?' e.g foo-???-bar:
    Vms name will be foo-001-bar, foo-002-bar....
    No name like foo??bar?? wil be accepted from engine so no need to cover.

    :param pool_name: the name of the pool
    :type pool_name: str
    :param size: size of the pool
    :type size: int
    :return: the list of vms according to pool's name
    """
    vm_list = []
    index_len = pool_name.count("?")
    for i in range(1, size + 1):
        if index_len:
            vm_number = ('{:0%sd}' % index_len).format(i)
            vm_list.append(pool_name.replace("?" * index_len, vm_number))
        else:
            vm_list.append("%s-%s" % (pool_name, i))
    return vm_list


def validate_pool_size(vmpool, size):
    """
    __Author__ = slitmano
    This function compares vmpool size to an expected size
    :param vmpool: name of vm pool
    :type vmpool: str
    :param size: expected size of vm pool
    :type size: int
    :return: True if vmpool size == size, False otherwise
    :rtype: bool
    """
    return ll_vmpools.get_vm_pool_size(vmpool=vmpool) == size


def wait_for_empty_vm_pool(
    vmpool, timeout=VM_POOL_ACTION_TIMEOUT, interval=VM_POOL_ACTION_SLEEP
):
    """
    __Author__ = slitmano
    waits until vmpool is empty or TIMEOUT exceeds
    :param vmpool: name of vmpool.
    :type vmpool: str
    :param timeout: timeout threshold for getting an empty vmpool
    :type timeout: int
    :param interval: waiting time between each size check
    :type interval: int
    :return: True if vm pool got empty, False otherwise
    :rtype: bool
    """
    logger.info(
        'Waiting for vm pool %s to get empty up to %d seconds,'
        'sampling every %d second.', vmpool, timeout, interval
    )
    sampler = timeout_api.TimeoutingSampler(
        timeout=timeout, sleep=interval, func=validate_pool_size,
        vmpool=vmpool, size=0
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


def remove_whole_vm_pool(vmpool, size, remove_vms=True, stop_vms=False):
    """
    Description: Detach vms, remove them and remove vm pool.
    :param vmpool: name of the VMPool
    :type vmpool: str
    :param size: number of vms in pool
    :type size: int
    :param remove_vms: remove all vms in pool
    :type remove_vms: bool
    :param stop_vms: stop vms before detaching
    :type stop_vms: bool
    :return: True if operation was successful, False otherwise
    :rtype: bool
    """
    vms_in_pool = ll_vmpools.get_vms_in_pool_by_name(vm_pool=vmpool)
    ret = ll_vmpools.detachVms(
        positive=True, vm_pool=vmpool, stop_vms=stop_vms
    )
    if not ret:
        logger.warning("Failed to stop and detach vms on pool: %s", vmpool)
        return False
    if not wait_for_empty_vm_pool(vmpool=vmpool):
        return False
    if remove_vms:
        ret = ll_vms.safely_remove_vms(vms=vms_in_pool)
        if not ret:
            logger.warning("Failed to remove vms from pool: %s", vmpool)
            return False
    ret = ll_vmpools.removeVmPool(positive=True, vmpool=vmpool)
    return ret
