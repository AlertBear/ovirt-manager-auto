
"""
Import Export Test
"""

import logging
from art.rhevm_api.utils.test_utils import setPersistentNetwork
from rhevmtests.networking import config, network_cleanup
from art.rhevm_api.tests_lib.low_level.storagedomains import (
    cleanDataCenter, addStorageDomain, attachStorageDomain,
    getStorageDomainNamesForType)
from art.rhevm_api.tests_lib.high_level.storagedomains import(
    detach_and_deactivate_domain
)
from art.rhevm_api.tests_lib.high_level.networks import(
    prepareSetup, createAndAttachNetworkSN, remove_net_from_setup
)
from art.rhevm_api.tests_lib.low_level.templates import(
    exportTemplate, removeTemplate,
    addTemplateNic, removeTemplateFromExportDomain,
    createTemplate)
from art.rhevm_api.tests_lib.low_level.vms import(
    stopVm, addNic, exportVm, removeVm,
    removeVmFromExportDomain, waitForIP, createVm)
from art.test_handler.exceptions import NetworkException

logger = logging.getLogger("Import_Export")

#################################################


def setup_package():
    """
    Prepare environment
    """
    if not config.GOLDEN_ENV:
        logger.info(
            "Creating data center, cluster, adding host and export domain"
        )
        if not prepareSetup(hosts=config.VDS_HOSTS[0], cpuName=config.CPU_NAME,
                            username=config.HOSTS_USER,
                            password=config.HOSTS_PW,
                            datacenter=config.DC_NAME[0],
                            storageDomainName=config.STORAGE_NAME[0],
                            storage_type=config.STORAGE_TYPE,
                            cluster=config.CLUSTER_NAME[0],
                            lun_address=config.LUN_ADDRESS[0],
                            lun_target=config.LUN_TARGET[0],
                            luns=config.LUN[0], version=config.COMP_VERSION,
                            vmName=config.IE_VM,
                            vm_password=config.VMS_LINUX_PW,
                            mgmt_network=config.MGMT_BRIDGE,
                            template_name=config.IE_TEMPLATE):
            raise NetworkException("Cannot create setup")

        logger.info("Stopping VM %s", config.IE_VM)
        if not stopVm(True, vm=config.IE_VM):
            raise NetworkException("Failed to stop VM: %s" %
                                   config.VM_NAME[0])

        logger.info("Adding export domain (NFS) to %s", config.DC_NAME[0],)
        if not addStorageDomain(True, host=config.HOSTS[0],
                                name=config.EXPORT_STORAGE_NAME,
                                type=config.EXPORT_TYPE,
                                storage_type="nfs",
                                address=config.EXPORT_STORAGE_ADDRESS,
                                path=config.EXPORT_STORAGE_PATH):
            raise NetworkException(
                "Cannot create Export Storage Domain "
            )
    else:
        logger.info("Cleaning the GE setup")
        network_cleanup()
        logger.info("Creating new VM %s", config.IE_VM)
        sd_name = getStorageDomainNamesForType(
            datacenter_name=config.DC_NAME[0],
            storage_type=config.STORAGE_TYPE
        )[0]
        if not createVm(True, vmName=config.IE_VM,
                        vmDescription='linux vm',
                        cluster=config.CLUSTER_NAME[0],
                        nic=config.NIC_NAME[0],
                        storageDomainName=sd_name,
                        size=config.DISK_SIZE,
                        diskInterface=config.INTERFACE_VIRTIO,
                        nicType=config.NIC_TYPE_VIRTIO,
                        start='true',
                        display_type=config.DISPLAY_TYPE,
                        os_type=config.OS_TYPE,
                        image=config.COBBLER_PROFILE,
                        user=config.VMS_LINUX_USER,
                        password=config.VMS_LINUX_PW,
                        installation=True,
                        network=config.MGMT_BRIDGE,
                        useAgent=True, diskType=config.DISK_TYPE_SYSTEM):
            logger.error("Cannot create VM")

        logger.info("Creating new Template %s", config.IE_TEMPLATE)
        ip_addr = waitForIP(config.IE_VM)[1]['ip']
        if not setPersistentNetwork(host=ip_addr,
                                    password=config.VMS_LINUX_PW):
            raise NetworkException(
                "Set persistent network failed"
            )
        if not stopVm(True, vm=config.IE_VM):
            raise NetworkException(
                "Cannot stop vm %s" % config.IE_VM
            )
        if not createTemplate(True, vm=config.IE_VM,
                              cluster=config.CLUSTER_NAME[0],
                              name=config.IE_TEMPLATE):
            raise NetworkException(
                "Cannot create template %s" % config.IE_TEMPLATE
            )

    if not attachStorageDomain(True, datacenter=config.DC_NAME[0],
                               storagedomain=config.EXPORT_STORAGE_NAME):
        raise NetworkException(
            "Cannot attach Export Storage Domain to %s" % config.DC_NAME[0]
        )

    local_dict = {config.NETWORKS[0]: {'nic': 1,
                                       'required': 'false'},
                  config.NETWORKS[1]: {'mtu': config.MTU[0],
                                       'nic': 2,
                                       'required': 'false'},
                  config.NETWORKS[2]: {'vlan_id': config.VLAN_ID[0],
                                       'nic': 3,
                                       'required': 'false'}}

    logger.info("Attaching bridged, MTU and VLAN networks to host")
    if not createAndAttachNetworkSN(data_center=config.DC_NAME[0],
                                    cluster=config.CLUSTER_NAME[0],
                                    host=config.VDS_HOSTS[0],
                                    network_dict=local_dict,
                                    auto_nics=[0, 3]):
        raise NetworkException(
            "Cannot create and attach networks to setup"
        )

    logger.info("Adding 4 NICs to new VM and Template ")
    net_list = ["sw1", "sw2", "sw3", None]
    for index, net in enumerate(net_list):
        if not addNic(
                True, config.IE_VM, name=config.NIC_NAME[index + 1],
                network=net, vnic_profile=net
        ):
            raise NetworkException(
                "Cannot add vnic_profile %s to VM %s" % (net, config.IE_VM)
            )

        if not addTemplateNic(
                True, config.IE_TEMPLATE, name=config.NIC_NAME[index + 1],
                data_center=config.DC_NAME[0], network=net
        ):
            raise NetworkException(
                "Cannot add NIC to Template %s" % config.IE_TEMPLATE
            )

    logger.info(
        "Export %s to Export domain", config.IE_TEMPLATE
    )
    if not exportTemplate(
            positive=True, template=config.IE_TEMPLATE,
            storagedomain=config.EXPORT_STORAGE_NAME
    ):
        raise NetworkException(
            "Couldn't export Template %s to export Domain" % config.IE_TEMPLATE
        )

    logger.info("Export %s to Export domain", config.IE_VM)
    if not exportVm(
            positive=True, vm=config.IE_VM,
            storagedomain=config.EXPORT_STORAGE_NAME
    ):
        raise NetworkException(
            "Couldn't export VM %s to export Domain" % config.IE_VM
        )

    logger.info(
        "Remove %s from setup: %s", config.IE_VM, config.DC_NAME[0]
    )
    if not removeVm(positive=True, vm=config.IE_VM, stopVM='true'):
        raise NetworkException(
            "Couldn't remove imported VM %s" % config.IE_VM
        )

    logger.info(
        "Remove %s from setup: %s", config.IE_TEMPLATE, config.DC_NAME[0]
    )
    if not removeTemplate(
            positive=True, template=config.IE_TEMPLATE
    ):
        raise NetworkException(
            "Couldn't remove %s" % config.IE_TEMPLATE
        )


def teardown_package():
    """
    Cleans the environment
    """
    logger.info("Starting teardown process")
    if not config.GOLDEN_ENV:
        logger.info("Removing setup: %s", config.DC_NAME[0])
        if not cleanDataCenter(
                positive=True, datacenter=config.DC_NAME[0],
                vdc=config.VDC_HOST,
                vdc_password=config.VDC_ROOT_PASSWORD
        ):
            raise NetworkException(
                "Cannot remove setup: %s" % config.DC_NAME[0]
            )
    else:
        logger.info("Starting teardown in the GE")
        logger.info("Removing VM %s from Export Domain", config.IE_VM)
        if not removeVmFromExportDomain(
                True, vm=config.IE_VM,
                datacenter=config.DC_NAME[0],
                export_storagedomain=config.EXPORT_STORAGE_NAME
        ):
            logger.error("Couldn't remove VM %s form Export Domain" %
                         config.IE_VM)

        logger.info("Removing Template %s from Export Domain",
                    config.IE_TEMPLATE)
        if not removeTemplateFromExportDomain(
                True, template=config.IE_TEMPLATE,
                datacenter=config.DC_NAME[0],
                export_storagedomain=config.EXPORT_STORAGE_NAME
        ):
            logger.error("Couldn't remove template %s form Export Domain" %
                         config.IE_TEMPLATE)

        logger.info("Detach and deactivate Export Storage Domain")
        if not detach_and_deactivate_domain(
                datacenter_name=config.DC_NAME[0],
                domain=config.EXPORT_STORAGE_NAME
        ):
            logger.error(
                "Cannot detach and deactivate Export Storage"
            )

        logger.info("Remove all networks besides mgmt from DC/Cluster and "
                    "Host")
        if not remove_net_from_setup(
                host=config.VDS_HOSTS[0], auto_nics=[0], all_net=True,
                mgmt_network=config.MGMT_BRIDGE,
                data_center=config.DC_NAME[0]
        ):
            logger.error(
                "Cannot remove all networks from setup"
            )
        logger.info("Cleaning the GE setup")
        network_cleanup()
