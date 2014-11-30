"""
Network QOS feature test
"""

import logging
from art.rhevm_api.tests_lib.low_level.vms import addVm, startVm
from rhevmtests.networking import config
from art.rhevm_api.tests_lib.low_level.storagedomains import cleanDataCenter
from art.test_handler.exceptions import NetworkException
from art.rhevm_api.tests_lib.high_level.networks import prepareSetup
from art.rhevm_api.tests_lib.low_level import vms

logger = logging.getLogger("Network_VNIC_QoS_Init")

#################################################


def setup_package():
    """
    Prepare environment
    """
    if config.GOLDEN_ENV:
        logger.info(
            "Running on golden env, starting 1 VM %s on host %s",
            config.VM_NAME[0], config.HOSTS[0]
        )
        if not startVm(
            positive=True, vm=config.VM_NAME[0], wait_for_ip=True,
            placement_host=config.HOSTS[0]
        ):
            raise NetworkException(
                "Cannot start VM %s on host %s" %
                (config.VM_NAME[0], config.HOSTS[0])
            )
    else:
        if not prepareSetup(
            hosts=config.VDS_HOSTS, cpuName=config.CPU_NAME,
            username=config.HOSTS_USER, password=config.HOSTS_PW,
            datacenter=config.DC_NAME[0],
            storageDomainName=config.STORAGE_NAME[0],
            storage_type=config.STORAGE_TYPE,
            cluster=config.CLUSTER_NAME[0],
            lun_address=config.LUN_ADDRESS[0],
            lun_target=config.LUN_TARGET[0],
            luns=config.LUN[0], version=config.COMP_VERSION,
            placement_host=config.HOSTS[0], vmName=config.VM_NAME[0],
            template_name=config.TEMPLATE_NAME[0],
            vm_password=config.VMS_LINUX_PW, mgmt_network=config.MGMT_BRIDGE
        ):
            raise NetworkException("Cannot create setup")

        logger.info("Add VM %s to the setup", config.VM_NAME[1])
        if not addVm(
            True, name=config.VM_NAME[1], cluster=config.CLUSTER_NAME[0],
            template=config.TEMPLATE_NAME[0], display_type=config.DISPLAY_TYPE,
            placement_host=config.HOSTS[0]
        ):
            raise NetworkException("Cannot create VM %s from template" %
                                   config.VM_NAME[1])


def teardown_package():
    """
    Cleans the environment
    """
    if config.GOLDEN_ENV:
        logger.info(
            "Running on golden env, stopping VM %s", config.VM_NAME[0]
        )

        if not vms.stopVms(vms=config.VM_NAME[0]):
            logger.error(
                "Failed to stop VM: %s" % config.VM_NAME[0]
            )

    else:
        if not cleanDataCenter(
            positive=True, datacenter=config.DC_NAME[0], vdc=config.VDC_HOST,
            vdc_password=config.VDC_ROOT_PASSWORD
        ):
            logger.error("Cannot remove setup")
