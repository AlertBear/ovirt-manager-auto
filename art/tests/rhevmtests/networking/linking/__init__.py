"""
Linking feature test
"""

import logging
from rhevmtests.networking import config
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
                        datacenter=config.DC_NAME[0],
                        storageDomainName=config.STORAGE_NAME[0],
                        storage_type=config.STORAGE_TYPE,
                        cluster=config.CLUSTER_NAME[0],
                        lun_address=config.LUN_ADDRESS[0],
                        lun_target=config.LUN_TARGET[0],
                        luns=config.LUN[0], version=config.COMP_VERSION,
                        vmName=config.VM_NAME[0],
                        template_name=config.TEMPLATE_NAME[0],
                        vm_password=config.VMS_LINUX_PW,
                        mgmt_network=config.MGMT_BRIDGE,
                        vm_network=config.MGMT_BRIDGE,
                        auto_nics=[config.HOST_NICS[0]]):
        raise NetworkException("Cannot create setup")
    if not createAndAttachNetworkSN(data_center=config.DC_NAME[0],
                                    cluster=config.CLUSTER_NAME[0],
                                    host=config.HOSTS[0],
                                    network_dict=local_dict,
                                    auto_nics=[config.HOST_NICS[0],
                                               config.HOST_NICS[1]]):
        raise NetworkException("Cannot create and attach network")
    if not addVm(True, name=config.VM_NAME[1], cluster=config.CLUSTER_NAME[0],
                 template=config.TEMPLATE_NAME[0],
                 display_type=config.DISPLAY_TYPE):
        raise VMException("Cannot create VM from template")


def teardown_package():
    """
    Cleans the environment
    """
    if not cleanDataCenter(positive=True, datacenter=config.DC_NAME[0],
                           vdc=config.VDC_HOST,
                           vdc_password=config.VDC_ROOT_PASSWORD):
        raise DataCenterException("Cannot remove setup")
