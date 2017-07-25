"""
Helper for SLA tests
"""

import logging
import re

import art.core_api.apis_exceptions as apis_exceptions
import art.rhevm_api.tests_lib.high_level.vms as hl_vms
import art.rhevm_api.tests_lib.low_level.clusters as ll_clusters
import art.rhevm_api.tests_lib.low_level.datacenters as ll_datacenters
import art.rhevm_api.tests_lib.low_level.hosts as ll_hosts
import art.rhevm_api.tests_lib.low_level.sla as ll_sla
import art.rhevm_api.tests_lib.low_level.storagedomains as ll_sds
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import art.test_handler.exceptions as errors
import config as conf
from art.core_api import apis_utils
from art.core_api.apis_exceptions import APITimeout
from art.core_api.apis_utils import TimeoutingSampler
from art.unittest_lib import testflow
from concurrent.futures import ThreadPoolExecutor
from rhevmtests import helpers

logger = logging.getLogger(__name__)


def _wait_for_host_cpu_load(
    host_name, expected_min_load=0,
    expected_max_load=100, timeout=180, sleep=10
):
    """
    Wait until host will reach cpu load between minimal and maximal values

    Args:
        host_name (str): hosts names
        expected_min_load (int): wait for host cpu load greater
            than expected minimum value
        expected_max_load (int): wait for host cpu load smaller
            than expected maximum value
        timeout (int): sampler timeout
        sleep (int): sampler sleep

    Returns:
        bool: True, if host reach cpu load between expected minimal and
            maximal values before timeout, otherwise False
    """
    sampler = TimeoutingSampler(
        timeout, sleep, ll_hosts.get_host_cpu_load, host_name
    )
    logger.info(
        "Wait until host %s will have cpu load between %d and %d",
        host_name, expected_min_load, expected_max_load
    )
    try:
        for sample in sampler:
            logger.info(
                "Host %s cpu load equal to %d", host_name, sample
            )
            if expected_max_load >= sample >= expected_min_load:
                return True
    except APITimeout:
        logger.error(
            "Host %s cpu load not between expected values %d and %d",
            host_name, expected_min_load, expected_max_load
        )
        return False


def wait_for_hosts_cpu_load(
    hosts,
    expected_min_load=0,
    expected_max_load=100,
    timeout=180,
    sleep=10
):
    """
    Wait until hosts will reach cpu load between minimal and maximal values

    Args:
        hosts (list): hosts names
        expected_min_load (int): wait for host cpu load greater
            than expected minimum value
        expected_max_load (int): wait for host cpu load smaller
            than expected maximum value
        timeout (int): sampler timeout
        sleep (int): sampler sleep

    Returns:
        bool: True, if all hosts reach cpu load between expected minimal and
            maximal values before timeout, otherwise False
    """
    results = []
    with ThreadPoolExecutor(max_workers=len(hosts)) as executor:
        for host in hosts:
            results.append(
                executor.submit(
                    _wait_for_host_cpu_load,
                    host, expected_min_load, expected_max_load, timeout, sleep
                )
            )
    for result in results:
        if not result.result():
            return False
    return True


def _start_and_wait_for_cpu_load_on_resources(load, hosts_d):
    """
    1) Start specific load on resources and
    2) Wait until CPU load on resource will reach given values

    Args:
        load (int): CPU load
        hosts_d (dict): host and resource dictionary

    Raises:
        HostException: if one of internal functions failed
    """
    if not ll_sla.load_resources_cpu(
        hosts_d[conf.RESOURCE], load
    ):
        raise errors.HostException()
    if not wait_for_hosts_cpu_load(
        hosts=hosts_d[conf.HOST],
        expected_min_load=load - 5
    ):
        raise errors.HostException()


def start_and_wait_for_cpu_load_on_resources(load_to_host_d):
    """
    1) Start specific loads on resources
    2) Wait until CPU loads on resources will reach given values

    Args:
        load_to_host_d (dict): load to host and resource mapping

    Raises:
        HostException: if one of internal functions failed
    """
    results = []
    with ThreadPoolExecutor(
        max_workers=len(load_to_host_d.keys())
    ) as executor:
        for load, hosts_d in load_to_host_d.iteritems():
            results.append(
                executor.submit(
                    _start_and_wait_for_cpu_load_on_resources, load, hosts_d
                )
            )
    for result in results:
        if result.exception():
            raise result.exception()


def stop_load_on_resources(hosts_and_resources_l):
    """
    Stop CPU load on resources

    Args:
        hosts_and_resources_l (list): list of hosts and resources dictionaries
    """
    hosts = []
    resources = []
    for host_and_resource in hosts_and_resources_l:
        hosts += host_and_resource[conf.HOST]
        resources += host_and_resource[conf.RESOURCE]
    ll_sla.stop_cpu_load_on_resources(resources)
    wait_for_hosts_cpu_load(
        hosts=hosts, expected_max_load=10
    )


def wait_for_hosts_state_in_cluster(
    num_of_hosts,
    timeout,
    sleep,
    cluster_name,
    state=conf.HOST_UP,
    negative=False
):
    """
    Wait until number of hosts in given cluster will have specific state

    Args:
        num_of_hosts (int): Expected number of hosts with given state
        timeout (int): Sampler timeout
        sleep (int): Sampler sleep time
        cluster_name (str): Cluster name
        state (str): Expected hosts state
        negative (bool): Negative or positive flow

    Returns:
        bool: True, if engine have given number of hosts in given state,
            otherwise False
    """
    cluster_obj = ll_clusters.get_cluster_object(cluster_name=cluster_name)
    log_msg = "not equal" if negative else "equal"
    sampler = TimeoutingSampler(
        timeout=timeout,
        sleep=sleep,
        func=ll_hosts.HOST_API.get,
        abs_link=False
    )
    try:
        for sample in sampler:
            count = 0
            for host in sample:
                if host.get_cluster().get_id() == cluster_obj.get_id():
                    if host.get_status() == state:
                        count += 1
            if (count == num_of_hosts) == (not negative):
                return True
    except APITimeout:
        logger.error(
            "Timeout when waiting for hosts with state %s, will be %s to %d",
            state, log_msg, num_of_hosts
        )
        return False


def wait_for_active_vms_on_host(
    host_name,
    expected_num_of_vms,
    sampler_timeout=300,
    sampler_sleep=10,
    negative=False
):
    """
    Wait for specific number of active vms on host

    Args:
        host_name (str): Host name
        expected_num_of_vms (int): Expected number of VM's on host
        negative (bool): Wait for positive or negative status
        sampler_timeout (int): Sampler timeout
        sampler_sleep (int): Sampler sleep

    Returns:
        bool: True, if host has expected number of vms, otherwise False
    """
    sampler = TimeoutingSampler(
        sampler_timeout, sampler_sleep, ll_hosts.HOST_API.find, val=host_name
    )
    try:
        for sample in sampler:
            active_vms = sample.get_summary().get_active()
            logger.info(
                "Number of active VM's on the host %s: %s",
                sample.get_name(), active_vms
            )
            if (active_vms == expected_num_of_vms) == (not negative):
                return True
    except APITimeout:
        logger.error(
            "Timeout when waiting for number of vms %d on host %s",
            expected_num_of_vms, host_name
        )
        return False


def wait_for_active_vms_on_hosts(
    hosts,
    expected_num_of_vms,
    sampler_timeout=300,
    sampler_sleep=10,
    negative=False
):
    """
    Wait for specific number of active vms on hosts

    Args:
        hosts (list): Hosts names
        expected_num_of_vms (int): Expected number of VM's on host
        negative (bool): Wait for positive or negative status
        sampler_timeout (int): Sampler timeout
        sampler_sleep (int): Sampler sleep

    Returns:
        bool: True, if all hosts has expected number of vms, otherwise False
    """
    results = []
    with ThreadPoolExecutor(max_workers=len(hosts)) as executor:
        for host in hosts:
            results.append(
                executor.submit(
                    wait_for_active_vms_on_host,
                    host, expected_num_of_vms,
                    sampler_timeout, sampler_sleep, negative
                )
            )
    for result in results:
        if not result.result():
            return False
    return True


def stop_all_ge_vms_and_update_to_default_params():
    """
    1) Stop all GE VM's
    2) Update all GE VM's to default parameters
    """
    ll_vms.stop_vms_safely(vms_list=conf.VM_NAME)
    with ThreadPoolExecutor(max_workers=len(conf.VM_NAME)) as executor:
        for vm in conf.VM_NAME:
            executor.submit(
                ll_vms.updateVm, True, vm, **conf.DEFAULT_VM_PARAMETERS
            )


def get_pinning_information(host_resource, vm_name):
    """
    Get from virsh VM pinning information

    Args:
        host_resource (VDS): Host resource
        vm_name (str): Vm name

    Returns:
        dict: Vm pinning information
    """
    vcpu_info_d = {}
    vcpu_info = host_resource.run_command(
        ["virsh", "-r", "vcpuinfo", vm_name]
    )[1]
    pattern = r"VCPU:\s*(\d+)\s*\nCPU:\s*(\d+).*CPU Affinity:\s*([y-]+)"
    reg_exp_res = re.findall(pattern=pattern, string=vcpu_info, flags=re.S)
    for key, value in zip(
        (conf.VCPU, conf.CPU, conf.CPU_AFFINITY), reg_exp_res[0]
    ):
        vcpu_info_d[key] = value
    return vcpu_info_d


def check_vm_cpu_pinning(host_resource, vm_name, expected_pinning):
    """
    Check if VM pinning information equal to expected one

    Args:
        host_resource (VDS): Host resource
        vm_name (str): Vm name
        expected_pinning (dict): Expected VM pinning information

    Returns:
        bool: True, if real VM pinning information equal to expected one,
            otherwise False
    """
    vcpu_info_d = get_pinning_information(
        host_resource=host_resource, vm_name=vm_name
    )
    for key, value in expected_pinning.iteritems():
        if str(vcpu_info_d[key]) != str(value):
            return False
    return True


def get_cpu_info(resource):
    """
    Get CPU info from resource

    Args:
        resource (VDS): resource

    Returns:
        dict: Cpu info dictionary
    """
    cpu_d = {}
    rc, out, _ = resource.run_command(['cat', '/proc/cpuinfo'])
    if rc:
        logger.error("Failed to get CPU info from %s", resource)
        return cpu_d
    for line in out.split('\n')[:-1]:
        if line == "":
            break
        name, value = line.split(':')
        cpu_d[name.strip()] = value.strip()
    return cpu_d


def get_numa_aware_ksm_status(resource):
    """
    Get status if KSM merge pages across NUMA node

    Args:
        resource (VDS): VDS resource

    Returns:
        bool: True, if KSM merge pages across NUMA nodes, otherwise False
    """
    cmd = ["cat", conf.NUMA_AWARE_KSM_FILE]
    return bool(int(resource.run_command(command=cmd)[1]))


def wait_for_numa_aware_ksm_status(
    resource, expected_value, sampler_timeout=60, sampler_sleep=5
):
    """
    Wait for host NUMA aware KSM state

    Args:
        resource (VDS): VDS resource
        expected_value (bool): Expected value
        sampler_timeout (int): Sampler timeout
        sampler_sleep (int): Sampler sleep

    Returns:
        bool: True, if host NUMA aware KSM state equal to expected value,
            otherwise False
    """
    sampler = TimeoutingSampler(
        sampler_timeout, sampler_sleep, get_numa_aware_ksm_status, resource
    )
    try:
        for sample in sampler:
            if sample == expected_value:
                return True
    except APITimeout:
        logger.error(
            "%s still does not have expected NUMA aware KSM state %s",
            resource, expected_value
        )
        return False


def wait_for_vm_gets_to_full_consumption(vm_name, expected_load):
    """
    Wait until VM gets to full CPU consumption.
    Check that the value is as expected 3 times,
    in order to be sure the CPU value is stable

    Args:
        vm_name (str): VM name
        expected_load (int): Expected VM CPU load

    Returns:
        bool: True if VM gets to the expected CPU load, False otherwise
    """
    count = 0
    sampler = apis_utils.TimeoutingSampler(
        timeout=conf.SAMPLER_TIMEOUT,
        sleep=conf.SAMPLER_SLEEP,
        func=hl_vms.get_vm_cpu_consumption_on_the_host,
        vm_name=vm_name
    )
    for sample in sampler:
        try:
            if expected_load - 3 <= sample <= expected_load + 3:
                logging.info(
                    "Current CPU usage is as expected: %d" % expected_load
                )
                count += 1
                if count == 3:
                    return True
            else:
                logging.warning(
                    "CPU usage of %s is %d, waiting for "
                    "usage will be %d, 3 times",
                    vm_name, sample, expected_load
                )
        except apis_exceptions.APITimeout:
            logging.error(
                "Timeout when trying to get VM %s CPU consumption", vm_name
            )
    return False


def wait_for_vms_gets_to_full_consumption(expected_values):
    """
    Wait until VMs gets to full CPU consumption

    Args:
        expected_values (dict): Expected VM's CPU load

    Returns:
        bool: True if all VM's get to the expected CPU load, False otherwise
    """
    results = list()
    with ThreadPoolExecutor(max_workers=len(expected_values.keys())) as e:
        for vm_name, expected_load in expected_values.iteritems():
            logger.info("Checking consumption on the VM %s", vm_name)
            results.append(
                e.submit(
                    fn=wait_for_vm_gets_to_full_consumption,
                    vm_name=vm_name,
                    expected_load=expected_load
                )
            )

    for vm_name, result in zip(expected_values.keys(), results):
        if result.exception():
            logger.error(
                "Got exception while checking the VM %s consumption: %s",
                vm_name, result.exception()
            )
            raise result.exception()
        if not result.result():
            raise errors.VMException("Cannot get VM %s consumption" % vm_name)
    return True


def load_vm_and_check_the_load(load_dict, expected_values=None):
    """
    1) Load VM's
    2) Verify that VM's have expected CPU load percentage

    Args:
        load_dict (dict): CPU load parameters
        expected_values (dict): Expected CPU load percentage

    Returns:
        bool: True, if VM has expected CPU load, otherwise False
    """
    if expected_values is None:
        expected_values = load_dict
    for vm_name, load_value in load_dict.iteritems():
        vm_ip = hl_vms.get_vm_ip(vm_name=vm_name)
        vm_res = helpers.get_host_resource(
            ip=vm_ip, password=conf.VMS_LINUX_PW
        )
        testflow.step("Load VM %s CPU to 100 percent", vm_name)
        if not ll_sla.load_resource_cpu(resource=vm_res, load=100):
            logger.error("Failed to load VM %s CPU", vm_name)
            return False
    testflow.step(
        "Wait until VM's CPU load will be equal to expected values: %s",
        expected_values
    )
    if not wait_for_vms_gets_to_full_consumption(
        expected_values=expected_values
    ):
        return False
    return True


def wait_for_host_scheduling_memory(
    host_name,
    expected_sch_memory,
    sampler_timeout=120,
    sampler_sleep=conf.SAMPLER_SLEEP
):
    """
    Wait until the host will have expected amount of scheduling memory

    Args:
        host_name (str): Host name
        expected_sch_memory (int): Expected scheduling memory
        sampler_timeout (int): Sampler timeout
        sampler_sleep (int): Sampler sleep time

    Returns:
        bool: True, if the host has expected scheduling memory
            before it reaches timeout, otherwise False
    """
    sampler = apis_utils.TimeoutingSampler(
        timeout=sampler_timeout,
        sleep=sampler_sleep,
        func=ll_hosts.get_host_max_scheduling_memory,
        host_name=host_name
    )
    error = 256 * conf.MB
    for sample in sampler:
        try:
            if (
                expected_sch_memory - error <=
                sample <=
                expected_sch_memory + error
            ):
                return True
        except apis_exceptions.APITimeout:
            logging.error(
                "Host %s has unexpected amount of scheduling memory: %sMb",
                host_name, sample / conf.MB
            )
    return False


def wait_for_dc_and_storagedomains():
    """
    1) Wait for datacenter state 'UP'
    2) Wait for storage domains status 'ACTIVE'

    Returns:
        bool: True, if all actions succeed, otherwise False
    """
    testflow.setup(
        "Wait until the datacenter %s will have state equal to 'UP'",
        conf.DC_NAME[0]
    )
    if not ll_datacenters.waitForDataCenterState(
        name=conf.DC_NAME[0]
    ):
        return False
    testflow.setup(
        "Wait until all storage domains will have state equal to '%s'",
        conf.SD_ACTIVE
    )
    results = []
    storage_domains = ll_sds.getDCStorages(
        datacenter=conf.DC_NAME[0], get_href=False
    )
    with ThreadPoolExecutor(max_workers=len(storage_domains)) as executor:
        for storage_domain in storage_domains:
            if storage_domain.get_type() == ll_sds.DATA_DOMAIN_TYPE:
                results.append(
                    executor.submit(
                        ll_sds.wait_for_storage_domain_status,
                        True,
                        conf.DC_NAME[0],
                        storage_domain.get_name(),
                        conf.SD_ACTIVE
                    )
                )
    for result in results:
        if result.exception():
            logger.error(result.exception())
            return False
    return True


def get_pci_device(host_name):
    """
    Get PCI device with IOMMU from the host

    Args:
        host_name (str): Host name

    Returns:
        HostDevice: Host device with IOMMU
    """
    host_devices = ll_hosts.get_host_devices(host_name=host_name)
    for host_device in host_devices:
        device_product = host_device.get_product()
        if device_product:
            for correct_product in conf.HOST_DEVICES_TO_ATTACH:
                if device_product.get_name() == correct_product:
                    return host_device
    return None
