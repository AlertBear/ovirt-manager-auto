"""
Init file for hosted_engine_ha package
"""
import logging

import art.core_api.apis_exceptions as core_errors
import art.core_api.apis_utils as utils
import art.test_handler as t_handler
import art.test_handler.exceptions as errors
import config as conf
import hosted_engine_ha_test as he_test

logger = logging.getLogger(__name__)
t_handler.find_test_file.__test__ = False


def get_number_of_he_hosts(host_executor):
    """
    Get number of hosts from metadata

    :param host_executor: host executor
    :type host_executor: VDS
    :return: number of hosts under metadata
    :rtype: int
    """
    return len(
        he_test.HostedEngineTest.get_he_stats(
            host_executor
        ).keys()
    )


def wait_until_he_metadata(host_executor, num_of_hosts):
    """
    Wait until metadata will have information about specific number of hosts

    :param host_executor: host executor
    :type host_executor: VDS
    :param num_of_hosts: number of hosts, that must exist under metadata
    :type num_of_hosts: int
    :return: True, if in given timeout exist information about
    specific number of hosts under metadata, otherwise False
    :rtype: bool
    """
    sampler = utils.TimeoutingSampler(
        conf.SAMPLER_TIMEOUT,
        conf.SAMPLER_SLEEP,
        get_number_of_he_hosts,
        host_executor
    )
    try:
        for sample in sampler:
            logger.info(
                "Wait until metadata will have information about %d hosts",
                num_of_hosts
            )
            if sample == num_of_hosts:
                return True
    except core_errors.APITimeout:
        logger.error(
            "Metadata still not have information about %d hosts", num_of_hosts
        )
        return False


def setup_package():
    """
    Wait until HE agent metadata updated
    """
    for vds in conf.VDS_HOSTS:
        logger.info("Copy %s script to %s", conf.GET_HE_STATS_SCRIPT, vds.fqdn)
        vds.copy_to(
            conf.SLAVE_HOST,
            t_handler.find_test_file(conf.GET_HE_STATS_SCRIPT),
            conf.SCRIPT_DEST_PATH
        )
    if not wait_until_he_metadata(
        conf.VDS_HOSTS[0].executor(), len(conf.HOSTS)
    ):
        raise errors.HostedEngineException(
            "Metadata still not have information about all hosts"
        )
