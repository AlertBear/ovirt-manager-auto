"""
Jumbo Frames test
"""

import logging
from art.rhevm_api.tests_lib.low_level.storagedomains import\
    cleanDataCenter
from art.rhevm_api.tests_lib.high_level.networks import prepareSetup, \
    createAndAttachNetworkSN
from art.rhevm_api.tests_lib.low_level.vms import addVm, startVm,\
    waitForVmsStates
from art.rhevm_api.utils.test_utils import toggleServiceOnHost
from art.test_handler.exceptions import DataCenterException,\
    NetworkException, VMException

logger = logging.getLogger("Jumbo")
firewall_service = "iptables"

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
                        storageDomainName=config.STORAGE_NAME,
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
                        template_name=config.TEMPLATE_NAME,
                        vm_password=config.HOSTS_PW,
                        auto_nics=[config.HOST_NICS[0]]):
        raise NetworkException("Cannot create setup")

    if not addVm(True, name=config.VM_NAME[1],
                 cluster=config.CLUSTER_NAME,
                 template=config.TEMPLATE_NAME,
                 placement_host=config.HOSTS[1],
                 display_type=config.DISPLAY_TYPE):
        raise VMException("Cannot create VM from template")

    if not startVm(True, vm=config.VM_NAME[1]):
            raise NetworkException("Cannot start VM")

    if not waitForVmsStates(True,
                            names=config.VM_NAME[0]+','+config.VM_NAME[1],
                            states='up'):
            raise NetworkException("VM status is not up in the "
                                   "predefined timeout")

    for host in config.HOSTS:
        stop_firewall = toggleServiceOnHost(positive=True,
                                            host=host,
                                            user=config.HOSTS_USER,
                                            password=config.HOSTS_PW,
                                            service=firewall_service,
                                            action="STOP")
        if not stop_firewall:
            raise NetworkException("Cannot stop Firewall service")


def teardown_package():
    """
    Cleans the environment
    """
    import config

    local_dict = {config.NETWORKS[0]: {'mtu': config.MTU[3],
                                       'nic': config.HOST_NICS[1],
                                       'required': 'false'},
                  config.NETWORKS[1]: {'mtu': config.MTU[3],
                                       'nic': config.HOST_NICS[2],
                                       'required': 'false'},
                  config.NETWORKS[2]: {'mtu': config.MTU[3],
                                       'nic': config.HOST_NICS[3],
                                       'required': 'false'}}

    logger.info("Setting all hosts networks to MTU: %s", config.MTU[3])
    if not createAndAttachNetworkSN(data_center=config.DC_NAME,
                                    cluster=config.CLUSTER_NAME,
                                    host=config.HOSTS,
                                    network_dict=local_dict,
                                    auto_nics=[config.HOST_NICS[0]]):
        raise NetworkException("Cannot create and attach network")

    logger.info("Cleanning hosts interface")
    if not createAndAttachNetworkSN(data_center=config.DC_NAME,
                                    cluster=config.CLUSTER_NAME,
                                    host=config.HOSTS,
                                    network_dict={},
                                    auto_nics=[config.HOST_NICS[0]]):
        raise NetworkException("Cannot create and attach network")

    if not cleanDataCenter(positive=True, datacenter=config.DC_NAME):
        raise DataCenterException("Cannot remove setup")
