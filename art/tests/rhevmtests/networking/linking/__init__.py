"""
Linking feature test
"""

import logging

from rhevmtests.networking import config
from art.rhevm_api.tests_lib.low_level.storagedomains import cleanDataCenter
from art.test_handler.exceptions import NetworkException
from art.rhevm_api.tests_lib.low_level.vms import addVm
from art.rhevm_api.tests_lib.high_level.networks import(
    createAndAttachNetworkSN, prepareSetup, remove_net_from_setup
)
from art.rhevm_api.tests_lib.low_level import vms
from art.rhevm_api.tests_lib.high_level import vms as hl_vm


logger = logging.getLogger("Linking")

#################################################


def setup_package():
    """
    Prepare environment
    """
    local_dict = {config.VLAN_NETWORKS[0]: {'vlan_id':
                                            config.VLAN_ID[0],
                                            'nic': 1,
                                            'required': 'false'},
                  config.VLAN_NETWORKS[1]: {'vlan_id':
                                            config.VLAN_ID[1],
                                            'nic': 1,
                                            'required': 'false'},
                  config.VLAN_NETWORKS[2]: {'vlan_id':
                                            config.VLAN_ID[2],
                                            'nic': 1,
                                            'required': 'false'},
                  config.VLAN_NETWORKS[3]: {'vlan_id':
                                            config.VLAN_ID[3],
                                            'nic': 1,
                                            'required': 'false'},
                  config.VLAN_NETWORKS[4]: {'vlan_id':
                                            config.VLAN_ID[4],
                                            'nic': 1,
                                            'required': 'false'}}
    if config.GOLDEN_ENV:
        logger.info(
            "Running on golden env, setting up only networks and starting "
            " VM %s at host %s", config.VM_NAME[0], config.HOSTS[0]
        )

        if not hl_vm.start_vm_on_specific_host(
                vm=config.VM_NAME[0], host=config.HOSTS[0]
        ):
            raise NetworkException(
                "Cannot start VM %s at host %s" % (
                    config.VM_NAME[0], config.HOSTS[0]
                )
            )
        if not vms.waitForVMState(vm=config.VM_NAME[0]):
            raise NetworkException("VM %s did not come up" % config.VM_NAME[0])

    else:
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
                            template_name=config.TEMPLATE_NAME[0],
                            vm_password=config.VMS_LINUX_PW,
                            mgmt_network=config.MGMT_BRIDGE,
                            auto_nics=[0]):
            raise NetworkException("Cannot create setup")

        if not addVm(
                True, name=config.VM_NAME[1], cluster=config.CLUSTER_NAME[0],
                template=config.TEMPLATE_NAME[0],
                display_type=config.DISPLAY_TYPE
        ):
            raise NetworkException("Cannot create VM from template")

    if not createAndAttachNetworkSN(
            data_center=config.DC_NAME[0], cluster=config.CLUSTER_NAME[0],
            host=config.VDS_HOSTS[0], network_dict=local_dict,
            auto_nics=[0, 1]
    ):
        raise NetworkException("Cannot create and attach network")


def teardown_package():
    """
    Cleans the environment
    """
    if config.GOLDEN_ENV:
        logger.info(
            "Running on golden env, removing networks and stopping VM %s",
            config.VM_NAME[0]
        )
        if not vms.stopVm(True, vm=config.VM_NAME[0]):
            raise NetworkException(
                "Failed to stop VM: %s" % config.VM_NAME[0]
            )

        if not remove_net_from_setup(
                host=config.VDS_HOSTS[0], auto_nics=[0],
                data_center=config.DC_NAME[0], all_net=True,
                mgmt_network=config.MGMT_BRIDGE
        ):
            raise NetworkException(
                "Failed to remove networks from DC %s" % config.DC_NAME[0]
            )

    else:
        if not cleanDataCenter(
                positive=True, datacenter=config.DC_NAME[0],
                vdc=config.VDC_HOST, vdc_password=config.VDC_ROOT_PASSWORD
        ):
            raise NetworkException("Cannot remove setup")
