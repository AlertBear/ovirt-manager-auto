"""
Test ArbitraryVlanDeviceName
Supporting vlan devices with names not in standard "dev.VLANID"
(e.g. eth0.10-fcoe, em1.myvlan10, vlan20, ...).
"""

import logging
from rhevmtests.networking import config, network_cleanup
from art.rhevm_api.tests_lib.high_level.networks import (
    create_basic_setup, remove_basic_setup
)
from art.test_handler.exceptions import NetworkException
from rhevmtests.networking.arbitrary_vlan_device_name.helper import(
    set_libvirtd_sasl
)

logger = logging.getLogger("Arbitrary_VlanDeviceName_Init")


def setup_package():
    """
    Prepare environment
    """
    if config.GOLDEN_ENV:
        logger.info("Running on golden env, no setup")
        network_cleanup()

    else:
        logger.info("Create setup with datacenter, cluster and host")
        if not create_basic_setup(
            datacenter=config.DC_NAME[0], storage_type=config.STORAGE_TYPE,
            version=config.COMP_VERSION, cluster=config.CLUSTER_NAME[0],
            cpu=config.CPU_NAME, host=config.HOSTS[0],
            host_password=config.HOSTS_PW
        ):
            raise NetworkException("Failed to create setup")

    logger.info("Disabling sasl in libvirt")
    if not set_libvirtd_sasl(host_obj=config.VDS_HOSTS[0], sasl=False):
        raise NetworkException(
            "Failed to disable sasl on %s" % config.HOSTS[0]
        )


def teardown_package():
    """
    Cleans the environment
    """
    if config.GOLDEN_ENV:
        logger.info("Running on golden env, no teardown")

    else:
        if not remove_basic_setup(
            datacenter=config.DC_NAME[0], cluster=config.CLUSTER_NAME[0],
            hosts=[config.HOSTS[0]]
        ):
            logger.error("Failed to remove setup")

    logger.info("Enabling sasl in libvirt")
    if not set_libvirtd_sasl(host_obj=config.VDS_HOSTS[0]):
        logger.error("Failed to enable sasl on %s", config.HOSTS[0])
