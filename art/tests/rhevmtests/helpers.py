"""
Rhevmtests helper functions
"""
from art.rhevm_api.tests_lib.low_level.templates import (
    get_template_from_cluster,
)
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
    templates = get_template_from_cluster(cluster)
    for template in config.TEMPLATE_NAME:
        if template in templates:
            return template
    return None
