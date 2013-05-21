"""
Linking feature test
"""

import logging
from art.rhevm_api.tests_lib.low_level.storagedomains import\
    cleanDataCenter
from art.test_handler.exceptions import\
    DataCenterException, VMException, NetworkException
from art.rhevm_api.tests_lib.low_level.vms import addVm
from art.rhevm_api.tests_lib.high_level.networks import\
    createAndAttachNetworkSN, prepareSetup
logger = logging.getLogger("Linking")

#################################################


def setup_package():
    """
    Prepare environment
    """
    import config
    local_dict = {config.VLAN_NETWORKS[0]: {'vlan_id':
                                            config.VLAN_ID[0],
                                            'nic': config.HOST_NICS[1],
                                            'required': 'false'},
                  config.VLAN_NETWORKS[1]: {'vlan_id':
                                            config.VLAN_ID[1],
                                            'nic': config.HOST_NICS[1],
                                            'required': 'false'},
                  config.VLAN_NETWORKS[2]: {'vlan_id':
                                            config.VLAN_ID[2],
                                            'nic': config.HOST_NICS[1],
                                            'required': 'false'},
                  config.VLAN_NETWORKS[3]: {'vlan_id':
                                            config.VLAN_ID[3],
                                            'nic': config.HOST_NICS[1],
                                            'required': 'false'},
                  config.VLAN_NETWORKS[4]: {'vlan_id':
                                            config.VLAN_ID[4],
                                            'nic': config.HOST_NICS[1],
                                            'required': 'false'}}
    if not prepareSetup(hosts=config.HOSTS[0], cpuName=config.CPU_NAME,
                        username='root', password=config.HOSTS_PW,
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
                        vm_password=config.HOSTS_PW):
        raise NetworkException("Cannot create setup")
    if not createAndAttachNetworkSN(data_center=config.DC_NAME,
                                    cluster=config.CLUSTER_NAME,
                                    host=config.HOSTS[0],
                                    network_dict=local_dict,
                                    auto_nics=[config.HOST_NICS[0],
                                               config.HOST_NICS[1]]):
        raise NetworkException("Cannot create and attach network")
    if not addVm(True, name=config.VM_NAME[1], cluster=config.CLUSTER_NAME,
                 template=config.TEMPLATE_NAME,
                 display_type=config.DISPLAY_TYPE):
        raise VMException("Cannot create VM from template")


def teardown_package():
    """
    Cleans the environment
    """
    import config
    if not cleanDataCenter(positive=True, datacenter=config.DC_NAME):
        raise DataCenterException("Cannot remove setup")
