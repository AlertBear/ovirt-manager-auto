"""
Storage spm priority sanity package
"""
from art.rhevm_api.tests_lib.high_level import datacenters
from art.rhevm_api.tests_lib.low_level import storagedomains, hosts
from rhevmtests.storage.storage_spm_priority_sanity import config

import logging
logger = logging.getLogger(__name__)


def setup_package():
    """
    Prepares environment
    """
    if not config.GOLDEN_ENV:
        datacenters.build_setup(config.PARAMETERS, config.PARAMETERS,
                                config.STORAGE_TYPE, config.TESTNAME)

    logger.info("Make sure there are only %s hosts active in the environment",
                config.NUMBER_OF_HOSTS)
    cluster_hosts = hosts.get_cluster_hosts(config.CLUSTER_NAME)
    assert len(cluster_hosts) == config.NUMBER_OF_HOSTS
    for host in config.HOSTS:
        if host not in cluster_hosts:
            if hosts.isHostUp(True, host):
                assert hosts.deactivateHost(True, host)

    config.TEST_HOSTS = cluster_hosts
    logger.info("Hosts for tests: %s", config.TEST_HOSTS)

    logger.info("Getting hosts' priorities to restore them later")
    for host in cluster_hosts:
        config.TEST_HOSTS_PRIORITIES[host] = hosts.getSPMPriority(host)

    logger.info("Host priorities: %s", config.TEST_HOSTS_PRIORITIES)


def teardown_package():
    """
    Cleans the environment
    """
    logger.info("Restoring host priorities before test")
    for host, priority in config.TEST_HOSTS_PRIORITIES.iteritems():
        hosts.setSPMPriority(True, host, priority)

    logger.info("Make sure all the host are activated")
    for host in config.HOSTS:
        if not hosts.isHostUp(True, host):
            hosts.activateHost(True, host)

    if not config.GOLDEN_ENV:
        assert storagedomains.cleanDataCenter(True, config.DATA_CENTER_NAME)
