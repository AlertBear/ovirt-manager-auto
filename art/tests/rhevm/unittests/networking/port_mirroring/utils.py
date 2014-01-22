"""
Utilities used by port_mirroring_test
"""

from art.rhevm_api.tests_lib.high_level.networks import TrafficMonitor
from art.rhevm_api.tests_lib.low_level.vms import updateNic, stopVm, startVm,\
    migrateVm, getVmHost
from art.rhevm_api.utils.test_utils import sendICMP, configureTempStaticIp
from art.test_handler.exceptions import VMException

import config


def sendAndCaptureTraffic(srcVM, srcIP, dstIP,
                          listenVM=config.VM_NAME[0], nic='eth1',
                          expectTraffic=True, dupCheck=True):
    '''
    A function that sends ICMP traffic from 'srcIP' to 'dstIP' while capturing
    traffic on 'listeningVM' to check if mirroring is happening.
    **Parameters**:
        *  *srcVM* - mgmt netowrk IP of the VM to send ping from
        *  *srcIP* - IP to send ping form
        *  *dstIP* - IP to send ping to
        *  *listenVM* - name of the VM that will listen to the traffic
        *  *nic* - NIC to listen to traffic on
        *  *expectTraffic* - boolean to indicate if we expect to see the ping
                             traffic on the listening machine or not.
    **Return**: If expectTraffic is True: True if the ping traffic was sent and
                captured on the listening machine, False otherwise.
                If expectTraffic is False: True if the ping traffic wasn't
                captured, False otherwise.
    '''
    listenVmIndex = config.VM_NAME.index(listenVM)

    with TrafficMonitor(expectedRes=expectTraffic,
                        machine=config.MGMT_IPS[listenVmIndex],
                        user=config.VM_LINUX_USER,
                        password=config.VM_LINUX_PASSWORD,
                        nic=nic, src=srcIP, dst=dstIP, dupCheck=dupCheck,
                        protocol='icmp', numPackets=3, ) as monitor:
            monitor.addTask(sendICMP, host=srcVM, user=config.VM_LINUX_USER,
                            password=config.VM_LINUX_PASSWORD, ip=dstIP)
    return monitor.getResult()


def setPortMirroring(vm, nic, network, disableMirroring=False):
    '''
    Set port mirroring on a machine by shutting it down and bringing it back up
    to avoid unplugging NIC's and changing their order in the machine (eth1,
    eth2, etc)
    **Parameters**:
        *  *vm* - name of the VM
        *  *nic* - nic to enable/disable port mirroring on
        *  *network* - the name of the network the nic is connected to
        *  *disableMirroring* - boolean to indicate if we want to enable or
                                disable port mirroring (leave False to enable)
    '''
    if not stopVm(True, vm):
        raise VMException('Failed to stop VM')

    vnic_profile = network + ('' if disableMirroring else '_PM')
    if not updateNic(True, vm, nic, network=network,
                     vnic_profile=vnic_profile):
        raise VMException('Failed to update NIC port mirroring.')

    if not startVm(True, vm, wait_for_ip=True):
        raise VMException('Failed to start VM.')

    # Reconfiguring static ips
    vmIndex = config.VM_NAME.index(vm)

    for ip, nic in zip((config.NET1_IPS[vmIndex], config.NET2_IPS[vmIndex]),
                       ('eth1', 'eth2')):
            if not configureTempStaticIp(config.MGMT_IPS[vmIndex],
                                         config.VM_LINUX_USER,
                                         config.VM_LINUX_PASSWORD,
                                         ip=ip, nic=nic):
                raise VMException('Failed to reconfigure static ip on %s'
                                  % vm)


def returnVmsToOriginalHost():
    '''
    Returns all the VMs to original host they were on
    '''
    for vm in config.VM_NAME[:config.NUM_VMS]:
        if getVmHost(vm)[1]['vmHoster'] == config.HOSTS[1]:
            if not migrateVm(True, vm, config.HOSTS[0]):
                raise VMException('Failed to migrate vm %s' % vm)
