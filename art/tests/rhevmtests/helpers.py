#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
rhevmtests helper functions
"""

import logging
from rhevmtests import config
import art.rhevm_api.resources
from art.rhevm_api.resources import ssh
import art.rhevm_api.resources.user as users
import art.rhevm_api.tests_lib.low_level.jobs as ll_jobs
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
    src_host_exec = src_host.executor()
    dst_host_exec = dst_host.executor()

    # Remove old keys from local KNOWN_HOSTS file
    if not src_host.remove_remote_host_ssh_key(dst_host):
        return False

    # Remove local key from remote host AUTHORIZED_KEYS file
    if not dst_host.remove_remote_key_from_authorized_keys():
        return False

    # Get local SSH key and add it to remote host AUTHORIZED_KEYS file
    local_key = src_host.get_ssh_public_key().strip()
    remote_cmd = ["echo", local_key, ">>", ssh.AUTHORIZED_KEYS]
    rc = dst_host_exec.run_cmd(remote_cmd)[0]
    if rc:
        return False

    # Adding remote host SSH key to local KNOWN_HOSTS file
    for i in [dst_host.ip, dst_host.fqdn]:
        rc1, remote_key = src_host_exec.run_cmd(ssh_keyscan + [i])[:2]
        local_cmd = ["echo", remote_key, ">>", ssh.KNOWN_HOSTS]
        rc2 = src_host_exec.run_cmd(local_cmd)[0]
        if rc1 or rc2:
            return False
    return True


def get_host_resource_with_root_user(ip, root_password):
    """
    Return remote resource with user root on give ip

    :param ip: host ip
    :type: ip: str
    :param root_password: root password
    :type: root_password: str
    :return: Host with root user
    :rtype: Host
    """
    host = art.rhevm_api.resources.Host(ip)
    host.users.append(users.RootUser(root_password))
    return host


def get_host_executor_with_root_user(ip, root_password):
    """
    Return remote executor with user root on give ip

    :param ip: host ip
    :type: ip: str
    :param root_password: root password
    :type: root_password: str
    :return: RemoteExecutor with root user
    :rtype: RemoteExecutor
    """
    return get_host_resource_with_root_user(ip, root_password).executor()


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


def generate_object_names(object_type, count):
    """
    Generate list on names by given object type

    :param object_type: object_type (QoS for example)
    :object_type type: str
    :param count: Number of names to generate
    :object_type count: int
    :return: List of names
    :rtype: list
    """
    return ["%s_%s" % (object_type, i) for i in range(count)]
