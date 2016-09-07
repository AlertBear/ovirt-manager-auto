"""
Quota test helpers
"""
import logging

import art.rhevm_api.tests_lib.low_level.datacenters as ll_datacenters
import config as conf

logger = logging.getLogger(__name__)


def create_quota_limits(
    dc_name, quota_name, quota_cluster_limit=None, quota_storage_limit=None
):
    """
    Create quota limits on the quota

    Args:
        dc_name (str): Datacenter name
        quota_name (str):  Quota name
        quota_cluster_limit (dict): Quota cluster limits
        quota_storage_limit (dict): Quota storage limits

    Returns:
        bool: True, if succeeds to create quota limits, otherwise False
    """
    if quota_cluster_limit:
        logger.info(
            "Create cluster limitation %s under quota %s",
            quota_cluster_limit, quota_name
        )
        if not ll_datacenters.create_quota_limits(
            dc_name=dc_name,
            quota_name=quota_name,
            limit_type=conf.LIMIT_TYPE_CLUSTER,
            limits_d=quota_cluster_limit
        ):
            logger.error(
                "Failed to create cluster limitation under quota %s",
                quota_name
            )
            return False

    if quota_storage_limit:
        logger.info(
            "Create storage limitation %s under quota %s",
            quota_storage_limit, quota_name
        )
        if not ll_datacenters.create_quota_limits(
            dc_name=dc_name,
            quota_name=quota_name,
            limit_type=conf.LIMIT_TYPE_STORAGE,
            limits_d=quota_storage_limit
        ):
            logger.error(
                "Failed to create storage limitation under quota %s",
                quota_name
            )
            return False

    return True
