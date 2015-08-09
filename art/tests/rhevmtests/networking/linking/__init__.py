#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Linking feature test
"""

import logging

from rhevmtests.networking import config, network_cleanup
from art.rhevm_api.tests_lib.high_level.datacenters import clean_datacenter
from art.test_handler.exceptions import NetworkException
from art.rhevm_api.tests_lib.low_level.vms import addVm
from art.rhevm_api.tests_lib.low_level import vms
from art.rhevm_api.tests_lib.high_level.networks import(
    createAndAttachNetworkSN, prepareSetup, remove_net_from_setup
)
import rhevmtests.networking.helper as net_help

logger = logging.getLogger("Linking_Init")

#################################################


def setup_package():
    """
    Prepare environment
    """
    local_dict = {
        config.VLAN_NETWORKS[0]: {
            "vlan_id": config.VLAN_ID[0], "nic": 1, "required": "false"
        },
        config.VLAN_NETWORKS[1]: {
            "vlan_id": config.VLAN_ID[1], "nic": 1, "required": "false"
        },
        config.VLAN_NETWORKS[2]: {
            "vlan_id": config.VLAN_ID[2], "nic": 1, "required": "false"
        },
        config.VLAN_NETWORKS[3]: {
            "vlan_id": config.VLAN_ID[3], "nic": 1, "required": "false"
        },
        config.VLAN_NETWORKS[4]: {
            "vlan_id": config.VLAN_ID[4], "nic": 1, "required": "false"
        }
    }
    if config.GOLDEN_ENV:
        network_cleanup()
        logger.info(
            "Running on golden env, setting up only networks and starting "
            " VM %s at host %s", config.VM_NAME[0], config.HOSTS[0]
        )

        if not net_help.run_vm_once_specific_host(
                vm=config.VM_NAME[0], host=config.HOSTS[0]
        ):
            raise NetworkException(
                "Cannot start VM %s at host %s" %
                (config.VM_NAME[0], config.HOSTS[0])
            )
        if not vms.waitForVMState(vm=config.VM_NAME[0]):
            raise NetworkException("VM %s did not come up" % config.VM_NAME[0])

    else:
        if not prepareSetup(
            hosts=config.VDS_HOSTS[0], cpuName=config.CPU_NAME,
            username=config.HOSTS_USER, password=config.HOSTS_PW,
            datacenter=config.DC_NAME[0],
            storageDomainName=config.STORAGE_NAME[0],
            storage_type=config.STORAGE_TYPE, cluster=config.CLUSTER_NAME[0],
            lun_address=config.LUN_ADDRESS[0], lun_target=config.LUN_TARGET[0],
            luns=config.LUN[0], version=config.COMP_VERSION,
            vmName=config.VM_NAME[0], template_name=config.TEMPLATE_NAME[0],
            vm_password=config.VMS_LINUX_PW, mgmt_network=config.MGMT_BRIDGE,
            auto_nics=[0]
        ):
            raise NetworkException("Cannot create setup")

        if not addVm(
                True, name=config.VM_NAME[1], cluster=config.CLUSTER_NAME[0],
                template=config.TEMPLATE_NAME[0],
                display_type=config.DISPLAY_TYPE
        ):
            raise NetworkException(
                "Cannot create VM %s from template" % config.VM_NAME[1]
            )

    if not createAndAttachNetworkSN(
            data_center=config.DC_NAME[0], cluster=config.CLUSTER_NAME[0],
            host=config.VDS_HOSTS[0], network_dict=local_dict,
            auto_nics=[0, 1]
    ):
        raise NetworkException("Cannot create and attach networks")


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
            logger.error(
                "Failed to stop VM: %s", config.VM_NAME[0]
            )

        if not remove_net_from_setup(
                host=config.VDS_HOSTS[0], auto_nics=[0],
                data_center=config.DC_NAME[0], all_net=True,
                mgmt_network=config.MGMT_BRIDGE
        ):
            logger.error("Failed to remove networks from setup")

    else:
        if not clean_datacenter(
                positive=True, datacenter=config.DC_NAME[0],
                vdc=config.VDC_HOST, vdc_password=config.VDC_ROOT_PASSWORD
        ):
            logger.error("Cannot remove setup")
