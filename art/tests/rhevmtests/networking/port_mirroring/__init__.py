"""
Port Mirroring test
"""

import logging
from rhevmtests.networking import config
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
    configureTempStaticIp, toggleServiceOnHost

logger = logging.getLogger("PortMirroring")

#################################################


def setup_package():
    """
    Prepare environment
    """

    logger.info("Create DC, Cluster, attach hosts and create VM and template")
    if not prepareSetup(hosts=",".join(config.HOSTS), cpuName=config.CPU_NAME,
                        username=config.HOSTS_USER,
                        password=config.HOSTS_PW,
                        datacenter=config.DC_NAME[0],
                        storageDomainName=config.STORAGE_NAME[0],
                        storage_type=config.STORAGE_TYPE,
                        cluster=config.CLUSTER_NAME[0],
                        auto_nics=[config.HOST_NICS[0]],
                        lun_address=config.LUN_ADDRESS[0],
                        lun_target=config.LUN_TARGET[0],
                        luns=config.LUN[0], version=config.COMP_VERSION,
                        vm_password=config.VMS_LINUX_PW,
                        placement_host=config.HOSTS[0],
                        vmName=config.VM_NAME[0],
                        mgmt_network=config.MGMT_BRIDGE,
                        vm_network=config.MGMT_BRIDGE,
                        template_name=config.TEMPLATE_NAME[0]):
        raise DataCenterException("Cannot create setup")

    # Setup networks and host NICs
    network_params = {None: {'nic': config.BOND[0], 'mode': 1,
                             'slaves': [config.HOST_NICS[2],
                                        config.HOST_NICS[3]]},
                      config.VLAN_NETWORKS[0]: {'vlan_id': config.VLAN_ID[0],
                                                'nic': config.HOST_NICS[1],
                                                'required': 'false'},
                      config.VLAN_NETWORKS[1]: {'vlan_id': config.VLAN_ID[1],
                                                'nic': config.BOND[0],
                                                'required': 'false'}}

    logger.info("Create and attach networks")
    if not createAndAttachNetworkSN(data_center=config.DC_NAME[0],
                                    cluster=config.CLUSTER_NAME[0],
                                    host=config.HOSTS,
                                    network_dict=network_params,
                                    auto_nics=config.HOST_NICS[:2]):
        raise NetworkException("Cannot create and attach networks")

    logger.info("Create VNIC profiles with port mirroring for mgmt network "
                "and sw1")
    for i, network in enumerate((config.MGMT_BRIDGE, config.VLAN_NETWORKS[0])):
        if not addVnicProfile(positive=True, name=config.PM_VNIC_PROFILE[i],
                              cluster=config.CLUSTER_NAME[0],
                              network=network, port_mirroring=True):
            raise NetworkException('Failed to create VNIC profile with port '
                                   'mirroring.')

    if not updateNic(True, config.VM_NAME[0], config.NIC_NAME[0],
                     plugged=False):
        raise NetworkException("Failed to unplug NIC1 on VM1")

    logger.info("Updating NIC1 to profile with port mirroring")
    if not updateNic(True, config.VM_NAME[0], config.NIC_NAME[0],
                     network=config.MGMT_BRIDGE,
                     vnic_profile=config.PM_VNIC_PROFILE[0]):
        raise NetworkException("Failed to update NIC1 to profile with port "
                               "mirroring")

    logger.info("Plugin NIC1 on VM1")
    if not updateNic(True, config.VM_NAME[0], config.NIC_NAME[0],
                     plugged=True):
        raise NetworkException("Failed to plug NIC 1 on VM1")

    if not addNic(True, vm=config.VM_NAME[0], name=config.NIC_NAME[1],
                  interface=config.NIC_TYPE_VIRTIO,
                  network=config.VLAN_NETWORKS[0],
                  vnic_profile=config.PM_VNIC_PROFILE[1]):
        raise VMException('Failed to add %s to %s.' %
                          (config.NIC_NAME[1], config.VM_NAME[0]))

    if not addNic(True, vm=config.VM_NAME[0], name=config.NIC_NAME[2],
                  interface=config.NIC_TYPE_VIRTIO,
                  network=config.VLAN_NETWORKS[1]):
        raise VMException('Failed to add nic to %s.' % config.VM_NAME[0])

    logger.info("Create 4 more VMs from the template created by "
                "prepareSetup()")
    for vmName in config.VM_NAME[1:config.NUM_VMS]:
        if not createVm(True, vmName=vmName,
                        vmDescription='linux vm',
                        cluster=config.CLUSTER_NAME[0],
                        start='True', template=config.TEMPLATE_NAME[0],
                        placement_host=config.HOSTS[0],
                        network=config.MGMT_BRIDGE):
            raise VMException('Failed to create %s from template' % vmName)

    for vmName in config.VM_NAME[1:config.NUM_VMS]:
        logger.info("Add NICs to VMs. VM1 is handled separately since it "
                    "needs port mirroring")
        if not waitForVMState(vmName):
            raise VMException('Failed to start %s.' % config.VM_NAME[0])

        for i in (0, 1):
            if not addNic(True, vm=vmName, name=config.NIC_NAME[i + 1],
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
        local_mgmt_ip = out['ip']
        config.MGMT_IPS.append(local_mgmt_ip)

        logger.info("Configure static IPs for sw1 and sw2")
        for nicIndex, ip in enumerate((config.NET1_IPS[i], config.NET2_IPS[i]),
                                      start=1):
            if not configureTempStaticIp(local_mgmt_ip, config.VMS_LINUX_USER,
                                         config.VMS_LINUX_PW, ip,
                                         'eth%s' % nicIndex):
                raise VMException('Failed to configure static IP for sw%s.' %
                                  nicIndex)

        if not setPersistentNetwork(host=local_mgmt_ip,
                                    password=config.VMS_LINUX_PW):
            raise VMException('Failed to set network configuration.')

    for host in config.HOSTS:
        stop_firewall = toggleServiceOnHost(positive=True,
                                            host=host,
                                            user=config.HOSTS_USER,
                                            password=config.HOSTS_PW,
                                            service=config.FIREWALL_SRV,
                                            action="STOP")
        if not stop_firewall:
            raise NetworkException("Cannot stop Firewall service")


def teardown_package():
    """
    Clean the environment
    """
    logger.info("Clean the environment")
    if not cleanDataCenter(positive=True, datacenter=config.DC_NAME[0],
                           vdc=config.VDC_HOST,
                           vdc_password=config.VDC_ROOT_PASSWORD):
        raise DataCenterException("Cannot remove setup")
