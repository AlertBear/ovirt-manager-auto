"""
NetworkFilter Test
"""

import logging
from rhevmtests.networking import config, network_cleanup
from art.rhevm_api.tests_lib.low_level.storagedomains import cleanDataCenter
from art.rhevm_api.tests_lib.high_level.networks import prepareSetup
from art.test_handler.exceptions import NetworkException
from art.rhevm_api.tests_lib.low_level import vms
from art.rhevm_api.tests_lib.high_level import vms as hl_vm

logger = logging.getLogger("Network_Filter_Init")

#################################################


def setup_package():
    """
    Prepare environment
    """
    if config.GOLDEN_ENV:
        network_cleanup()
        logger.info(
            "Running on golden env, starting VM %s on host %s",
            config.VM_NAME[0], config.HOSTS[0]
        )

        if not hl_vm.start_vm_on_specific_host(
                vm=config.VM_NAME[0], host=config.HOSTS[0]
        ):
            raise NetworkException(
                "Cannot start VM %s on host %s" %
                (config.VM_NAME[0], config.HOSTS[0])
            )
        if not vms.waitForVMState(vm=config.VM_NAME[0]):
            raise NetworkException(
                "VM %s did not come up" % config.VM_NAME[0]
            )

    else:
        logger.info("Creating data center, cluster, adding host and storage")
        if not prepareSetup(hosts=config.VDS_HOSTS[0],
                            cpuName=config.CPU_NAME,
                            username=config.HOSTS_USER,
                            password=config.HOSTS_PW,
                            datacenter=config.DC_NAME[0],
                            storageDomainName=config.STORAGE_NAME[0],
                            storage_type=config.STORAGE_TYPE,
                            cluster=config.CLUSTER_NAME[0],
                            lun_address=config.LUN_ADDRESS[0],
                            lun_target=config.LUN_TARGET[0],
                            luns=config.LUN[0], version=config.COMP_VERSION,
                            vmName=config.VM_NAME[0],
                            vm_password=config.VMS_LINUX_PW,
                            mgmt_network=config.MGMT_BRIDGE,
                            auto_nics=[0]):
            raise NetworkException("Cannot create setup")


def teardown_package():
    """
    Cleans the environment
    """
    if config.GOLDEN_ENV:
        logger.info(
            "Running on golden env, stopping VM %s", config.VM_NAME[0]
        )
        if not vms.stopVm(True, vm=config.VM_NAME[0]):
            logger.error(
                "Failed to stop VM: %s", config.VM_NAME[0]
            )

    else:
        if not cleanDataCenter(
                positive=True, datacenter=config.DC_NAME[0],
                vdc=config.VDC_HOST, vdc_password=config.VDC_ROOT_PASSWORD
        ):
            logger.error("Cannot remove setup")
