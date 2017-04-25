"""
MOM Test Helpers
"""
import logging
import shlex

import art.rhevm_api.tests_lib.low_level.clusters as ll_clusters
import art.rhevm_api.tests_lib.low_level.hosts as ll_hosts
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import config as conf
from art.core_api.apis_exceptions import APITimeout
from art.core_api.apis_utils import TimeoutingSampler
from art.test_handler import find_test_file

logger = logging.getLogger(__name__)
find_test_file.__test__ = False


def change_mom_pressure_percentage(resource, pressure_threshold):
    """
    Change MOM pressure threshold

    Args:
        resource (VDS): VDS resource
        pressure_threshold (str): MOM defvar pressure threshold

    Returns:
        bool: True, if succeed to change pressure threshold, otherwise False
    """
    logger.info(
        "Change MOM pressure_threshold to %s", pressure_threshold
    )
    command = "sed -i 's/{0} [0-9\.]*/{0} {1}/' {2}".format(
        conf.DEFVAR_PRESSURE_THRESHOLD,
        pressure_threshold,
        conf.BALLOON_FILE
    )
    if resource.run_command(command=shlex.split(command))[0]:
        return False
    return resource.service(conf.MOM_SERVICE).restart()


def change_swapping(resource, enable):
    """
    Enable or disable swap on resource

    Args:
        resource (VDS): VDS resource
        enable (bool): Swap flag

    Returns:
        bool: True, if succeed to change swap state, otherwise False
    """
    command = "swapon" if enable else "swapoff"
    return not bool(
        resource.run_command([command, "-a"])[0]
    )


def allocate_host_memory(perc=0.7):
    """
    Saturate host memory to given percent

    Args:
        perc (float): Memory saturation percent(1 - full saturation)

    Returns:
        str: Memory allocation PID
    """
    host_free_memory = ll_hosts.get_host_free_memory(host_name=conf.HOSTS[0])
    allocate_memory = int(host_free_memory * perc)
    logger.info(
        "Allocating %s B of memory on host %s", allocate_memory, conf.HOSTS[0]
    )
    rc, out, _ = conf.VDS_HOSTS[0].run_command(
        [
            "python", conf.HOST_ALLOC_PATH, str(allocate_memory),
            "&>", "/tmp/OUT1", "&", "echo", "$!"
        ]
    )
    return out.strip()


def cancel_host_allocation(pid):
    """
    Cancel host host memory allocation

    Args:
        pid (str): Memory allocation PID
    """
    logger.info("Kill memory allocation process on host %s", conf.HOSTS[0])
    assert not conf.VDS_HOSTS[0].run_command(["kill", "-9", pid])[0]
    assert not conf.VDS_HOSTS[0].fs.exists("/proc/%s" % pid)


def is_ksm_running(resource):
    """
    Check KSM state on host resource

    Args:
        resource (VDS): VDS resource

    Returns:
        bool: KSM state
    """
    ksm_state = resource.vds_client(cmd="Host.getStats").get("ksmState")
    logger.info("KSM state on resource %s is %s", resource, ksm_state)
    return ksm_state


def wait_for_ksm_state(resource):
    """
    Wait for KSM state True on the resource

    Args:
        resource (VDS): VDS resource

    Returns:
        bool: True, if KSM state on the resource equal to True before timeout,
            otherwise False
    """
    sampler = TimeoutingSampler(
        timeout=conf.SAMPLER_TIMEOUT,
        sleep=conf.SAMPLER_SLEEP,
        func=is_ksm_running,
        resource=resource
    )
    logger.info(
        "Wait until resource %s KSM state will be equal to True", resource
    )
    try:
        for sample in sampler:
            if sample:
                return True
    except APITimeout:
        logger.error(
            "Resource KSM state on the resource %s equal to False", resource
        )
        return False


def get_vms_ballooning_info(vm_list):
    """
    Get VM's ballooning information from VDSM

    Args:
        vm_list (list): VM's names

    Returns:
        dict: Vm's ballooning stats
    """
    mom_dict = {}
    for vm_name in vm_list:
        vm_id = ll_vms.get_vm(vm=vm_name).get_id()
        vm_stats = conf.VDS_HOSTS[0].vds_client(
            cmd="VM.getStats", args={"vmID": vm_id}
        )
        if not vm_stats:
            return mom_dict
        vm_stats = vm_stats[0]
        mom_dict[vm_name] = {}
        if conf.VM_BALLOON_INFO in vm_stats:
            vm_balloon_info = vm_stats[conf.VM_BALLOON_INFO]
            for balloon_stat in (conf.VM_BALLOON_CURRENT, conf.VM_BALLOON_MAX):
                mom_dict[vm_name][balloon_stat] = int(
                    vm_balloon_info[balloon_stat]
                )
    logger.debug("MOM dictionary: %s", mom_dict)
    return mom_dict


def check_vms_balloon_state(vm_list, deflation=True):
    """
    Check VM's balloon deflation or inflation

    Args:
        vm_list (list): VM's names
        deflation (bool): Deflation state

    Returns:
        bool: True, if balloon has expected state, otherwise False
    """
    vms_ballooning_info = get_vms_ballooning_info(vm_list=vm_list)
    if not vms_ballooning_info:
        logger.error(
            "Failed to get VM's ballooning information from the host %s",
            conf.HOSTS[0]
        )
        return False
    for vm_name in vm_list:
        vm_ballooning_info = vms_ballooning_info[vm_name]
        if not vm_ballooning_info:
            logger.error(
                "Failed to get VM %s ballooning information from the host %s",
                vm_name, conf.HOSTS[0]
            )
            return False
        balloon_cur = vm_ballooning_info[conf.VM_BALLOON_CURRENT]
        balloon_max = vm_ballooning_info[conf.VM_BALLOON_MAX]
        logger.info(
            "VM %s has %s equal to %s and %s equal to %s",
            vm_name,
            conf.VM_BALLOON_MAX,
            balloon_max,
            conf.VM_BALLOON_CURRENT,
            balloon_cur
        )
        if (balloon_max - 1024 > balloon_cur) == deflation:
            return True
    return False


def wait_for_vms_balloon_state(
    vm_list,
    deflation=True,
    negative=False,
    timeout=conf.SAMPLER_TIMEOUT,
    sleep=conf.SAMPLER_SLEEP
):
    """
    Wait until VM's ballooning will have correct state,
    balloon can deflate or inflate

    Args:
        vm_list (list): VM's names
        deflation (bool): Deflation state
        negative (bool): Negative or positive test
        timeout (int): Sampler timeout
        sleep (int): Sampler sleep

    Returns:
        bool: True, if balloon state of all VM's has expected state,
            otherwise False
    """
    sampler = TimeoutingSampler(
        timeout=timeout,
        sleep=sleep,
        func=check_vms_balloon_state,
        vm_list=vm_list,
        deflation=deflation
    )
    balloon_msg = "deflate" if deflation else "inflate"
    logger.info(
        "Wait until VM's %s balloons will %s", vm_list, balloon_msg
    )
    try:
        for sample in sampler:
            if sample != negative:
                return True
    except APITimeout:
        logger.error("VM's %s balloons do not %s", vm_list, balloon_msg)
        return False


def enable_host_ballooning(enable=True):
    """
    1) Update cluster ballooning
    2) Deactivate the host
    3) Activate the host

    Args:
        enable (bool): Enable or disable ballooning on the cluster

    Returns:
        bool: True, if all actions succeeds, otherwise False
    """
    if not ll_clusters.updateCluster(
        positive=True,
        cluster=conf.CLUSTER_NAME[0],
        ballooning_enabled=enable
    ):
        return False
    if not ll_hosts.deactivate_host(
        positive=True, host=conf.HOSTS[0], host_resource=conf.VDS_HOSTS[0]
    ):
        return False
    return ll_hosts.activate_host(
        positive=True, host=conf.HOSTS[0], host_resource=conf.VDS_HOSTS[0]
    )
