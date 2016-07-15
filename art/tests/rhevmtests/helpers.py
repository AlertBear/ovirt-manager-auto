#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
rhevmtests helper functions
"""
import functools
import logging
import os
from rrmngmnt import ssh
import config
from art.rhevm_api.resources import User, Host, storage
import art.rhevm_api.tests_lib.high_level.vms as hl_vms
from art.rhevm_api.tests_lib.low_level import (
    disks as ll_disks,
    vms as ll_vms,
    jobs as ll_jobs,
    hosts as ll_hosts,
    templates as ll_templates,
    storagedomains as ll_sd,
)
from art.rhevm_api.tests_lib.high_level import storagedomains as hl_sd
from art.rhevm_api.utils.test_utils import wait_for_tasks
from art.rhevm_api.utils import cpumodel
from utilities.foremanApi import ForemanActions
from concurrent.futures import ThreadPoolExecutor
import art.test_handler.exceptions as errors
import art.core_api.apis_exceptions as apis_exceptions
from art.core_api import apis_utils

NFS = config.STORAGE_TYPE_NFS
GULSTERFS = config.STORAGE_TYPE_GLUSTER
GLUSTER_MNT_OPTS = ['-t', 'glusterfs']
NFS_MNT_OPTS = ['-t', 'nfs', '-v', '-o', 'vers=3']

logger = logging.getLogger(__name__)


def get_golden_template_name(cluster=config.CLUSTER_NAME[0]):
    """
    Return golden environment's template name for a certain cluster

    __author__ = "cmestreg"
    :param cluster: Name of the cluster
    :type cluster: str
    :returns: Name of the template
    :rtype: str
    """
    templates = ll_templates.get_template_from_cluster(cluster)
    for template in config.TEMPLATE_NAME:
        if template in templates:
            return template
    return None


def set_passwordless_ssh(src_host, dst_host):
    """
    Set passwordless SSH to remote host

    :param src_host: Source host resource object
    :type src_host: Host
    :param dst_host: Destination host resource object
    :type dst_host: Host
    :return: True/False
    :rtype: bool
    """
    logger.info(
        "Setting passwordless ssh from engine (%s) to host (%s)",
        src_host.ip, dst_host.ip
    )
    error = "Failed to set passwordless SSH to %s" % dst_host.ip
    ssh_keyscan = ["ssh-keyscan", "-t", "rsa"]
    known_hosts = ssh.KNOWN_HOSTS % os.path.expanduser(
        "~%s" % src_host.root_user.name
    )
    authorized_keys = ssh.AUTHORIZED_KEYS % os.path.expanduser(
        "~%s" % dst_host.root_user.name
    )

    # Remove old keys from local KNOWN_HOSTS file
    if not src_host.remove_remote_host_ssh_key(dst_host):
        logger.error(error)
        return False

    # Remove local key from remote host AUTHORIZED_KEYS file
    if not dst_host.remove_remote_key_from_authorized_keys():
        logger.error(error)
        return False

    # Get local SSH key and add it to remote host AUTHORIZED_KEYS file
    local_key = src_host.get_ssh_public_key().strip()

    remote_cmd = ["echo", local_key, ">>", authorized_keys]
    rc = dst_host.run_command(remote_cmd)[0]
    if rc:
        logger.error(error)
        return False

    # Adding remote host SSH key to local KNOWN_HOSTS file
    for i in [dst_host.ip, dst_host.fqdn]:
        rc1, remote_key = src_host.run_command(ssh_keyscan + [i])[:2]
        local_cmd = ["echo", remote_key, ">>", known_hosts]
        rc2 = src_host.run_command(local_cmd)[0]
        if rc1 or rc2:
            logger.error(error)
            return False
    return True


def get_unfinished_jobs_list():
    """
    Returns list of unfinished jobs and prints theirs description to a log
    if there is some, it also prints message "There are unfinished jobs in DB"
    which is caught by groovy post build script which set build to UNSTABLE.

    __author__ = "pbalogh"
    :return: Unfinished jobs
    :rtype: list
    """
    logger.info('Check for unfinished jobs in DB')
    active_jobs = ll_jobs.get_active_jobs()
    if active_jobs:
        logger.error("There are unfinished jobs in DB")
        for job in active_jobs:
            logger.warning(
                'There is unfinished job with description: %s', job.description
            )
    else:
        logger.info("There is no unfinished job")
    return active_jobs


def clean_unfinished_jobs_on_engine():
    """
    Check if there is some unfinished (STARTED) jobs on engine, and if there is
    some, it changes its status to FINISHED

    __author__ = "pbalogh"
    :return: None
    """
    if ll_jobs.get_active_jobs():
        logger.warning("Set STATUS of unfinished jobs to FINISHED")
        config.ENGINE.db.psql(
            "UPDATE job SET status = 'FINISHED' WHERE status = 'STARTED'"
        )


def generate_object_names(
    num_of_cases, num_of_objects=config.NUM_OF_OBJECT, prefix=config.PREFIX
):
    """
    Generate object names per case

    :param num_of_cases: Number of cases
    :type num_of_cases: int
    :param num_of_objects: Number of object_type for each case
    :type num_of_objects: int
    :param prefix: object_type (QoS for example)
    :type prefix: str
    :return: {case_num:[case1_QoS1, ...]}
    :rtype: dict
    """
    cases = range(1, num_of_cases + 1)
    return dict(
        [
            (
                c, [
                    "C%s_%s%d" % (
                        c, prefix, (i + 1)) for i in range(num_of_objects)
                    ]
            ) for c in cases
        ]
    )


def get_host_resource_of_running_vm(vm):
    """
    Get host resource of given VM

    :param vm: VM name
    :type vm: str
    :return: Host resource
    :rtype: resources.Host
    """
    logger.info("Get %s host resource", vm)
    host_ip = ll_hosts.get_host_ip_from_engine(
        host=ll_vms.get_vm_host(vm_name=vm)
    )
    return get_host_resource(
        ip=host_ip, password=config.HOSTS_PW
    )


def get_host_resource(ip, password, username=None):
    """
    Return remote resource with given username/password on given ip

    :param ip: host ip
    :type: ip: str
    :param username: host username, if None using root user
    :type username: str
    :param password: user's password
    :type: password: str
    :return: Host with root user
    :rtype: Host
    """
    host = Host(ip)
    _user = username if username else config.VDC_ROOT_USER
    host.users.append(User(_user, password))
    return host


def get_host_executor(ip, password, username=None, use_pkey=False):
    """

    :param ip: Host ip
    :type: ip: str
    :param password: User's password
    :type: password: str
    :param username:  Host username, if None using root user
    :type username: str
    :param use_pkey: Use ssh private key to connect without password
    :type use_pkey: bool
    :return: RemoteExecutor with given username
    :rtype: RemoteExecutor
    """

    _user = username if username else config.VDC_ROOT_USER
    user = User(_user, password)
    return get_host_resource(
        ip, username, password
    ).executor(user, pkey=use_pkey)


def wait_for_jobs_deco(jobs):
    """
    Decorator used to ensure that following a test execution, a list of
    specified jobs will be waited on

    Sample usage:
    @wait_for_jobs_deco([ENUMS['job_move_or_copy_disk']])
    def test_x(self):

    :param jobs: List of jobs to wait for
    :type jobs: list
    """
    def deco(f):
        @functools.wraps(f)
        def run(*args, **kwargs):
            try:
                result = f(*args, **kwargs)
            finally:
                ll_jobs.wait_for_jobs(jobs)
            return result
        return run
    return deco


def get_vm_resource(vm, start_vm=True):
    """
    Get VM resource

    Args:
        vm (str): VM name
        start_vm (bool): Start VM before fetch IP

    Returns:
        Host: VM resource
    """
    ip = hl_vms.get_vm_ip(vm_name=vm, start_vm=start_vm)
    return get_host_resource(ip, config.VMS_LINUX_PW)


def cleanup_file_resources(storage_types=(GULSTERFS, NFS)):
    """
    Clean all unused file resources
    """
    logger.info("Cleaning File based storage resources: %s", storage_types)
    for storage_type in storage_types:
        if storage_type == NFS:
            for address, path in zip(
                    config.UNUSED_DATA_DOMAIN_ADDRESSES,
                    config.UNUSED_DATA_DOMAIN_PATHS
            ):
                storage.clean_mount_point(
                    config.HOSTS[0], address, path, opts=NFS_MNT_OPTS
                )
        elif storage_type == GULSTERFS:
            for address, path in zip(
                    config.UNUSED_GLUSTER_DATA_DOMAIN_ADDRESSES,
                    config.UNUSED_GLUSTER_DATA_DOMAIN_PATHS
            ):
                storage.clean_mount_point(
                    config.HOSTS[0], address, path, opts=GLUSTER_MNT_OPTS
                )


def storage_cleanup():
    """
    Clean up all storage domains which are not in GE yaml and direct LUNs
    """
    direct_luns = [disk for disk in ll_disks.get_all_disks() if (
        disk.storage_type == config.DISK_TYPE_LUN
    )]
    for direct_lun in direct_luns:
        logger.error(
            "DIRECT LUN DISK LEFTOVER FOUND: NAME: %s ,ID: %s",
            direct_lun.get_alias(), direct_lun.get_id()
        )
        if not ll_disks.deleteDisk(True, disk_id=direct_lun.get_id()):
            logger.error("Failed to delete direct lun with ID: %s", direct_lun)

    logger.info("Retrieve all Storage domains")
    engine_sds_objs = ll_sd.get_storage_domains()
    logger.info(
        "The storage domains names in engine: %s",
        [sd_obj.get_name() for sd_obj in engine_sds_objs]
    )
    logger.info("The GE storage domains names: %s", config.SD_LIST)
    for dc in config.dcs:
        dc_name = dc['name']
        spm = None
        wait_for_tasks(config.VDC_HOST, config.VDC_ROOT_PASSWORD, dc_name)
        for sd_obj in engine_sds_objs:
            sd_name = sd_obj.get_name()
            if sd_name not in config.SD_LIST:
                spm = spm if spm else ll_hosts.getSPMHost(config.HOSTS)
                logger.error(
                    "SD LEFTOVER FOUND: NAME: %s, ID: %s, TYPE: %s",
                    sd_name, sd_obj.id, sd_obj.storage.get_type()
                )
                hl_sd.destroy_storage_domain(sd_name, dc_name, host_name=spm)
    cleanup_file_resources(config.opts['storages'])


def determine_best_cpu_model(hosts, comp_version=None):
    """
    Returns the best cpu family for given hosts

    :param hosts: list of hosts
    :type hosts: list of resources.Host instances
    :param comp_version: compatibility version
    :type comp_version: str

    :returns: cpu family name
    :rtype: str (None in case of failure)
    """
    cpu_den = cpumodel.CpuModelDenominator()
    try:
        return cpu_den.get_common_cpu_model(
            hosts, version=comp_version,
        )
    except cpumodel.CpuModelError as ex:
        logger.error("Can not determine the best cpu_model: %s", ex)


def get_pm_details(host_name):
    """
    Get the power management details for specific host

    :param host_name: host fqdn to retrieve its details
    :type host_name: str
    :return: dictionary of host details.
             for example:
             {
                'cheetah01.scl.lab.tlv.redhat.com': {
                   'pm_password': u'calvin',
                   'pm_address': u'cheetah01-mgmt.scl.lab.tlv.redhat.com',
                   'pm_username': u'root',
                   'pm_type': u'ipmilan'
                }
             }
    :rtype: dict
    """
    foreman_api = ForemanActions(
        config.FOREMAN_URL, config.FOREMAN_USER, config.FOREMAN_PASSWD
    )
    pm_host_details = foreman_api.get_host_pm_details(host_name)
    logger.debug("Power Management Details: %s", pm_host_details)
    return pm_host_details


def wait_for_vm_gets_to_full_consumption(vm_name, expected_load):
    """
    Wait until VM gets to full CPU consumption
    Check that the value is as expected 3 times,
    In order to be sure the CPU value is stable.

    :param vm_name: vm name
    :type vm_name: str
    :param expected_load: value of expected CPU load
    :type expected_load: int
    :return: True if VM gets to the expected CPU load, False otherwise
    :rtype: bool
    """
    count = 0
    sampler = apis_utils.TimeoutingSampler(
        300, 10, hl_vms.get_vm_cpu_consumption_on_the_host, vm_name
    )
    for sample in sampler:
        try:
            if expected_load - 1 <= sample <= expected_load + 1:
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
                "Timeout When Trying to get VM %s CPU consumption", vm_name
            )
    return False


def wait_for_vms_gets_to_full_consumption(expected_dict):
    """
    Wait until VMs gets to full CPU consumption


    :param expected_dict: keys- VM name, Values- expected CPU load
    :type expected_dict: dict
    :return:True if all VMs gets to the expected CPU load, False otherwise
    :rtype: bool
    """
    results = list()
    with ThreadPoolExecutor(max_workers=2) as e:
        for vm_name, expected_load in expected_dict.iteritems():
            logger.info("checking consumption on VM %s", vm_name)
            results.append(
                e.submit(
                    wait_for_vm_gets_to_full_consumption,
                    vm_name, expected_load
                )
            )

    for vm_name, result in zip(expected_dict.keys(), results):
        if result.exception():
            logger.error(
                "Got exception while checking VM %s consumption: %s",
                vm_name, result.exception()
            )
            raise result.exception()
        if not result.result():
            raise errors.VMException("Cannot get vm %s consumption" % vm_name)
    return True


def get_host_resource_by_name(host_name):
    """
    Get host resource by name

    Args:
        host_name (str): host name

    Returns:
        VDS: host resource
    """
    host_ip = ll_hosts.get_host_ip_from_engine(host_name)
    for host_resource in config.VDS_HOSTS:
        if host_resource.ip == host_ip:
            return host_resource
    return None


def wait_for_vm_gets_to_full_memory(vm_name, expected_memory):
    """
    Wait until VM gets to full Memory allocation,
    Check that the value is as expected 3 times,
    In order to be sure the Memory value is stable.

    Args:
        vm_name (str): vm_name
        expected_memory(int): value of expected Memory allocation
    Returns:
      bool: True if VM gets to the expected Memory allocation, False otherwise
    """
    count = 0
    vm_resource = get_vm_resource(vm_name)
    expected_mem = expected_memory / 1024
    sampler = apis_utils.TimeoutingSampler(
        60, 5, hl_vms.get_memory_on_vm, vm_resource
    )
    for sample in sampler:
        try:
            if expected_mem * 0.90 <= sample <= expected_mem:
                logging.info(
                    "Try #: %d Memory is as expected: %d ",
                    count, expected_mem
                )
                count += 1
                if count == 3:
                    logging.info(
                        "Current Memory is as expected: %d" % expected_mem
                    )
                    return True
            else:
                logging.warning(
                    "Memory allocation of %s:  is %d, waiting for "
                    "usage will be %d, 3 times",
                    vm_name, sample, expected_mem
                )
        except apis_exceptions.APITimeout:
            logging.error(
                "Timeout When Trying to get VM %s CPU consumption", vm_name
            )
    return False
