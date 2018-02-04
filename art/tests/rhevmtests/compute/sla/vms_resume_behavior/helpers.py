"""
Helpers file for the vms_resume_behavior test
"""
import time
import config as conf
import rhevmtests.helpers as rhevm_helpers
from concurrent.futures import ThreadPoolExecutor
from art.unittest_lib import testflow
from art.rhevm_api.tests_lib.low_level import (
    storagedomains as ll_sd,
    vms as ll_vms
)


def block_storage_on_host_of_running_vm(vm_name, storage_domain_ip):
    """
    Create iptables rule blocking the storage

    Args:
        vm_name (str): VM name
        storage_domain_ip(str): Storage Domain IP to block

    Returns:
        bool: True, if the command succeeds, otherwise False
    """
    block_dest = dict()
    block_dest[conf.DESTINATION_IP] = [storage_domain_ip]
    host_resource = rhevm_helpers.get_host_resource_of_running_vm(vm_name)
    return host_resource.firewall.chain(conf.INPUT_CHAIN).insert_rule(
        block_dest, conf.RULE_DROP, rule_num="1"
    )


def unblock_storage_on_host_of_running_vm(
    vm_name, time_to_sleep_after_io_error, storage_domain_ip
):
    """
    Delete iptables rule blocking the storage

    Args:
        vm_name (str): VM name
        time_to_sleep_after_io_error (int): the time after getting IO error
             and before unblocking the storage. This interval differs for
             'KILL' scenario and two others ('AUTO_RESUME', LEAVE_PAUSED).
             'KILL' requires 80 sec sleep to behave according to Resume
             Behavior algorithm.
        storage_domain_ip (str): Storage Domain IP to unblock

    Returns:
        bool: True, if the command succeeds, otherwise False
    """
    time.sleep(time_to_sleep_after_io_error)
    host_resource = rhevm_helpers.get_host_resource_of_running_vm(vm_name)
    block_dest = dict()
    block_dest[conf.DESTINATION_IP] = [storage_domain_ip]
    return host_resource.firewall.chain(conf.INPUT_CHAIN).delete_rule(
        block_dest, conf.RULE_DROP
    )


def get_storage_domain_ips(vm_name):
    """
    Get storage IP addresses.

    Args:
        vm_name (str): VM name

    Returns:
        list: Storage Domain IPs list for the domain type
    """
    storage_domain_name = (
        ll_vms.get_vms_disks_storage_domain_name(vm_name=vm_name)
    )
    storage_domain_ips = ll_sd.getDomainAddress(
        positive=True, storage_domain=storage_domain_name
    )[1][conf.DESTINATION_IP]

    return storage_domain_ips


def check_vm_status(vm_name, vm_state, resume_behavior):
    """
    Check VM Status after the following was done in test Setup (fixtures):
    Block the Storage, Wait for I/O error, Unblock the Storage

    Args:
        vm_name (str): name of VM that is tested for resume behavior
        vm_state (str): state of VM as result of unblocking storage after
            storage I/O error pause.
        resume_behavior (str): Resume Behavior settings

    Raises:
        AssertionError: if the VM status after I/O error is not as expected
    """
    if resume_behavior == conf.VM_RB_LEAVE_PAUSED:
        testflow.step(
            "The VM %s is configured with resume_behavior=LEAVE_PAUSED, "
            "wait for a minute before checking VM status after unblocking "
            "the storage and only after that run waitForVMStates function ",
            vm_name
        )
        time.sleep(60)
    testflow.step(
        "Wait until VM %s will have state %s after the storage "
        "unblocking. Fails after timeout=%s.",
        vm_name,
        vm_state,
        conf.VM_STATE_AFTER_STORAGE_ERROR_TIMEOUT
    )
    ll_vms.wait_for_vm_states(
        vm_name=vm_name,
        states=[vm_state],
        timeout=conf.VM_STATE_AFTER_STORAGE_ERROR_TIMEOUT
    )


def block_unblock_storage_for_threadpool(sleep_after_io_error, vm):
    """
    1) Block the Storage
    2) Wait for I/O error
    3) Wait for interval=sleep_after_io_error before unblocking the storage.
       This wait interval for 'KILL' must be not less than 80 sec (engine
       implementation. For other options - leave_paused and auto_resume - it
       must not be 80. The default for tests is 10 sec)
    4) Unblock the Storage

    Args:
        sleep_after_io_error (int): sleep interval before unblocking the
            storage.
        vm (str): vm name for which storage domain ID is blocked.

    Raises:
        AssertionError: if one of the function steps (block, wait for IO pause,
            unblock) fails
    """
    storage_domain_ips = get_storage_domain_ips(vm_name=vm)
    for ip in storage_domain_ips:
        testflow.setup("Block the Storage %s", ip)
        assert block_storage_on_host_of_running_vm(
            vm_name=vm, storage_domain_ip=ip
        )
    testflow.setup(
        "Wait until VM %s have state Paused because of I/O Error", vm
    )
    ll_vms.wait_for_vm_states(
        vm_name=vm,
        states=[conf.VM_PAUSED],
        timeout=conf.SAMPLER_TIMEOUT
    )

    for ip in storage_domain_ips:
        testflow.setup("Unblock the Storage %s", ip)
        assert unblock_storage_on_host_of_running_vm(
            vm_name=vm,
            time_to_sleep_after_io_error=sleep_after_io_error,
            storage_domain_ip=ip
        ), "Failed to unblock the storage on host for running vm %s" % vm


def check_vm_status_thread_pool(vm_state_after_io_error, resume_behavior):
    """
    Args:
        vm_state_after_io_error (str): state of VM as result of unblocking
            storage after storage I/O error pause.
        resume_behavior (str): Resume Behavior settings

    Raises:
        AssertionError: if one the VM status after I/O error is not as expected
    """
    results = []
    with ThreadPoolExecutor(
        max_workers=len(conf.RESUME_BEHAVIOR_VMS)
    ) as executor:
        for item in conf.RESUME_BEHAVIOR_VMS:
            testflow.setup(
                "Check that VM %s status after io error resolved is %s",
                item, vm_state_after_io_error
            )
            results.append(
                executor.submit(
                    check_vm_status,
                    vm_name=item,
                    vm_state=vm_state_after_io_error,
                    resume_behavior=resume_behavior
                )
            )
    for result in results:
        if result.exception():
            raise result.exception()
