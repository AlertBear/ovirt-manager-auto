"""
Quota Test - test initialization
"""

import os
import logging
from rhevmtests.sla.quota import config as c
import art.test_handler.exceptions as errors
import art.rhevm_api.tests_lib.low_level.datacenters as ll_datacenters
import art.rhevm_api.tests_lib.high_level.datacenters as hl_datacenters

LOGGER = logging.getLogger(__name__)


def setup_package():
    """
    Create basic resources required by all tests.
    Create the main datacenter and cluster, installs a host and starts it,
    creates and activates main storage.
    """
    if os.environ.get("JENKINS_URL") and not c.GOLDEN_ENV:
        LOGGER.info("Building setup...")
        hl_datacenters.build_setup(
            c.PARAMETERS, c.PARAMETERS,
            c.STORAGE_TYPE, c.TEST_NAME
        )
    logging.info("Remove all events from engine")
    sql = "DELETE FROM audit_log"
    c.ENGINE.db.psql(sql)
    logging.info(
        "Create quota %s under datacenter %s", c.QUOTA_NAME, c.DC_NAME_0
    )
    if not ll_datacenters.create_dc_quota(
        dc_name=c.DC_NAME_0, quota_name=c.QUOTA_NAME
    ):
        raise errors.DataCenterException(
            "Failed to create quota %s under datacenter %s" %
            (c.QUOTA_NAME, c.DC_NAME_0)
        )


def teardown_package():
    """
    Package-level teardown run only once at end of all tests.
    Detaches main storage, removes it, deactivates host, removes host,
    removes main cluster and main dc.
    """
    logging.info(
        "Delete quota %s from datacenter %s", c.QUOTA_NAME, c.DC_NAME_0
    )
    if not ll_datacenters.delete_dc_quota(
        dc_name=c.DC_NAME_0, quota_name=c.QUOTA_NAME
    ):
        logging.error(
            "Failed to delete quota %s from datacenter %s",
            c.QUOTA_NAME, c.DC_NAME_0
        )
    if os.environ.get("JENKINS_URL") and not c.GOLDEN_ENV:
        if not hl_datacenters.clean_datacenter(
            True, c.DC_NAME[0],
            vdc=c.VDC_HOST,
            vdc_password=c.VDC_ROOT_PASSWORD

        ):
            raise errors.DataCenterException(
                "Failed to clean datacenter %s" % c.DC_NAME[0]
            )
