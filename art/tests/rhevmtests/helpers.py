"""
Rhevmtests helper functions
"""
import art.rhevm_api.tests_lib.low_level.templates as ll_templates
from art.rhevm_api.resources import ssh
from rhevmtests.storage import config


def get_golden_template_name(cluster=config.CLUSTER_NAME):
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
