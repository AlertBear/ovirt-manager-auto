"""
HE HA test helpers
"""
import logging
import os
import socket
import time

import art.core_api.apis_exceptions as core_errors
import art.core_api.apis_utils as utils
import config as conf

logger = logging.getLogger(__name__)


def locate_he_stats_script():
    """
    Locate HE stats script on the slave

    Returns:
        str: Path of the HE stats script
    """
    dir_path = os.path.dirname(os.path.realpath(__file__))
    return os.path.join(dir_path, conf.HE_STATS_SCRIPT_NAME)


def get_resource_by_name(host_name):
    """
    Get VDS object by name

    Args:
        host_name (str): Host FQDN or IP

    Returns:
        VDS: VDS resource
    """
    for vds_resource in conf.VDS_HOSTS:
        logger.debug(
            "Host to search: %s; Host FQDN: %s",
            host_name, vds_resource.fqdn
        )
        if host_name in (vds_resource.ip, vds_resource.fqdn):
            return vds_resource
    return None


def get_output_from_run_cmd(host_resource, cmd, negative=False):
    """
    Run command on host and get output from it

    Args:
        host_resource (VDS): Host resource
        cmd (list): Command to run
        negative (bool):

    Returns:
        str: Command output

    Raises:
        socket.timeout
    """
    try:
        rc, out, err = host_resource.run_command(
            command=cmd,
            tcp_timeout=conf.TCP_TIMEOUT,
            io_timeout=conf.IO_TIMEOUT
        )
    except socket.timeout as e:
        if negative:
            logger.debug("Socket timeout: %s", e)
            return ""
        else:
            raise
    else:
        assert bool(rc) == negative
        return out


def get_he_stats(command_executor):
    """
    Get output of the HE stats script and generate
    dictionary where the key is hostname

    Args:
        command_executor (VDS): Host resource to execute the command

    Returns:
        dict: HE stats
    """
    cmd = ["python", conf.SCRIPT_DEST_PATH]
    status_dict = eval(command_executor.run_command(command=cmd)[1])
    stat_d = {}
    for host_d in status_dict.itervalues():
        if conf.HOSTNAME in host_d:
            hostname = host_d[conf.HOSTNAME]
            stat_d[hostname] = {}
            for he_stat in conf.HE_STATS:
                if he_stat == conf.ENGINE_STATUS:
                    engine_status = eval(host_d[conf.ENGINE_STATUS])
                    for he_vm_stat in conf.HE_VM_STATS:
                        stat_d[hostname][he_vm_stat] = engine_status.get(
                            he_vm_stat
                        )
                else:
                    stat_d[hostname][he_stat] = host_d.get(he_stat)
    logger.debug("HE Dictionary: %s", stat_d)
    return stat_d


def get_number_of_he_hosts(host_resource):
    """
    Get from the metadata the number of HE hosts

    Args:
        host_resource (VDS): Host resource

    Returns:
        int: The number of the HE hosts
    """
    return len(get_he_stats(host_resource).keys())


def wait_until_he_metadata(host_resource, expected_number_of_he_hosts):
    """
    Wait until the HE metadata will have information about HE hosts

    Args:
        host_resource (VDS): Host resource
        expected_number_of_he_hosts (int): The expected number of HE hosts

    Returns:
        bool: True, if the metadata has expected number of hosts,
            otherwise False
    """
    sampler = utils.TimeoutingSampler(
        conf.SAMPLER_TIMEOUT,
        conf.SAMPLER_SLEEP,
        get_number_of_he_hosts,
        host_resource
    )
    try:
        for sample in sampler:
            logger.info(
                "Wait until the metadata will have information about %s hosts",
                expected_number_of_he_hosts
            )
            if sample == expected_number_of_he_hosts:
                return True
    except core_errors.APITimeout:
        logger.error(
            "The metadata still does not have "
            "information about %s hosts",
            expected_number_of_he_hosts
        )
        return False


def get_host_he_stat(command_executor, host_resource, he_stat):
    """
    Get host HE stat

    Args:
        command_executor (VDS): Host resource to execute the command
        host_resource (VDS): Host resource
        he_stat (list): Host HE stat

    Returns:
        HE host stat
    """
    return get_he_stats(
        command_executor=command_executor
    ).get(host_resource.fqdn).get(he_stat)


def get_hosts_he_stats(command_executor, host_resources, he_stat):
    """
    Get host HE stat

    Args:
        command_executor (VDS): Host resource to execute the command
        host_resources (list): Host resources
        he_stat (list): Host HE stat

    Returns:
        list: HE hosts stats
    """
    he_stats = get_he_stats(command_executor=command_executor)
    hosts_he_stats = []
    for host_resource in host_resources:
        hosts_he_stats.append(
            he_stats.get(host_resource.fqdn).get(he_stat)
        )
    return hosts_he_stats


def wait_for_host_he_stat(
    command_executor,
    host_resource,
    he_stat,
    timeout=conf.SAMPLER_TIMEOUT,
    **kwargs
):
    """
    Wait until the host will have HE parameter equal to the expected value

    Args:
        command_executor (VDS): Host resource to execute the command
        host_resource (VDS): Host resource
        he_stat (list): Host HE stat
        timeout (int): Sampler timeout

    Keyword Args:
        live-data (bool): HE up-to-date status
        score (int): HE score
        vm (str): HE VM state
        health (str): HE VM health

    Returns:
        bool: True, if host has HE parameter equal to the expected value,
            otherwise False
    """
    sampler = utils.TimeoutingSampler(
        timeout,
        conf.SAMPLER_SLEEP,
        get_host_he_stat,
        command_executor,
        host_resource,
        he_stat
    )
    he_stat_expected_value = kwargs.get(he_stat)
    try:
        for sample in sampler:
            logger.info(
                "%s current %s equal to %s, when the expected value is %s",
                host_resource, he_stat, sample, he_stat_expected_value
            )
            if he_stat_expected_value == sample:
                return True
    except core_errors.APITimeout:
        logger.error(
            "%s: %s does not equal to the expected value %s",
            host_resource, he_stat, he_stat_expected_value
        )
        return False


def wait_for_host_he_up_to_date(
    command_executor, host_resource, timeout=conf.SAMPLER_TIMEOUT
):
    """
    Wait until the host will have HE up-to-date status equals to True

    Args:
        command_executor (VDS): Host resource to execute the HE command
        host_resource (VDS): Host resource
        timeout (int): Sampler timeout

    Returns:
        bool: True, if host has HE up-to-date status equals to True,
            otherwise False
    """
    expected_up_to_date_value = {conf.UP_TO_DATE: True}
    return wait_for_host_he_stat(
        command_executor=command_executor,
        host_resource=host_resource,
        he_stat=conf.UP_TO_DATE,
        timeout=timeout,
        **expected_up_to_date_value
    )


def wait_for_host_he_score(
    command_executor,
    host_resource,
    expected_score,
    timeout=conf.SAMPLER_TIMEOUT
):
    """
    Wait until the host will have the HE score equals to the expected score

    Args:
        command_executor (VDS): Host resource to execute the HE command
        host_resource (VDS): Host resource
        expected_score (int): HE expected score
        timeout (int): Sampler timeout

    Returns:
        bool: True, if host has the HE score equals to the expected score,
            otherwise False
    """
    expected_up_to_date_value = {conf.SCORE: expected_score}
    return wait_for_host_he_stat(
        command_executor=command_executor,
        host_resource=host_resource,
        he_stat=conf.SCORE,
        timeout=timeout,
        **expected_up_to_date_value
    )


def wait_for_host_he_vm_health_bad(
    command_executor, host_resource, timeout=conf.SAMPLER_TIMEOUT
):
    """
    Wait until the host will have HE VM health state equals to Bad

    Args:
        command_executor (VDS): Host resource to execute the HE command
        host_resource (VDS): Host resource
        timeout (int): Sampler timeout

    Returns:
        bool: True, if host has HE VM health state equals to Bad,
            otherwise False
    """
    expected_he_vm_health_value = {conf.ENGINE_HEALTH: conf.ENGINE_HEALTH_BAD}
    return wait_for_host_he_stat(
        command_executor=command_executor,
        host_resource=host_resource,
        he_stat=conf.ENGINE_HEALTH,
        timeout=timeout,
        **expected_he_vm_health_value
    )


def wait_for_hosts_he_stats(
    command_executor, hosts_resources, he_stat, timeout, **kwargs
):
    """
    Wait until one of the hosts will have HE parameter
    equal to the expected value

    Args:
        command_executor (VDS): Host resource to execute the command
        hosts_resources (list): Host resource
        he_stat (list): Host HE stat
        timeout (int): Sampler timeout

    Keyword Args:
        live-data (bool): HE up-to-date status
        score (int): HE score
        vm (str): HE VM state
        health (str): HE VM health

    Returns:
        bool: True, if one of the hosts has HE parameter
            equal to the expected value, otherwise False
    """
    sampler = utils.TimeoutingSampler(
        timeout,
        conf.SAMPLER_SLEEP,
        get_hosts_he_stats,
        command_executor,
        hosts_resources,
        he_stat
    )
    he_stat_expected_value = kwargs.get(he_stat)
    hosts_fqdns = [host_resource.fqdn for host_resource in hosts_resources]
    try:
        for sample in sampler:
            logger.info(
                "Hosts %s current %s equal to %s, "
                "when the expected value is %s",
                hosts_fqdns, he_stat, sample, he_stat_expected_value
            )
            if he_stat_expected_value in sample:
                return True
    except core_errors.APITimeout:
        logger.error(
            "Hosts %s does not have %s equal to the expected value %s",
            hosts_fqdns, he_stat, he_stat_expected_value
        )
        return False


def wait_for_hosts_he_vm_up_state(
    command_executor, hosts_resources, timeout=conf.SAMPLER_TIMEOUT
):
    """
    Wait until one of the hosts will have HE VM state equal to the 'up' state

    Args:
        command_executor (VDS): Host resource to execute the command
        hosts_resources (list): Host resource
        timeout (int): Sampler timeout

    Returns:
        bool: True, if one of the hosts has HE VM state
            equal to the 'up' state, otherwise False
    """
    expected_vm_state_value = {conf.VM_STATE: conf.VM_UP}
    return wait_for_hosts_he_stats(
        command_executor=command_executor,
        hosts_resources=hosts_resources,
        he_stat=conf.VM_STATE,
        timeout=timeout,
        **expected_vm_state_value
    )


def wait_for_hosts_he_vm_health_state(
    command_executor, hosts_resources, timeout=conf.SAMPLER_TIMEOUT
):
    """
    Wait until one of the hosts will have HE VM
    health state equal to the 'good' state

    Args:
        command_executor (VDS): Host resource to execute the command
        hosts_resources (list): Host resource
        timeout (int): Sampler timeout

    Returns:
        bool: True, if one of the hosts has HE VM health state
            equal to the 'good' state, otherwise False
    """
    expected_vm_state_value = {conf.ENGINE_HEALTH: conf.ENGINE_HEALTH_GOOD}
    return wait_for_hosts_he_stats(
        command_executor=command_executor,
        hosts_resources=hosts_resources,
        he_stat=conf.ENGINE_HEALTH,
        timeout=timeout,
        **expected_vm_state_value
    )


def set_he_maintenance_mode(host_resource, mode):
    """
    Set global/local maintenance

    Args:
        host_resource (VDS): Host resource
        mode (str): HE maintenance mode(global, local or none)
    """
    cmd = [conf.HOSTED_ENGINE_CMD, "--set-maintenance", "--mode=%s" % mode]
    logger.info(
        "Set maintenance mode of host %s to %s", host_resource, mode
    )
    host_resource.run_command(command=cmd)


def run_power_management_command(
    command_executor, host_to_fence_pm, fence_command
):
    """
    Run power management command via vdsClient

    Args:
        command_executor (VDS): Host resource to execute the command
        host_to_fence_pm (dict): Target host PM
        fence_command (str): Fence command(status, on, off or reboot)

    Returns:
        bool: True if action succeeds, otherwise False
    """
    pm_args = {
        "addr": host_to_fence_pm.get(conf.PM_ADDRESS),
        "port": host_to_fence_pm.get(conf.PM_SLOT, "0"),
        "agent": host_to_fence_pm.get(conf.PM_TYPE),
        "username": host_to_fence_pm.get(conf.PM_USERNAME),
        "password": host_to_fence_pm.get(conf.PM_PASSWORD),
        "action": fence_command
    }
    out = command_executor.vds_client(cmd="Host.fenceNode", args=pm_args)
    if not out:
        logger.error(
            "%s: failed to %s host %s",
            command_executor,
            fence_command,
            host_to_fence_pm.get(conf.PM_ADDRESS)
        )
    return bool(out)


def drop_host_he_score_to_max(host_resource):
    """
    1) Put host to the local maintenance to drop host score to 0
    2) Put host to the 'none' maintenance to back host score to 3400

    Args:
        host_resource (VDS): Host resource

    Returns:
        bool: True, if all actions succeed, otherwise False
    """
    logger.info(
        "%s: put host to the '%s' maintenance",
        host_resource, conf.MAINTENANCE_LOCAL
    )
    set_he_maintenance_mode(
        host_resource=host_resource, mode=conf.MAINTENANCE_LOCAL
    )
    if not wait_for_host_he_score(
        command_executor=host_resource,
        host_resource=host_resource,
        expected_score=conf.ZERO_SCORE
    ):
        return False

    time.sleep(conf.METADATA_UPDATE_INTERVAL)

    logger.info(
        "%s: put host to the '%s' maintenance",
        host_resource, conf.MAINTENANCE_NONE
    )
    set_he_maintenance_mode(
        host_resource=host_resource, mode=conf.MAINTENANCE_NONE
    )
    logger.info(
        "Check if the host %s has maximal score %s",
        host_resource, conf.MAX_SCORE
    )
    if not wait_for_host_he_score(
        command_executor=host_resource,
        host_resource=host_resource,
        expected_score=conf.MAX_SCORE
    ):
        return False
    return True


def host_has_sanlock_share(host_resource):
    """
    Parse sanlock command `sanlock client status` and
    check if the host sanlock has 'share' status

    Args:
        host_resource (VDS): Host resource

    Returns:
        bool: True, if the host has sanlock status share, otherwise False
    """
    he_storage_domain = host_resource.run_command(
        command=["grep", "storage=", conf.HOSTED_ENGINE_CONF_FILE]
    )[1].strip().split("=")[1]
    dir_name = ("%s/" % he_storage_domain.split("/")[-1]).replace("_", "__")
    cmd = ["sanlock", "client", "status"]
    out = host_resource.run_command(command=cmd)[1]
    for line in out.splitlines():
        if dir_name in line:
            line_arr = line.strip().split()
            if line_arr[0].strip() == "r":
                return True
    return False


def check_he_vm_state_via_vdsm(host_resource, expected_state=None):
    """
    Check HE VM state via vdsClient

    Args:
        host_resource (VDS): Host resource
        expected_state (str): Expected HE VM state

    Returns:
        bool: True, if HE VM exists on the resource and has state UP
    """
    vms = host_resource.vds_client(cmd="Host.getVMList")
    if vms:
        logger.debug("%s: VM's that run %s", host_resource, vms)
        if expected_state:
            vm_id = vms[0]
            vm_info = host_resource.vds_client(
                cmd="VM.getStats", args={"vmID": vm_id}
            )
            vm_status = vm_info[0].get("status")
            return vm_status == expected_state
        return True
    return False


def wait_for_he_vm_via_vdsm(host_resource, expected_state=None):
    """
    Check that HE vm stays on the old host via vdsClient

    Args:
        host_resource (VDS): Host resource
        expected_state (str): Expected HE VM state

    Returns:
        bool: True, if the HE VM continue to run on the old host,
            otherwise False
    """
    sampler = utils.TimeoutingSampler(
        conf.WAIT_TIMEOUT,
        conf.SAMPLER_SLEEP,
        check_he_vm_state_via_vdsm,
        host_resource,
        expected_state
    )
    try:
        for sample in sampler:
            if not sample:
                logger.error(
                    "%s: HE VM does not run on the host", host_resource
                )
                return False
    except core_errors.APITimeout:
        return True
