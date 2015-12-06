"""
Helper functions for scheduler tests
"""
import logging
import rhevmtests.sla.config as conf
import art.test_handler.exceptions as errors
import art.rhevm_api.tests_lib.low_level.hosts as ll_hosts
import art.rhevm_api.tests_lib.low_level.storagedomains as ll_sd

logger = logging.getLogger(__name__)


def choose_host_as_spm(host_name, data_center, storage_domain):
    """
    Select host as SPM and verify that data center storage domain active

    :param host_name: host name
    :type host_name: str
    :param data_center: data center name
    :type data_center: str
    :param storage_domain: storage domain name
    :type storage_domain: str
    :raises: DataCenterException, StorageDomainException
    """
    if not ll_hosts.checkHostSpmStatus(True, host_name):
        logger.info("Select host %s as SPM", host_name)
        if not ll_hosts.select_host_as_spm(
            positive=True,
            host=host_name,
            datacenter=data_center,
            wait=False
        ) or not ll_hosts.wait_for_host_spm(host_name):
            raise errors.DataCenterException(
                "Selecting host %s as SPM failed" % host_name
            )
        if not ll_sd.waitForStorageDomainStatus(
            positive=True, dataCenterName=data_center,
            storageDomainName=storage_domain,
            expectedStatus=conf.ENUMS["storage_domain_state_active"]
        ):
            raise errors.StorageDomainException(
                "Failed to activate storage domain %s "
                "after force change of SPM host" % storage_domain
            )
