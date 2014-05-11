"""
Port Mirroring test
"""

import logging

from art.rhevm_api.tests_lib.low_level.storagedomains import cleanDataCenter
from art.rhevm_api.tests_lib.low_level.vms import createVm, waitForIP,\
    updateNic
from art.rhevm_api.tests_lib.high_level.networks import prepareSetup,\
    createAndAttachNetworkSN
from art.rhevm_api.tests_lib.low_level.networks import addVnicProfile
from art.test_handler.exceptions import DataCenterException,\
    VMException, NetworkException
from art.rhevm_api.tests_lib.low_level.vms import addNic, waitForVMState
from art.rhevm_api.utils.test_utils import setPersistentNetwork,\
    configureTempStaticIp

logger = logging.getLogger("PortMirroring")

#################################################


def setup_package():
    """
    Prepare environment
    """
    import config
    logger.info("Create DC, Cluster, attach hosts and create VM and template")
    if not prepareSetup(hosts=','.join(config.HOSTS), cpuName=config.CPU_NAME,
                        username=config.HOSTS_USER,
                        password=','.join(config.HOSTS_PW),
                        datacenter=config.DC_NAME,
                        storageDomainName=config.STORAGE_DOMAIN_NAME,
                        storage_type=config.STORAGE_TYPE,
                        cluster=config.CLUSTER_NAME,
                        auto_nics=[config.HOST_NICS[0]],
                        lun_address=config.LUN_ADDRESS,
                        lun_target=config.LUN_TARGET,
                        luns=config.LUN, version=config.VERSION,
                        vm_password=config.VM_LINUX_PASSWORD,
                        nic=config.VM_NICS[0],
                        placement_host=config.HOSTS[0],
                        vmName=config.VM_NAME[0],
                        mgmt_network=config.MGMT_BRIDGE,
                        template_name=config.TEMPLATE_NAME):
        raise DataCenterException("Cannot create setup")

    # Setup networks and host NICs
    networkParams = {None: {'nic': config.BOND[0], 'mode': 1,
                            'slaves': [config.HOST_NICS[2],
                                       config.HOST_NICS[3]]},
                     config.VLAN_NETWORKS[0]: {'vlan_id': config.VLAN_ID[0],
                                               'nic': config.HOST_NICS[1],
                                               'required': 'false'},
                     config.VLAN_NETWORKS[1]: {'vlan_id': config.VLAN_ID[1],
                                               'nic': config.BOND[0],
                                               'required': 'false'}}

    logger.info("Create and attach networks")
    if not createAndAttachNetworkSN(data_center=config.DC_NAME,
                                    cluster=config.CLUSTER_NAME,
                                    host=config.HOSTS,
                                    network_dict=networkParams,
                                    auto_nics=config.HOST_NICS[:2]):
        raise NetworkException("Cannot create and attach networks")

    logger.info("Create VNIC profiles with port mirroring for mgmt network "
                "and sw1")
    for i, network in enumerate((config.MGMT_BRIDGE, config.VLAN_NETWORKS[0])):
        if not addVnicProfile(positive=True, name=config.VNIC_PROFILE[i],
                              cluster=config.CLUSTER_NAME,
                              network=network, port_mirroring=True):
            raise NetworkException('Failed to create VNIC profile with port '
                                   'mirroring.')

    logger.info("Unplug NIC1 on VM1")
    if not updateNic(True, config.VM_NAME[0], config.VM_NICS[0],
                     plugged=False):
        raise NetworkException("Failed to unplug NIC1 on VM1")

    logger.info("Updating NIC1 to profile with port mirroring")
    if not updateNic(True, config.VM_NAME[0], config.VM_NICS[0],
                     network=config.MGMT_BRIDGE,
                     vnic_profile=config.VNIC_PROFILE[0]):
        raise NetworkException("Failed to update NIC1 to profile with port "
                               "mirroring")

    logger.info("Plugin NIC1 on VM1")
    if not updateNic(True, config.VM_NAME[0], config.VM_NICS[0],
                     plugged=True):
        raise NetworkException("Failed to plug NIC 1 on VM1")

    logger.info("Create 4 more VMs from the template created by "
                "prepareSetup()")
    for vmName in config.VM_NAME[1:config.NUM_VMS]:
        if not createVm(True, vmName=vmName,
                        vmDescription='linux vm', cluster=config.CLUSTER_NAME,
                        start='True', template=config.TEMPLATE_NAME,
                        placement_host=config.HOSTS[0],
                        network=config.MGMT_BRIDGE):
            raise VMException('Failed to create %s from template' % vmName)

    logger.info("Add NICs to VMs. VM1 is handled separately since it needs "
                "port mirroring")
    if not waitForVMState(config.VM_NAME[0]):
        raise VMException('Failed to start %s.' % config.VM_NAME[0])

    if not addNic(True, vm=config.VM_NAME[0], name=config.VM_NICS[1],
                  interface=config.NIC_TYPE_VIRTIO,
                  network=config.VLAN_NETWORKS[0],
                  vnic_profile=config.VNIC_PROFILE[1]):
        raise VMException('Failed to add %s to %s.' %
                          (config.VM_NICS[1], config.VM_NAME[0]))

    if not addNic(True, vm=config.VM_NAME[0], name=config.VM_NICS[2],
                  interface=config.NIC_TYPE_VIRTIO,
                  network=config.VLAN_NETWORKS[1]):
        raise VMException('Failed to add nic to %s.' % config.VM_NAME[0])

    for vmName in config.VM_NAME[1:config.NUM_VMS]:
        if not waitForVMState(vmName):
            raise VMException('Failed to start %s' % vmName)

        for i in (0, 1):
            if not addNic(True, vm=vmName, name=config.VM_NICS[i + 1],
                          interface=config.NIC_TYPE_VIRTIO,
                          network=config.VLAN_NETWORKS[i]):
                raise VMException('Failed to add nic to %s' % vmName)

    logger.info("Configure IPs for each VM")
    for i, vm in enumerate(config.VM_NAME[:config.NUM_VMS]):
        logger.info('Getting mgmt network IP for %s.', vm)
        rc, out = waitForIP(vm)

        if not rc:
            raise VMException('Failed to get VM IP on mgmt network')

        logger.info("Update the list of mgmt network network IPs with IP the "
                    "VM got (DHCP)")
        MGMT_IP = out['ip']
        config.MGMT_IPS.append(MGMT_IP)

        logger.info("Configure static IPs for sw1 and sw2")
        for nicIndex, ip in enumerate((config.NET1_IPS[i], config.NET2_IPS[i]),
                                      start=1):
            if not configureTempStaticIp(MGMT_IP, config.VM_LINUX_USER,
                                         config.VM_LINUX_PASSWORD, ip,
                                         'eth%s' % nicIndex):
                raise VMException('Failed to configure static IP for sw%s.' %
                                  nicIndex)

        if not setPersistentNetwork(host=MGMT_IP,
                                    password=config.VM_LINUX_PASSWORD):
            raise VMException('Failed to set network configuration.')


def teardown_package():
    """
    Clean the environment
    """
    import config
    logger.info("Clean the environment")
    if not cleanDataCenter(positive=True, datacenter=config.DC_NAME):
        raise DataCenterException("Cannot remove setup")
