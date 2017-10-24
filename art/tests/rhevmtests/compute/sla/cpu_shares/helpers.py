"""
CPU Share Test Helpers
"""

import art.rhevm_api.tests_lib.high_level.vms as hl_vms
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import rhevmtests.compute.sla.config as conf
import rhevmtests.helpers as rhevm_helpers
from art.core_api import apis_exceptions, apis_utils
from art.unittest_lib import testflow

logger = conf.logging.getLogger(__name__)


def load_vms_cpu(vms):
    """
    Load VM's CPU

    Args:
        vms (list): VM's names

    Returns:
        bool: True, if CPU load action succeed, otherwise False
    """
    for vm_name in vms:
        ll_vms.wait_for_vm_states(vm_name=vm_name)
        vm_resource = rhevm_helpers.get_host_resource(
            hl_vms.get_vm_ip(vm_name=vm_name), conf.VMS_LINUX_PW
        )
        testflow.step("Run CPU load on VM %s", vm_name)
        rc = vm_resource.run_command(
            ["dd", "if=/dev/zero", "of=/dev/null", "&"]
        )[0]
        if rc:
            return False
    return True


def get_vms_cpu_consumption_on_host(vms):
    """
    Get VM's CPU consumption from the host where VM's run

    Args:
        vms (list): VM's names

    Returns:
        dict: VM's CPU consumption
    """
    current_dict = dict(
        (
            vm_name, hl_vms.get_vm_cpu_consumption_on_the_host(vm_name=vm_name)
        ) for vm_name in vms
    )
    logger.info(
        "Current dict of VM's names and their cpu consumption :%s",
        current_dict
    )
    return current_dict


def check_ratio(current_dict, expected_dict):
    """
    Check if the current_dict values match the expected_dict values
    (with deviation of 5%)

    Args:
        current_dict (dict): Current VM's CPU consumption
        expected_dict (dict): Expected VM's CPU consumption

    Returns:
        bool: True, if values from current_dict equal to
            values from expected_dict. otherwise False
    """
    for vm_name, vm_cpu_consumption in current_dict.iteritems():
        target = expected_dict[vm_name]
        logger.info(
            "Check if VM %s current CPU consumption equal to expected one"
        )
        if not (target - 5 <= vm_cpu_consumption <= target + 5):
            logger.warning(
                "Current CPU usage of %s should be around %s", vm_name, target
            )
            return False
    return True


def check_cpu_share(vms, expected_dict):
    """
    Wait for VM's CPU share ratio will be equal to expected one

    Args:
        vms (list): VM's names
        expected_dict (dict): Expected VM's CPU consumption

    Returns:
        bool: True, if VM's CPU share ratio equal to expected one,
            otherwise False
    """
    sampler = apis_utils.TimeoutingSampler(
        timeout=conf.SAMPLER_TIMEOUT,
        sleep=conf.SAMPLER_SLEEP,
        func=get_vms_cpu_consumption_on_host,
        vms=vms
    )
    testflow.step(
        "Wait until VM's CPU shares ratio will be equal to: %s", expected_dict
    )
    try:
        for sample in sampler:
            if check_ratio(sample, expected_dict):
                return True
    except apis_exceptions.APITimeout:
        logger.error("Timeout when waiting for CPU shares expected ratio")
    return False
