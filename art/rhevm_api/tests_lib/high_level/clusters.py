import logging

from art.rhevm_api.tests_lib.low_level import (
    templates as ll_templates,
    hosts as ll_hosts,
    clusters as ll_clusters,
    general as ll_general
)

logger = logging.getLogger("art.hl_lib.cls")


@ll_general.generate_logs(step=True, error=False, warn=True)
def remove_templates_connected_cluster(cluster):
    """
    Remove templates that are connected to cluster

    Args:
        cluster (str): cluster name
    """
    templates_in_cluster = ll_templates.get_template_from_cluster(cluster)
    for template in templates_in_cluster:
        logger.info(
            'Remove Template: %s from cluster: %s', template, cluster
        )
        if not ll_templates.remove_template(True, template):
            logger.error("Remove template:%s failed", template)


@ll_general.generate_logs(step=True, error=False, warn=True)
def get_hosts_connected_to_cluster(cluster_id):
    """
    Get list of hosts connected to cluster

    Args:
        cluster_id (str): cluster id

    Returns:
        list: All hosts connected to the cluster
    """
    all_hosts = ll_hosts.HOST_API.get(abs_link=False)
    return filter(
        lambda x: x.get_cluster().get_id() == cluster_id,
        all_hosts
    )


@ll_general.generate_logs(step=True, error=False, warn=True)
def get_external_network_provider_names(cluster):
    """
    Get cluster external network providers names

    Args:
        cluster (str): By cluster name

    Returns:
        list: List of external network provider names
    """
    cluster_obj = ll_clusters.get_cluster_object(cluster_name=cluster)
    enp_objs = ll_clusters.get_external_network_providers_objects(
        cluster_object=cluster_obj
    )
    return [enp.get_name() for enp in enp_objs]
