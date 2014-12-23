"""
Migration feature test
"""

import logging
from rhevmtests.networking import config, network_cleanup
from art.rhevm_api.tests_lib.low_level.storagedomains import cleanDataCenter
from art.test_handler.exceptions import NetworkException
from art.rhevm_api.tests_lib.high_level.networks import prepareSetup
from art.rhevm_api.tests_lib.low_level import vms
from art.rhevm_api.tests_lib.high_level import vms as hl_vm
from rhevmtests.networking.network_migration.helper import set_host_status

logger = logging.getLogger("Network_Migration_Init")

#################################################


def setup_package():
    """
    Prepare environment
    """
    if config.GOLDEN_ENV:
        logger.info(
            "Running on golden env, starting VM %s on host %s",
            config.VM_NAME[0], config.HOSTS[0]
        )
        network_cleanup()

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
        logger.info(
            "Set all but 2 hosts in the Cluster %s to the maintenance "
            "state", config.CLUSTER_NAME[0]
        )
        set_host_status()
    else:
        if not prepareSetup(
            hosts=config.VDS_HOSTS, cpuName=config.CPU_NAME,
            username=config.HOSTS_USER, password=config.HOSTS_PW,
            datacenter=config.DC_NAME[0],
            storageDomainName=config.STORAGE_NAME[0],
            storage_type=config.STORAGE_TYPE, cluster=config.CLUSTER_NAME[0],
            lun_address=config.LUN_ADDRESS[0], lun_target=config.LUN_TARGET[0],
            luns=config.LUN[0], version=config.COMP_VERSION,
            placement_host=config.HOSTS[0], vmName=config.VM_NAME[0],
            vm_password=config.VMS_LINUX_PW, mgmt_network=config.MGMT_BRIDGE
        ):
            raise NetworkException("Cannot create setup")
    logger.info("Disabling firewall on the Hosts")
    for host in config.VDS_HOSTS:
        if not host.service(config.FIREWALL_SRV).stop():
            raise NetworkException("Cannot stop Firewall service")


def teardown_package():
    """
    Cleans the environment
    """
    logger.info("Enabling firewall on the Hosts")
    for host in config.VDS_HOSTS:
        if not host.service(config.FIREWALL_SRV).start():
            raise NetworkException("Cannot start Firewall service")
    if config.GOLDEN_ENV:
        logger.info(
            "Running on golden env, stopping VM %s", config.VM_NAME[0]
        )
        if not vms.stopVm(True, vm=config.VM_NAME[0]):
            raise NetworkException(
                "Failed to stop VM: %s" % config.VM_NAME[0]
            )
        logger.info("Set non-Network hosts to the active state")
        set_host_status(activate=True)
    else:
        if not cleanDataCenter(
            positive=True, datacenter=config.DC_NAME[0], vdc=config.VDC_HOST,
            vdc_password=config.VDC_ROOT_PASSWORD
        ):
            raise NetworkException("Cannot remove setup")
