import logging

import art.rhevm_api.tests_lib.low_level.templates as ll_templates
import art.rhevm_api.tests_lib.low_level.hosts as ll_hosts
import art.rhevm_api.tests_lib.low_level.clusters as ll_clusters

logger = logging.getLogger("art.hl_lib.cls")


def remove_templates_connected_cluster(cluster_name):
    """
    Description: filter templates connected to cluster and remove them
    :param cluster: cluster name
    :type cluster: str
    """
    templates_in_cluster = ll_templates.get_template_from_cluster(cluster_name)
    for template in templates_in_cluster:
        logger.info(
            'Remove Template: %s from cluster: %s', template, cluster_name
        )
        if not ll_templates.remove_template(True, template):
            logger.error("Remove template:%s failed", template)


def get_hosts_connected_to_cluster(cluster_id):
    """
    Description: get list of hosts connected to cluster
    :param cluster: cluster id
    :type cluster: uuid str
    :returns: list of hosts
    :rtype: list
    """
    all_hosts = ll_hosts.HOST_API.get(abs_link=False)
    return filter(
        lambda x: x.get_cluster().get_id() == cluster_id,
        all_hosts
    )


def get_external_network_provider_names(cluster_name):
    """
    Get external network providers names

    Args:
        cluster_name (str): By cluster name

    Returns:
        list: List of external network provider names
    """
    cluster_obj = ll_clusters.get_cluster_object(cluster_name=cluster_name)
    enp_objs = ll_clusters.get_external_network_providers_objects(
        cluster_object=cluster_obj
    )
    return [enp.get_name() for enp in enp_objs]
