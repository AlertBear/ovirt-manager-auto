"""
HE webadmin helpers
"""
import logging
import re
from time import sleep

import art.core_api.apis_exceptions as exceptions
import art.rhevm_api.tests_lib.low_level.hosts as ll_hosts
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import art.unittest_lib as test_libs
import art.unittest_lib as u_libs
import config as conf
from art.core_api.apis_utils import TimeoutingSampler

logger = logging.getLogger(__name__)


# noinspection PyTypeChecker
def wait_until_he_vm_will_appear_under_engine(
    timeout=conf.SAMPLER_TIMEOUT, sleep=conf.SAMPLER_SLEEP
):
    """
    Wait until the HE VM will appear under the engine after auto-import action

    Args:
        timeout (int): Sampler timeout
        sleep (int): Sampler sleep

    Returns:
        bool: True, if the HE VM appears before timeout, otherwise False
    """
    sampler = TimeoutingSampler(
        timeout=timeout,
        sleep=sleep,
        func=ll_vms.does_vm_exist,
        vm_name=conf.HE_VM_NAME
    )
    try:
        for sample in sampler:
            if sample:
                return True
    except exceptions.APITimeout:
        logger.error(
            "HE VM does not exist under engine after %s second", timeout
        )
        return False


def change_engine_config_ovf_update_interval(
    value=conf.OVF_UPDATE_INTERVAL_VALUE
):
    """
    1) Change the OvfUpdateIntervalInMinutes value via engine-config

    Args:
        value (int): New value

    Returns:
        bool: True, if update succeed, otherwise False
    """
    logger.info(
        "Change engine-config parameter %s to %s",
        conf.OVF_UPDATE_INTERVAL, value
    )
    cmd = [
        "{0}={1}".format(conf.OVF_UPDATE_INTERVAL, value)
    ]
    if not conf.ENGINE.engine_config(action="set", param=cmd).get("results"):
        logger.error(
            "Failed to set %s option to %s",
            conf.OVF_UPDATE_INTERVAL, value
        )
        return False
    return True


def run_hosted_engine_cli_command(resource, command):
    """
    Run the hosted engine command on a given resource

    Args:
        resource (VDS): VDS instance
        command (list): Command to run
    """
    cmd = [conf.HOSTED_ENGINE_CMD] + command
    resource.run_command(cmd)


def restart_he_vm():
    """
    Restart the HE VM
    """
    run_hosted_engine_cli_command(
        resource=conf.VDS_HOSTS[0], command=["--vm-poweroff"]
    )
    run_hosted_engine_cli_command(
        resource=conf.VDS_HOSTS[0], command=["--vm-start"]
    )


def check_he_vm_memory_via_engine(expected_value):
    """
    Check that HE VM memory equals to the expected value via engine

    Args:
        expected_value (int): Expected amount of the memory

    Returns:
        bool: True, if expected value equals to the engine value,
            otherwise False
    """
    test_libs.testflow.step(
        "Check via engine that HE VM has memory equal to %s", expected_value
    )
    return expected_value == ll_vms.get_vm_memory(vm_name=conf.HE_VM_NAME)


def check_he_vm_cpu_via_engine(expected_value):
    """
    Check that HE VM number of CPU's equals to the expected value via engine

    Args:
        expected_value (int): Expected amount of the CPU's

    Returns:
        bool: True, if expected value equals to the engine value,
            otherwise False
    """
    test_libs.testflow.step(
        "Check via engine that HE VM has amount of CPU's equal to %s",
        expected_value
    )
    return expected_value == ll_vms.get_vm_processing_units_number(
        vm_name=conf.HE_VM_NAME
    )


def check_he_vm_nic_via_engine(nic_name):
    """
    Check that HE VM has specific NIC via engine

    Args:
        nic_name (str): VM NIC name

    Returns:
        bool: True, if HE VM has NIC, otherwise False
    """
    try:
        test_libs.testflow.step(
            "Check via engine that HE VM has NIC %s", nic_name
        )
        ll_vms.get_vm_nic(vm=conf.HE_VM_NAME, nic=nic_name)
    except exceptions.EntityNotFound:
        return False
    return True


def check_he_vm_memory_via_guest_os(expected_value):
    """
    Check that HE VM memory equal to the expected value via guest OS

    Args:
        expected_value (int): Expected amount of the memory

    Returns:
        bool: True, if expected value equals to the guest OS value,
            otherwise False
    """
    rc, out, _ = conf.ENGINE_HOST.run_command(command=["cat", "/proc/meminfo"])
    if rc:
        return False
    matched = re.search(r'^MemTotal:\s+(\d+)', out)
    if not matched:
        return False
    vm_os_memory = int(matched.groups()[0]) * 1024
    error = 512 * conf.MB
    test_libs.testflow.step(
        "Check via guest OS that HE VM has memory equal to %s", expected_value
    )
    return expected_value - error <= vm_os_memory <= expected_value + error


def check_he_vm_cpu_via_guest_os(expected_value):
    """
    Check that HE VM memory equal to the expected value via guest OS

    Args:
        expected_value (int): Expected amount of the CPU's

    Returns:
        bool: True, if expected value equals to the guest OS value,
            otherwise False
    """
    rc, out, _ = conf.ENGINE_HOST.run_command(command=["lscpu"])
    if rc:
        return False
    matched = re.search(r"CPU\(s\):\s+(\d+)", out)
    if not matched:
        return False
    vm_os_cpus = int(matched.groups()[0])
    test_libs.testflow.step(
        "Check via guest OS that HE VM has amount of CPU's equal to %s",
        expected_value
    )
    return vm_os_cpus == expected_value


def check_he_vm_nic_via_guest_os(nic_name):
    """
    Check that HE VM has specific NIC via guest OS

    Args:
        nic_name (str): VM NIC name

    Returns:
        bool: True, if HE VM has NIC, otherwise False
    """
    vm_os_nics = conf.ENGINE_HOST.network.all_interfaces()
    test_libs.testflow.step(
        "Check via guest OS that HE VM has NIC %s", nic_name
    )
    return nic_name in vm_os_nics


def apply_new_parameters_on_he_vm():
    """
    1) Wait for the OVF update
    2) Restart HE VM
    3) Wait until the engine will be UP
    """
    logger.info("Wait until OVF update")
    sleep(conf.WAIT_FOR_OVF_UPDATE)
    logger.info("Restart HE VM")
    restart_he_vm()
    logger.info("Wait until the engine will be UP")
    return conf.ENGINE.wait_for_engine_status_up(timeout=conf.SAMPLER_TIMEOUT)


# noinspection PyTypeChecker
def wait_until_host_will_deploy_he(
    host_name,
    negative=False,
    timeout=conf.SAMPLER_TIMEOUT,
    sleep=conf.SAMPLER_SLEEP
):
    """
    Wait until the host will deploy hosted engine

    Args:
        host_name (str): Host name
        negative (bool): Positive or negative behaviour
        timeout (int): Sampler timeout
        sleep (int): Sampler sleep

    Returns:
        bool: True, if host is HE configured and negative=False or
            if host is not HE configured and negative=True, otherwise False
    """
    sampler = TimeoutingSampler(
        timeout=timeout,
        sleep=sleep,
        func=ll_hosts.is_hosted_engine_active,
        host_name=host_name
    )
    try:
        for sample in sampler:
            if sample != negative:
                return True
    except exceptions.APITimeout:
        logger.error(
            "Host does not HE configured after %s seconds", timeout
        )
        return False


def get_hosts_he_attrs(hosts_names, he_attr):
    """
    Get hosts hosted engine attribute values

    Args:
        hosts_names (list): Hosts names
        he_attr (str): Hosted engine object attribute name

    Returns:
        list: Hosts hosted engine attribute values
    """
    hosts_he_attr_values = list()
    for host_name in hosts_names:
        host_he_obj = ll_hosts.get_hosted_engine_obj(host_name=host_name)
        if not host_he_obj:
            return list()
        host_he_attr_value = getattr(host_he_obj, he_attr)
        logger.debug(
            "Host %s hosted engine attribute %s: %s",
            host_name, he_attr, host_he_attr_value
        )
        hosts_he_attr_values.append(host_he_attr_value)

    return hosts_he_attr_values


def wait_for_hosts_he_attributes(
    hosts_names,
    expected_values,
    timeout=conf.UPDATE_HE_STATS_TIMEOUT,
    sleep=conf.SAMPLER_SLEEP
):
    """
    Wait until hosts will have hosted engine attributes
    values equal to the expected values

    Args:
        hosts_names (list): Host names
        expected_values (dict): Expected values
            {he_attr_name: he_attr_expected_values, ...}
        timeout (int): Sampler timeout in seconds
        sleep (int): Sampler sleep interval in seconds

    Returns:
        bool: True, if all hosts have hosted engine attributes values equal
            to expected values, otherwise False
    """
    for he_attr, expected_value in expected_values.iteritems():
        u_libs.testflow.step(
            "Wait until the HE attribute %s of hosts %s will be equal to %s",
            he_attr, hosts_names, expected_value
        )
        sampler = TimeoutingSampler(
            timeout=timeout,
            sleep=sleep,
            func=get_hosts_he_attrs,
            hosts_names=hosts_names,
            he_attr=he_attr
        )
        try:
            for sample in sampler:
                status = all(
                    [
                        host_he_attr_value == expected_value
                        for host_he_attr_value in sample
                    ]
                )
                if status:
                    break
        except exceptions.APITimeout:
            logger.error(
                "Hosts %s does not have the expected %s"
                "HE attribute value after %s seconds",
                hosts_names, expected_values, timeout
            )
            return False
    return True
