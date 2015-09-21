
"""
Import Export Test
"""

import logging
import art.rhevm_api.utils.test_utils as test_utils
import rhevmtests.networking.config as config
import rhevmtests.networking as networking
import art.rhevm_api.tests_lib.low_level.storagedomains as ll_storagedomains
import art.rhevm_api.tests_lib.high_level.vms as hl_vms
import art.rhevm_api.tests_lib.high_level.networks as hl_networks
import art.rhevm_api.tests_lib.low_level.templates as ll_templates
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import art.test_handler.exceptions as exceptions

logger = logging.getLogger("Import_Export_Init")

#################################################


def setup_package():
    """
    Prepare environment
    """

    logger.info("Cleaning the GE setup")
    networking.network_cleanup()
    logger.info("Creating new VM %s", config.IE_VM)
    sd_name = ll_storagedomains.getStorageDomainNamesForType(
        datacenter_name=config.DC_NAME[0],
        storage_type=config.STORAGE_TYPE
    )[0]
    glance_name = config.EXTERNAL_PROVIDERS[config.GLANCE]
    if not hl_vms.create_vm_using_glance_image(
            vmName=config.IE_VM, vmDescription="linux vm",
            cluster=config.CLUSTER_NAME[0], nic=config.NIC_NAME[0],
            storageDomainName=sd_name, network=config.MGMT_BRIDGE,
            glance_storage_domain_name=glance_name,
            glance_image=config.GOLDEN_GLANCE_IMAGE

    ):
        raise exceptions.NetworkException(
            "Cannot create VM %s" % config.IE_VM
        )
    logger.info("Starting %s", config.IE_VM)
    if not ll_vms.startVm(True, config.IE_VM):
        raise exceptions.NetworkException(
            "Failed to start %s" % config.IE_VM
        )
    logger.info("Creating new Template %s", config.IE_TEMPLATE)
    ip_addr = ll_vms.waitForIP(config.IE_VM)[1]["ip"]
    if not test_utils.setPersistentNetwork(
            host=ip_addr, password=config.VMS_LINUX_PW
    ):
        raise exceptions.NetworkException("Set persistent network failed")
    if not ll_vms.stopVm(True, vm=config.IE_VM):
        raise exceptions.NetworkException(
            "Cannot stop vm %s" % config.IE_VM
        )
    if not ll_templates.createTemplate(
            True, vm=config.IE_VM, cluster=config.CLUSTER_NAME[0],
            name=config.IE_TEMPLATE
    ):
        raise exceptions.NetworkException(
            "Cannot create template %s" % config.IE_TEMPLATE
        )

    local_dict = {
        config.NETWORKS[0]: {"nic": 1, "required": "false"},
        config.NETWORKS[1]: {
            "mtu": config.MTU[0], "nic": 2, "required": "false"
        },
        config.NETWORKS[2]: {
            "vlan_id": config.VLAN_ID[0], "nic": 3, "required": "false"
        }
    }

    logger.info("Attaching bridged, MTU and VLAN networks to host")
    if not hl_networks.createAndAttachNetworkSN(
            data_center=config.DC_NAME[0], cluster=config.CLUSTER_NAME[0],
            host=config.VDS_HOSTS[0], network_dict=local_dict, auto_nics=[0, 3]
    ):
        raise exceptions.NetworkException(
            "Cannot create and attach networks to setup"
        )

    logger.info("Adding 4 NICs to new VM and Template ")
    net_list = config.NETWORKS[:3] + [None]
    for index, net in enumerate(net_list):
        if not ll_vms.addNic(
                True, config.IE_VM, name=config.NIC_NAME[index + 1],
                network=net, vnic_profile=net
        ):
            raise exceptions.NetworkException(
                "Cannot add vnic_profile %s to VM %s" % (net, config.IE_VM)
            )

        if not ll_templates.addTemplateNic(
                True, config.IE_TEMPLATE, name=config.NIC_NAME[index + 1],
                data_center=config.DC_NAME[0], network=net
        ):
            raise exceptions.NetworkException(
                "Cannot add NIC to Template %s" % config.IE_TEMPLATE
            )

    logger.info(
        "Export %s to Export domain", config.IE_TEMPLATE
    )
    if not ll_templates.exportTemplate(
            positive=True, template=config.IE_TEMPLATE,
            storagedomain=config.EXPORT_STORAGE_NAME
    ):
        raise exceptions.NetworkException(
            "Couldn't export Template %s to export Domain" % config.IE_TEMPLATE
        )

    logger.info("Export %s to Export domain", config.IE_VM)
    if not ll_vms.exportVm(
            positive=True, vm=config.IE_VM,
            storagedomain=config.EXPORT_STORAGE_NAME
    ):
        raise exceptions.NetworkException(
            "Couldn't export VM %s to export Domain" % config.IE_VM
        )

    logger.info(
        "Remove %s from setup: %s", config.IE_VM, config.DC_NAME[0]
    )
    if not ll_vms.removeVm(positive=True, vm=config.IE_VM, stopVM="true"):
        raise exceptions.NetworkException(
            "Couldn't remove imported VM %s" % config.IE_VM
        )

    logger.info(
        "Remove %s from setup: %s", config.IE_TEMPLATE, config.DC_NAME[0]
    )
    if not ll_templates.removeTemplate(
            positive=True, template=config.IE_TEMPLATE
    ):
        raise exceptions.NetworkException(
            "Couldn't remove %s" % config.IE_TEMPLATE
        )


def teardown_package():
    """
    Cleans the environment
    """
    logger.info("Starting teardown process")
    logger.info("Removing VM %s from Export Domain", config.IE_VM)
    if not ll_vms.removeVmFromExportDomain(
            True, vm=config.IE_VM,
            datacenter=config.DC_NAME[0],
            export_storagedomain=config.EXPORT_STORAGE_NAME
    ):
        logger.error(
            "Couldn't remove VM %s form Export Domain", config.IE_VM
        )

    logger.info("Removing Template %s from Export Domain",
                config.IE_TEMPLATE)
    if not ll_templates.removeTemplateFromExportDomain(
            True, template=config.IE_TEMPLATE,
            datacenter=config.DC_NAME[0],
            export_storagedomain=config.EXPORT_STORAGE_NAME
    ):
        logger.error(
            "Couldn't remove template %s form Export Domain",
            config.IE_TEMPLATE
        )

    logger.info(
        "Remove all networks besides MGMT from DC/Cluster and Host")
    if not hl_networks.remove_net_from_setup(
            host=config.HOSTS[0], all_net=True,
            mgmt_network=config.MGMT_BRIDGE,
            data_center=config.DC_NAME[0]
    ):
        logger.error(
            "Cannot remove all networks from setup"
        )
