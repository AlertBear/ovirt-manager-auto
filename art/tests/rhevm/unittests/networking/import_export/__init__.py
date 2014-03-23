
"""
Import Export Test
"""

import logging
from art.rhevm_api.tests_lib.high_level.storagedomains import addNFSDomain,\
    detach_and_deactivate_domain, attach_and_activate_domain
from art.rhevm_api.tests_lib.low_level.storagedomains import cleanDataCenter
from art.rhevm_api.tests_lib.high_level.networks import prepareSetup, \
    createAndAttachNetworkSN
from art.rhevm_api.tests_lib.low_level.templates import createTemplate,\
    exportTemplate, removeTemplate
from art.rhevm_api.tests_lib.low_level.vms import waitForVmsStates, stopVm,\
    addNic, exportVm, waitForIP, removeVm
from art.rhevm_api.utils.test_utils import setPersistentNetwork
from art.test_handler.exceptions import NetworkException

logger = logging.getLogger("ImportExport")

#################################################


def setup_package():
    """
    Prepare environment
    """
    import config
    logger.info("Creating two data centers, clusters, adding host and "
                "storage to each")
    for i in range(2):
        if not prepareSetup(hosts=config.HOSTS[i],
                            cpuName=config.CPU_NAME,
                            username=config.HOSTS_USER,
                            password=config.HOSTS_PW,
                            datacenter=config.DC_NAME[i],
                            storageDomainName=config.STORAGE_NAME[i],
                            storage_type=config.STORAGE_TYPE,
                            cluster=config.CLUSTER_NAME[i],
                            lun_address=config.LUN_ADDRESS[i],
                            lun_target=config.LUN_TARGET[i],
                            luns=config.LUN[i], version=config.VERSION[i],
                            vmName=config.VM_NAME[i],
                            vm_password=config.VMS_LINUX_PW,
                            mgmt_network=config.MGMT_BRIDGE,
                            auto_nics=[config.HOST_NICS[0]]):
            raise NetworkException("Cannot create setup %s" % i)

    logger.info("Adding export domain (NFS) to %s", config.DC_NAME[0])
    if not addNFSDomain(host=config.HOSTS[0], storage="Export",
                        data_center=config.DC_NAME[0],
                        address=config.EXPORT_STORAGE_ADDRESS,
                        path=config.EXPORT_STORAGE_PATH,
                        sd_type=config.EXPORT_TYPE):
        raise NetworkException("Cannot create and attach Export Storage "
                               "Domain to %s", config.DC_NAME[0])

    local_dict = {config.NETWORKS[0]: {'nic': config.HOST_NICS[1],
                                       'required': 'false'},
                  config.NETWORKS[1]: {'mtu': config.MTU[0],
                                       'nic': config.HOST_NICS[2],
                                       'required': 'false'},
                  config.NETWORKS[2]: {'vlan_id': config.VLAN_ID[0],
                                       'nic': config.HOST_NICS[3],
                                       'required': 'false'}}

    logger.info("Attaching bridged, MTU and VLAN networks to hosts")
    for i in range(2):
        if not createAndAttachNetworkSN(data_center=config.DC_NAME[i],
                                        cluster=config.CLUSTER_NAME[i],
                                        host=config.HOSTS[i],
                                        network_dict=local_dict,
                                        auto_nics=[config.HOST_NICS[0],
                                                   config.HOST_NICS[3]]):
            raise NetworkException("Cannot create and attach networks to "
                                   "setup %s", i)

    for i in range(2):
        logger.info("Get IP for %s", config.VM_NAME[i])
        ip = waitForIP(config.VM_NAME[i])[1]["ip"]
        if not ip:
            raise NetworkException("Failed to get IP from %s",
                                   config.VM_NAME[i])

        logger.info("setPersistentNetwork for %s", config.VM_NAME[i])
        if not setPersistentNetwork(host=ip, password=config.VMS_LINUX_PW):
            raise NetworkException("Failed to setPersistentNetwork on %s",
                                   config.VM_NAME[i])

        logger.info("Stopping VMs to create template from them")
        if not stopVm(positive=True, vm=config.VM_NAME[i]):
            raise NetworkException("Cannot stop VM %s" % config.VM_NAME[i])

        if not waitForVmsStates(True, names=config.VM_NAME[i], states='down'):
            raise NetworkException("VM  %s status is not down in the "
                                   "predefined timeout" % config.VM_NAME[i])

    logger.info("Adding NICs to VMs and creating Templates from those VMs")
    net_list = ["sw1", "sw2", "sw3", None]
    for i in range(2):
        for index, net in enumerate(net_list):
            if not addNic(True, config.VM_NAME[i],
                          name=config.NIC_NAME[index],
                          network=net, vnic_profile=net):
                raise NetworkException("Cannot add vnic_profile %s to VM" %
                                       net)

        if not createTemplate(True, vm=config.VM_NAME[i],
                              cluster=config.CLUSTER_NAME[i],
                              name=config.TEMPLATE_NAME[i]):
            raise NetworkException("Cannot create template %s" %
                                   config.TEMPLATE_NAME[i])

    logger.info("Export VM and template to Export domain")
    if not exportVm(positive=True, vm=config.VM_NAME[0],
                    storagedomain="Export"):
        raise NetworkException("Couldn't export VM %s to export Domain" %
                               config.VM_NAME[0])

    if not exportTemplate(positive=True,
                          template=config.TEMPLATE_NAME[0],
                          storagedomain="Export"):
        raise NetworkException("Couldn't export Template to export Domain")

    logger.info("Deactivate and detach Export storage domain from %s",
                config.DC_NAME[0])
    if not detach_and_deactivate_domain(datacenter=config.DC_NAME[0],
                                        domain="Export"):
        raise NetworkException("Couldn't detach and deactivate Export "
                               "storage domain from %s", config.DC_NAME[0])

    logger.info("Attach and activate Export storage domain on %s",
                config.DC_NAME[1])
    if not attach_and_activate_domain(datacenter=config.DC_NAME[1],
                                      domain="Export"):
        raise NetworkException("Couldn't reattach and reactivate Export "
                               "storage domain on %s", config.DC_NAME[1])

    logger.info("Export %s and %s to Export domain", config.VM_NAME[1],
                config.TEMPLATE_NAME[1])
    if not exportVm(positive=True, vm=config.VM_NAME[1],
                    storagedomain="Export"):
        raise NetworkException("Couldn't export VM %s to export Domain" %
                               config.VM_NAME[1])

    if not exportTemplate(positive=True,
                          template=config.TEMPLATE_NAME[1],
                          storagedomain="Export"):
        raise NetworkException("Couldn't export %s to export Domain",
                               config.TEMPLATE_NAME[1])

    logger.info("Removing setup: %s", config.DC_NAME[0])
    if not cleanDataCenter(positive=True, datacenter=config.DC_NAME[0]):
        raise NetworkException("Cannot remove setup: %s", config.DC_NAME[0])

    logger.info("Remove %s from setup: %s", config.VM_NAME[1],
                config.DC_NAME[1])
    if not removeVm(positive=True, vm=config.VM_NAME[1], stopVM='true'):
        raise NetworkException("Couldn't remove imported VM %s" %
                               config.VM_NAME[1])

    logger.info("Remove %s from setup: %s", config.TEMPLATE_NAME[1],
                config.DC_NAME[1])
    if not removeTemplate(positive=True,
                          template=config.TEMPLATE_NAME[1]):
        raise NetworkException("Couldn't remove %s", config.TEMPLATE_NAME[1])


def teardown_package():
    """
    Cleans the environment
    """
    import config
    if not cleanDataCenter(positive=True, datacenter=config.DC_NAME[1]):
        raise NetworkException("Cannot remove setup")
