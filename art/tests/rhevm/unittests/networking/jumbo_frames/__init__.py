"""
Jumbo Frames test
"""

import logging
from art.rhevm_api.tests_lib.low_level.storagedomains import\
    cleanDataCenter
from art.rhevm_api.tests_lib.high_level.networks import prepareSetup
from art.rhevm_api.tests_lib.low_level.vms import addVm, startVm,\
    waitForVmsStates
from art.test_handler.exceptions import DataCenterException,\
    NetworkException, VMException

logger = logging.getLogger("Jumbo")

#################################################


def setup_package():
    """
    Prepare environment
    Creates data center, cluster, two hosts, storage, two VMs and template
    """
    import config

    logger.info("Creating data center, cluster, adding host and storage")
    if not prepareSetup(hosts=','.join(config.HOSTS), cpuName=config.CPU_NAME,
                        username='root',
                        password=config.HOSTS_PW+','+config.HOSTS_PW,
                        datacenter=config.DC_NAME,
                        storageDomainName=config.DC_NAME + '_data_domain0',
                        storage_type=config.STORAGE_TYPE,
                        cluster=config.CLUSTER_NAME,
                        lun_address=config.LUN_ADDRESS,
                        lun_target=config.LUN_TARGET,
                        luns=config.LUN, version=config.VERSION,
                        cobblerAddress=config.COBBLER_ADDRESS,
                        cobblerUser=config.COBBLER_USER,
                        cobblerPasswd=config.COBBLER_PASSWORD,
                        placement_host=config.HOSTS[0],
                        vmName=config.VM_NAME[0],
                        vm_password=config.HOSTS_PW):
        raise NetworkException("Cannot create setup")

    if not addVm(True, name=config.VM_NAME[1], cluster=config.CLUSTER_NAME,
                 template=config.TEMPLATE_NAME, placement_host=config.HOSTS[1],
                 display_type=config.DISPLAY_TYPE):
        raise VMException("Cannot create VM from template")

    if not startVm(True, vm=config.VM_NAME[1]):
            raise NetworkException("Cannot start VM")
    if not waitForVmsStates(True,
                            names=config.VM_NAME[0]+','+config.VM_NAME[1],
                            states='up'):
            raise NetworkException("VM status is not up in the "
                                   "predefined timeout")


def teardown_package():
    """
    Cleans the environment
    """
    import config

    if not cleanDataCenter(positive=True, datacenter=config.DC_NAME):
        raise DataCenterException("Cannot remove setup")
