"""
SLA test
"""

import logging

import art.rhevm_api.tests_lib.high_level.datacenters as datacenters
from art.rhevm_api.tests_lib.low_level.storagedomains import cleanDataCenter
import art.rhevm_api.tests_lib.low_level.vms as vms
import art.test_handler.exceptions as errors
from art.test_handler.settings import opts

logger = logging.getLogger("SLA")
AFFINITY = opts['elements_conf']['RHEVM Enums']['vm_affinity_user_migratable']

#################################################


def setup_package():
    """
    Prepare environment for SLA test
    """
    import config
    logger.info("Building setup...")
    datacenters.build_setup(config.PARAMETERS, config.PARAMETERS,
                            config.STORAGE_TYPE, config.TEST_NAME)
    if not vms.createVm(positive=True, vmName=config.VM_NAME,
                        vmDescription="Watchdog VM",
                        cluster=config.CLUSTER_NAME,
                        storageDomainName=config.DATA_NAME[0],
                        size=6 * 1024 ** 3, nic='nic1',
                        memory=2 * 1024 ** 3,
                        watchdog_model=config.WATCHDOG_MODEL,
                        watchdog_action='none',
                        placement_affinity=AFFINITY,
                        placement_host=config.HOSTS[0],
                        vnic_profile='rhevm'):
        raise errors.VMException("Cannot add VM")
    if not vms.unattendedInstallation(positive=True, vm=config.VM_NAME,
                                      cobblerAddress=config.COBBLER_ADDRESS,
                                      cobblerUser=config.COBBLER_USER,
                                      cobblerPasswd=config.COBBLER_PASSWDd,
                                      image=config.COBBLER_PROFILE,
                                      nic='nic1'):
        raise errors.VMException("Cannot install Linux OS")


def teardown_package():
    """
    Cleans the environment
    """
    import config
    logger.info("Teardown...")
    cleanDataCenter(True, config.DC_NAME, vdc=config.VDC,
                    vdc_password=config.VDC_PASSWORD)
