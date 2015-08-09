#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Jumbo Frames init
"""

import logging
from rhevmtests.networking import config, network_cleanup
from art.rhevm_api.tests_lib.high_level.datacenters import clean_datacenter
import art.rhevm_api.tests_lib.high_level.networks as hl_networks
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import rhevmtests.networking.helper as net_help
from art.test_handler.exceptions import NetworkException

logger = logging.getLogger("Jumbo_frame_Init")


def setup_package():
    """
    Prepare environment
    Creates data center, cluster, two hosts, storage, two VMs and template
    """
    if config.GOLDEN_ENV:
        network_cleanup()
        logger.info(
            "Running on GE, using\nData center: %s\nCluster: %s\nhosts: %s, "
            "%s",
            config.DC_NAME[0], config.CLUSTER_NAME[0], config.HOSTS[0],
            config.HOSTS[1]
        )

        for i in range(2):
            logger.info(
                "Starting up VM %s on host %s", config.VM_NAME[i],
                config.HOSTS[i]
            )
            if not net_help.run_vm_once_specific_host(
                vm=config.VM_NAME[i], host=config.HOSTS[i]
            ):
                raise NetworkException(
                    "Cannot start VM %s on host %s" % (
                        config.VM_NAME[i], config.HOSTS[i]
                    )
                )

    else:
        logger.info(
            "Creating data center %s, cluster %s, adding hosts %s, %s and"
            "storage",
            config.DC_NAME[0], config.CLUSTER_NAME[0], config.HOSTS[0],
            config.HOSTS[1]
        )
        if not hl_networks.prepareSetup(
            hosts=config.VDS_HOSTS, cpuName=config.CPU_NAME,
            username=config.HOSTS_USER, password=config.HOSTS_PW,
            datacenter=config.DC_NAME[0], auto_nics=[0],
            storageDomainName=config.STORAGE_NAME[0],
            template=config.TEMPLATE_NAME[0],
            storage_type=config.STORAGE_TYPE, cluster=config.CLUSTER_NAME[0],
            lun_address=config.LUN_ADDRESS[0], lun_target=config.LUN_TARGET[0],
            luns=config.LUN[0], version=config.COMP_VERSION,
            placement_host=config.HOSTS[0], vmName=config.VM_NAME[0],
            vm_password=config.VMS_LINUX_PW, mgmt_network=config.MGMT_BRIDGE
        ):
            raise NetworkException("Cannot create setup")

        if not ll_vms.addVm(
            True, name=config.VM_NAME[1], cluster=config.CLUSTER_NAME[0],
            template=config.TEMPLATE_NAME[0], placement_host=config.HOSTS[1],
            display_type=config.DISPLAY_TYPE
        ):
            raise NetworkException(
                "Cannot create VM %s from template %s" % (
                    config.VM_NAME[1], config.TEMPLATE_NAME[0]
                )
            )
        if not ll_vms.startVm(
            True, vm=config.VM_NAME[1], wait_for_status="up"
        ):
            raise NetworkException("Cannot start VM %s" % config.VM_NAME[1])

    logger.info("Getting VMs IPs")
    for i in range(2):
        config.VM_IP_LIST.append(
            ll_vms.waitForIP(config.VM_NAME[i])[1]["ip"]
        )


def teardown_package():
    """
    Cleans the environment
    """
    local_dict = {
        config.NETWORKS[0]: {
            "mtu": config.MTU[3],
            "nic": 1,
            "required": "false"
        },
        config.NETWORKS[1]: {
            "mtu": config.MTU[3],
            "nic": 2,
            "required": "false"
        },
        config.NETWORKS[2]: {
            "mtu": config.MTU[3],
            "nic": 3,
            "required": "false"
        }
    }

    logger.info(
        "Setting all hosts NICs to MTU: %s", config.MTU[3]
    )
    if not hl_networks.createAndAttachNetworkSN(
        data_center=config.DC_NAME[0], cluster=config.CLUSTER_NAME[0],
        host=config.VDS_HOSTS[:2], network_dict=local_dict, auto_nics=[0]
    ):
        logger.error(
            "Cannot set MTU %s on %s", config.MTU[3], config.VDS_HOSTS[:2]
        )

    logger.info("Cleaning hosts interface")
    if not hl_networks.createAndAttachNetworkSN(
        data_center=config.DC_NAME[0], cluster=config.CLUSTER_NAME[0],
        host=config.VDS_HOSTS[:2], network_dict={}, auto_nics=[0]
    ):
        logger.error("Failed to Clean hosts interfaces")

    if config.GOLDEN_ENV:
        logger.info(
            "Running on GE just stopping VMs: %s, %s",
            config.VM_NAME[0], config.VM_NAME[1]
        )
        if not ll_vms.stopVms(vms=[config.VM_NAME[0], config.VM_NAME[1]]):
            logger.error(
                "Failed to stop VMs: %s %s",
                config.VM_NAME[0], config.VM_NAME[1]
            )
        if not hl_networks.remove_net_from_setup(
            host=config.VDS_HOSTS[:2], auto_nics=[0],
            data_center=config.DC_NAME[0], mgmt_network=config.MGMT_BRIDGE,
            all_net=True
        ):
            logger.error("Cannot remove networks from setup")
    else:
        if not clean_datacenter(
            positive=True, datacenter=config.DC_NAME[0], vdc=config.VDC_HOST,
            vdc_password=config.VDC_ROOT_PASSWORD
        ):
            logger.error("Cannot remove setup")
