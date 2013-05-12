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

    if not prepareSetup(hosts=','.join(config.HOSTS), cpuName=config.CPU_NAME,
                        username=config.HOSTS_USER,
                        password=','.join(config.HOSTS_PW),
                        datacenter=config.DC_NAME,
                        storageDomainName=config.STORAGE_DOMAIN_NAME,
                        storage_type=config.STORAGE_TYPE,
                        cluster=config.CLUSTER_NAME,
                        lun_address=config.LUN_ADDRESS,
                        lun_target=config.LUN_TARGET,
                        luns=config.LUN, version=config.VERSION,
                        cobblerAddress=config.COBBLER_ADDRESS,
                        cobblerUser=config.COBBLER_USER,
                        cobblerPasswd=config.COBBLER_PASSWORD,
                        vm_password=config.VM_LINUX_PASSWORD,
                        nic=config.VM_NICS[0],
                        placement_host=config.HOSTS[0],
                        vmName=config.VM_NAME[0],
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

    if not createAndAttachNetworkSN(data_center=config.DC_NAME,
                                    cluster=config.CLUSTER_NAME,
                                    host=config.HOSTS,
                                    network_dict=networkParams,
                                    auto_nics=config.HOST_NICS[:2]):
        raise NetworkException("Cannot create and attach networks")

    # Create VNIC profiles with port mirroring for rhevm and sw1
    for i, network in enumerate((config.MGMT_BRIDGE, config.VLAN_NETWORKS[0])):
        if not addVnicProfile(positive=True, name=config.VNIC_PROFILE[i],
                              cluster=config.CLUSTER_NAME,
                              network=network, port_mirroring=True):
            raise NetworkException('Failed to create VNIC profile with port '
                                   'mirroring.')

    # Update NIC1 on VM1 to a profile with port mirroring
    if not updateNic(True, config.VM_NAME[0], config.VM_NICS[0],
                     network=config.MGMT_BRIDGE,
                     vnic_profile=config.VNIC_PROFILE[0], plugged=False):
        raise NetworkException('Failed to update VM1 nic1 to a profile with '
                               'port mirroring.')
    if not updateNic(True, config.VM_NAME[0], config.VM_NICS[0], plugged=True):
        raise NetworkException('Failed to plug VM1 nic1 after update.')

    # Create 4 more VMs from the template created by prepareSetup()
    for vmName in config.VM_NAME[1:config.NUM_VMS]:
        if not createVm(True, vmName=vmName,
                        vmDescription='linux vm', cluster=config.CLUSTER_NAME,
                        start='True', template=config.TEMPLATE_NAME,
                        placement_host=config.HOSTS[0]):
            raise VMException('Failed to create %s from template' % vmName)

    # Add NICs to VMs. VM1 is handled separately since it needs port
    # mirroring
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

    # Configure IPs for each VM
    for i, vm in enumerate(config.VM_NAME[:config.NUM_VMS]):
        logger.info('Getting rhevm IP for %s.', vm)
        rc, out = waitForIP(vm)

        if not rc:
            raise VMException('Failed to get VM IP on rhevm')

        # Update the list of rhevm network IPs with IP the VM got (DHCP)
        rhevmIP = out['ip']
        config.RHEVM_IPS.append(rhevmIP)

        # Configure static IPs for sw1 and sw2
        for nicIndex, ip in enumerate((config.NET1_IPS[i], config.NET2_IPS[i]),
                                      start=1):
            if not configureTempStaticIp(rhevmIP, config.VM_LINUX_USER,
                                         config.VM_LINUX_PASSWORD, ip,
                                         'eth%s' % nicIndex):
                raise VMException('Failed to configure static IP for sw%s.' %
                                  nicIndex)

        if not setPersistentNetwork(host=rhevmIP,
                                    password=config.VM_LINUX_PASSWORD):
            raise VMException('Failed to set network configuration.')


def teardown_package():
    """
    Clean the environment
    """
    import config

    if not cleanDataCenter(positive=True, datacenter=config.DC_NAME):
        raise DataCenterException("Cannot remove setup")
