#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
rhevmtests helper functions
"""
import functools
import logging
import os

from _pytest.mark import ParameterSet

import art.core_api.apis_exceptions as apis_exceptions
import art.rhevm_api.tests_lib.high_level.vms as hl_vms
import config
from storageapi.storageErrors import GetLUNInfoError
from storageapi.storageManagerWrapper import StorageManagerWrapper
from art.core_api import apis_utils
from rrmngmnt.power_manager import SSHPowerManager

from art.rhevm_api.resources import User, Host, storage
from art.rhevm_api.tests_lib.high_level import (
    storagedomains as hl_sd,
    hosts as hl_hosts
)
from art.rhevm_api.tests_lib.low_level import (
    disks as ll_disks,
    vms as ll_vms,
    jobs as ll_jobs,
    hosts as ll_hosts,
    templates as ll_templates,
    storagedomains as ll_sd,
    general as ll_general
)
from art.rhevm_api.utils import cpumodel
from art.rhevm_api.utils.test_utils import wait_for_tasks
from rrmngmnt import ssh
from utilities.foremanApi import ForemanActions


NFS = config.STORAGE_TYPE_NFS
GLUSTERFS = config.STORAGE_TYPE_GLUSTER
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


@ll_general.generate_logs()
def set_passwordless_ssh(src_host, dst_host, dst_host_ips=None):
    """
    Set passwordless SSH to remote host

    Args:
        src_host (Host): Source host resource object
        dst_host (Host): Destination host resource object
        dst_host_ips (list): List of additional destination host IPs

    Returns:
        bool: True/False
    """
    ssh_keyscan = ["ssh-keyscan", "-t", "rsa"]
    known_hosts = ssh.KNOWN_HOSTS % os.path.expanduser(
        "~%s" % src_host.root_user.name
    )
    authorized_keys = ssh.AUTHORIZED_KEYS % os.path.expanduser(
        "~%s" % dst_host.root_user.name
    )

    # Check for KNOWN_HOSTS and AUTHORIZED_KEYS files existence
    known_exists = src_host.fs.exists(known_hosts)
    auth_exists = src_host.fs.exists(authorized_keys)

    # Remove old keys from local KNOWN_HOSTS file
    if known_exists and not src_host.remove_remote_host_ssh_key(dst_host):
        return False

    # Remove local key from remote host AUTHORIZED_KEYS file
    if auth_exists and not dst_host.remove_remote_key_from_authorized_keys():
        return False

    # Get local SSH key and add it to remote host AUTHORIZED_KEYS file
    local_key = src_host.get_ssh_public_key().strip()

    remote_cmd = ["echo", local_key, ">>", authorized_keys]
    rc = dst_host.run_command(remote_cmd)[0]
    if rc:
        return False

    # Add remote host SSH key to source host KNOWN_HOSTS file using ssh-keyscan
    # When adding destination host as FQDN, ignore the results from ssh-keyscan
    # to avoid failing of DNS resolution issues, which could occur in the labs
    hosts_to_add = [(dst_host.ip, True), (dst_host.fqdn, False)]
    hosts_to_add = hosts_to_add + [(ip, True) for ip in dst_host_ips]

    for i, check_error in hosts_to_add:
        rc1, remote_key = src_host.run_command(ssh_keyscan + [i])[:2]
        local_cmd = ["echo", remote_key, ">>", known_hosts]
        rc2 = src_host.run_command(local_cmd)[0]
        if check_error and (rc1 or rc2):
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
    num_of_cases, num_of_objects=5, prefix='net'
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
        ip, password, username
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


def cleanup_file_resources(storage_types=(GLUSTERFS, NFS)):
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
        elif storage_type == GLUSTERFS:
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
    storage_types = set()
    for dc in config.DC_NAME:
        spm = None
        wait_for_tasks(config.ENGINE, dc)
        for sd_obj in engine_sds_objs:
            sd_name = sd_obj.get_name()
            if sd_name not in config.SD_LIST:
                spm = spm if spm else ll_hosts.get_spm_host(config.HOSTS)
                logger.error(
                    "SD LEFTOVER FOUND: NAME: %s, ID: %s, TYPE: %s",
                    sd_name, sd_obj.id, sd_obj.storage.get_type()
                )
                hl_sd.destroy_storage_domain(
                    sd_name, dc, host_name=spm, engine=config.ENGINE
                )
                sd_type = sd_obj.storage.get_type()
                if sd_type in (NFS, GLUSTERFS):
                    storage_types.add(sd_type)
    if storage_types:
        cleanup_file_resources(storage_types)


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


@ll_general.generate_logs()
def get_host_resource_by_name(host_name):
    """
    Get host resource by host_name

    Args:
        host_name (str): host name

    Returns:
        VDS: host resource, or None if not found
    """
    return (
        config.VDS_HOSTS[config.HOSTS.index(host_name)]
        if host_name in config.HOSTS else None
    )


@ll_general.generate_logs()
def get_host_name_by_resource(host_resource):
    """
    Get host name by host_resource

    Args:
        host_resource (Host): Host resource

    Returns:
        str: Host name
    """
    return (
        config.HOSTS[config.VDS_HOSTS.index(host_resource)]
        if host_resource in config.VDS_HOSTS else None
    )


def wait_for_vm_gets_to_full_memory(
    vm_name,
    expected_memory,
    threshold=0.9,
    user_name=None,
    password=config.VMS_LINUX_PW
):
    """
    Wait until VM gets to full Memory allocation,
    Check that the value is as expected 3 times,
    In order to be sure the Memory value is stable.

    Args:
        vm_name (str): vm_name
        expected_memory(int): value of expected Memory allocation
        threshold (float): lower bound to memory on VM
        user_name (str): User name to login VM (None will login with root)
        password (str): Password to login VM

    Returns:
      bool: True if VM gets to the expected Memory allocation, False otherwise
    """
    count = 0
    vm_resource = get_host_executor(
        ip=hl_vms.get_vm_ip(vm_name), username=user_name, password=password
    )
    expected_mem = expected_memory / 1024
    sampler = apis_utils.TimeoutingSampler(
        60, 5, hl_vms.get_memory_on_vm, vm_resource
    )
    for sample in sampler:
        try:
            if expected_mem * threshold <= sample <= expected_mem:
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


def raise_if_false_in_list(results):
    """
    For finalizers, When we have fixture with more then one finalizer if one
    of the finalizer fail the next one will not execute.
    This function will raise if one element in the list is False

    Args:
        results (list): Results list

    Raises:
        AssertionError: If one element in the list is False

    Examples:
        results = list()

        def fin3():
            raise_if_false_in_list(results=results)
        request.addfinalizer(fin3)

        def fin2():
            results.append((some_function(), "ERROR for raise"))
        request.addfinalizer(fin2)

        def fin1():
            results.append((some_function(), "ERROR for raise"))
        request.addfinalizer(fin1)
    """
    res = [r[1] for r in results if not r[0]]
    assert not res, res


def get_gb(gb):
    """
    Return byte int value according to requested GB

    Args:
        gb (int): GB value

    Returns:
        int: byte value
    """

    return 1024 ** 3 * gb


def search_object(util, query, identity='name'):
    """
    Perform a search query and filter by identity key

    Args:
        util (object): getApi object, Example: VM_API
        query (str): Query sting
        identity (str): Identity key: name/id

    Returns:
        list: list of objects names

    """

    objects = util.query(query, all_content=True)
    return [
        getattr(obj, identity) for obj in objects if hasattr(obj, identity)
        ]


def get_storage_manager(storage_type, storage_server, storage_config):
    """
    Given the storage type manager and config, returns the storage manager
    instance

    Args:
        storage_type (str): The type of the storage
        storage_server (str): The storage server manager address
        storage_config (str): The configuration file of the storage managers

    Returns:
        StorageManager: Instance of StorageManager from storage_api
    """
    return StorageManagerWrapper(
        storage_server, storage_type, storage_config
    ).manager


def get_lun_id(storage_domain, storage_manager, storage_server):
    """
    Connect to storage manager using StorageManager instance and fetch the
    storage domain LUN ID

    Args:
        storage_domain (str): The name of the storage domain
        storage_manager (StorageManager): The storage manager instance
        storage_server (str): The storage server address

    Returns:
        str: The LUN ID as written in the storage server manager
    """
    lun_id = ""
    if storage_server == config.STORAGE_SERVER_XTREMIO:
        sd_lun_ids = ll_sd.get_storage_domain_luns_ids(storage_domain)
        lun_id = storage_manager.get_lun_id(sd_lun_ids[0])
    elif storage_server == config.STORAGE_SERVER_NETAPP:
        sd_lun_serials = ll_sd.get_storage_domain_luns_serials(storage_domain)
        lun_id = storage_manager.get_lun_id(
            sd_lun_serials[0].split('Mode_')[-1]
        )
    return lun_id


def get_lun_actual_size(storage_manager, lun_id):
    """
    Connects to storage server using storage_api manager instance and fetches
    the LUN actual used size for the given LUN id

    Args:
        lun_id (str): The ID of the LUN as written in the storage server
        storage_manager (StorageManager): Instance of StorageManager from
            storage_api repository

    Returns:
        float or None: The actual used space of the given LUN, in GB
    """
    try:
        lun_info = storage_manager.getLun(lun_id)
    except GetLUNInfoError:
        logger.error("Failed to get info of lun %s", lun_id)
        return None
    logger.info("Used space of lun: %s is: %s", lun_id, lun_info['used_size'])
    return float(lun_info['used_size'].replace('G', '').replace('B', ''))


def get_test_parametrize_ids(item, params):
    """
    Get test parametrize IDs from the current parametrize run

    Args:
        item (instance): pytest mark object (<func_name>.parametrize)
        params (list): Test parametrize params

    Returns:
        str: Test Id

    Examples:
        _id = get_test_parametrize_ids(
            self.test_create_networks.parametrize,
            ["param_1", "param_2"]
        )
        testflow.step(_id)
    """
    _id = ""
    param = [i for i in item if i.name == "parametrize"]
    param = param[0] if param else None
    if not param:
        return _id

    param_args = param.args
    if not param_args or len(param_args) < 2:
        return _id

    param_args_values = param_args[1]
    param_ids = param.kwargs.get("ids")
    for i in param_args:
        if isinstance(i, list) or isinstance(i, tuple):
            for x in i:
                if not isinstance(x, ParameterSet):
                    continue

                x_values = x.values
                if tuple(params) == x_values:
                    return param_ids[param_args_values.index(x)]
    return _id


def maintenance_and_activate_hosts(hosts=config.HOSTS, activate=True):
    """
    Put hosts in maintenance and activate them. Used mainly in order to refresh
    the iSCSI sessions or issue SCSI bus rescan for FC after LUNs list
    modification (i.e, new LUN creation or deletion (LUNs deletion for FC
    requires hosts reboot)).
    Suitable for hosted engine environments.

    Args:
        hosts (list): List of host names
        activate (bool): True for activating the hosts back, False otherwise

    Raises:
        AssertionError: In case of any failure
        APITimeout: Timeout exceeded waiting for all data center's tasks to
            complete
    """
    for host in hosts:
        host_resource = get_host_resource_by_name(host)
        wait_for_tasks(
            config.ENGINE, config.DATA_CENTER_NAME
        )
        assert hl_hosts.deactivate_host_if_up(host, host_resource), (
            "Failed to deactivate host %s" % host
        )
        if activate:
            assert hl_hosts.activate_host_if_not_up(host, host_resource), (
                "Failed to activate host %s" % host
            )
            assert ll_hosts.wait_for_hosts_states(True, host), (
                "Host %s Failed to reach state up" % host
            )
    if activate:
        assert ll_hosts.wait_for_spm(
            config.DATA_CENTER_NAME, config.WAIT_FOR_SPM_TIMEOUT,
            config.WAIT_FOR_SPM_INTERVAL
        ), "SPM was not elected on data-center %s" % config.DATA_CENTER_NAME


def reboot_hosts(hosts_resources):
    """
    Reboot given hosts.
    Necessary for LUNs list update after LUNs removal while using FC.

    Args:
        hosts_resources (list): List of host resources

    Raises:
        AssertionError: In case of any failure
        APITimeout: Timeout exceeded waiting for all data center's tasks to
            complete
    """
    hosts_pwr_mgmnt = [SSHPowerManager(host) for host in hosts_resources]
    hosts_names = [
        ll_hosts.get_host_name_from_engine(host) for host in hosts_resources
    ]

    for resource, host in zip(hosts_resources, hosts_names):
        wait_for_tasks(config.ENGINE, config.DATA_CENTER_NAME)
        assert hl_hosts.deactivate_host_if_up(host, resource), (
            "Failed to deactivate host %s" % host
        )

    for pwr_mgmt, host in zip(hosts_pwr_mgmnt, hosts_names):
        logger.info("Rebooting Host %s", host)
        pwr_mgmt.restart()

    logger.info("Activating hosts %s", hosts_names)
    for host in hosts_names:
        assert ll_hosts.activate_host(positive=True, host=host, wait=True), (
            "Failed to activate host %s" % host
        )

    assert ll_hosts.wait_for_spm(
        config.DATA_CENTER_NAME, config.WAIT_FOR_SPM_TIMEOUT,
        config.WAIT_FOR_SPM_INTERVAL
    ), "SPM was not elected on data-center %s" % config.DATA_CENTER_NAME


def config_iptables_connection(
    source, dest, protocol='all', ports=None, block=True
):
    """
    Blocks or unblocks outgoing connection to an address

    Args:
        source (str): ip or fqdn of the source machine
        dest (dict): ip or fqdn of host or hosts to which to prevent traffic
        protocol (str): affected network protocol, Default is 'all'
        ports (list): outgoing ports we want to block, default is None
        block (bool): True for blocking outgoing connections, False for
            unblocking

    Returns:
        bool: True if commands successed, False otherwise

    """
    # TODO: Add Firewall object and config_firewall function after Firewall
    # module is merged into rrmngmnt


def ignore_exception(func):
    """
    Decorator to catch exception

    Args:
        func (Function): Function to process

    Returns:
        Function: The function
    """
    def inner(**kwargs):
        """
        The call for the function

        Args:
            kwargs (dict): Function kwargs
        """
        try:
            return func(**kwargs)
        except Exception as e:
            logger.error("IGNORED EXCEPTION: %s", e)
    return inner
