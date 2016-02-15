#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
rhevmtests helper functions
"""
import functools
import logging
import os

from rrmngmnt import ssh
from rhevmtests import config
from art.rhevm_api.resources import User, Host
from art.test_handler import exceptions
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import art.rhevm_api.tests_lib.low_level.jobs as ll_jobs
import art.rhevm_api.tests_lib.low_level.hosts as ll_hosts
import art.rhevm_api.tests_lib.low_level.templates as ll_templates

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
    ssh_keyscan = ["ssh-keyscan", "-t", "rsa"]
    known_hosts = ssh.KNOWN_HOSTS % os.path.expanduser(
        "~%s" % src_host.root_user.name
    )
    authorized_keys = ssh.AUTHORIZED_KEYS % os.path.expanduser(
        "~%s" % dst_host.root_user.name
    )

    # Remove old keys from local KNOWN_HOSTS file
    if not src_host.remove_remote_host_ssh_key(dst_host):
        return False

    # Remove local key from remote host AUTHORIZED_KEYS file
    if not dst_host.remove_remote_key_from_authorized_keys():
        return False

    # Get local SSH key and add it to remote host AUTHORIZED_KEYS file
    local_key = src_host.get_ssh_public_key().strip()

    remote_cmd = ["echo", local_key, ">>", authorized_keys]
    rc = dst_host.run_command(remote_cmd)[0]
    if rc:
        return False

    # Adding remote host SSH key to local KNOWN_HOSTS file
    for i in [dst_host.ip, dst_host.fqdn]:
        rc1, remote_key = src_host.run_command(ssh_keyscan + [i])[:2]
        local_cmd = ["echo", remote_key, ">>", known_hosts]
        rc2 = src_host.run_command(local_cmd)[0]
        if rc1 or rc2:
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
                    "case%s_%s%d" % (
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


def get_vm_resource(vm):
    """
    Get VM executor

    :param vm: VM name
    :type vm: str
    :return: VM executor
    :rtype: resource_vds
    """
    logger.info("Get IP for: %s", vm)
    rc, ip = ll_vms.waitForIP(vm=vm, timeout=config.VM_IP_TIMEOUT)
    if not rc:
        raise exceptions.CanNotFindIP("Failed to get IP for: %s" % vm)
    ip = ip["ip"]
    return get_host_resource(ip, config.VMS_LINUX_PW)
