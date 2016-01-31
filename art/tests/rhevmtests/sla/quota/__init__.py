"""
Quota Test - test initialization
"""
import logging
import config as conf
import art.test_handler.exceptions as errors
import art.rhevm_api.tests_lib.low_level.datacenters as ll_dc

logger = logging.getLogger(__name__)


def setup_package():
    """
    1) Clean all events
    2) Create datacenter quota
    """
    logger.info("Remove all events from engine")
    sql = "DELETE FROM audit_log"
    conf.ENGINE.db.psql(sql)
    if not ll_dc.create_dc_quota(
        dc_name=conf.DC_NAME_0, quota_name=conf.QUOTA_NAME
    ):
        raise errors.DataCenterException()


def teardown_package():
    """
    1) Set datacenter quota mode to none
    2) Delete datacenter quota
    """
    logger.info(
        "Update datacenter %s quota mode to %s",
        conf.DC_NAME_0, conf.QUOTA_MODES[conf.QUOTA_NONE_MODE]
    )
    if not ll_dc.updateDataCenter(
        positive=True,
        datacenter=conf.DC_NAME_0,
        quota_mode=conf.QUOTA_MODES[conf.QUOTA_NONE_MODE]
    ):
        logger.error(
            "Failed to update datacenter %s quota mode", conf.DC_NAME_0
        )
    ll_dc.delete_dc_quota(
        dc_name=conf.DC_NAME_0, quota_name=conf.QUOTA_NAME
    )
