import logging

import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import art.rhevm_api.tests_lib.low_level.templates as ll_templates
import art.rhevm_api.tests_lib.low_level.hosts as ll_hosts

LOGGER = logging.getLogger("art.hl_lib.cls")


def remove_templates_connected_cluster(cluster_name):
    """
    Description: filter templates connected to cluster and remove them
    :param cluster: cluster name
    :type cluster: str
    """
    templates_in_cluster = ll_templates.get_template_from_cluster(cluster_name)
    for template in templates_in_cluster:
        if not ll_templates.removeTemplate(True, template):
            LOGGER.error("Remove template:%s failed", template)


def remove_vms_and_templates_from_cluster(cluster_name):
    """
    Description: filter vms and templates connected to cluster
    :param cluster: cluster name
    :type cluster: str
    """
    LOGGER.info('Remove VMs connected to cluster: %s', cluster_name)
    ll_vms.remove_all_vms_from_cluster(cluster_name)

    LOGGER.info('Remove Templates from cluster: %s', cluster_name)
    remove_templates_connected_cluster(cluster_name)


def get_hosts_connected_to_cluster(cluster_id):
    """
    Description: get list of hosts connected to cluster
    :param cluster: cluster id
    :type cluster: uuid str
    :returns: list of hosts
    :rtype: list
    """
    all_hosts = ll_hosts.HOST_API.get(absLink=False)
    return filter(
        lambda x: x.get_cluster().get_id() == cluster_id,
        all_hosts
    )
