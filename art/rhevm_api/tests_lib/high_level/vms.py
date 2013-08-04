"""
High-level functions above virtual machines
"""

import logging

from art.core_api import is_action
import art.rhevm_api.tests_lib.low_level.vms as vms
import art.rhevm_api.tests_lib.low_level.hosts as hosts
from art.rhevm_api.utils.test_utils import get_api
from art.test_handler.settings import opts
import art.test_handler.exceptions as errors

LOGGER = logging.getLogger(__name__)
ENUMS = opts['elements_conf']['RHEVM Enums']

VM_API = get_api('vm', 'vms')

GB = 1024**3
TIMEOUT = 120
ATTEMPTS = 600
INTERVAL = 2


@is_action()
def add_disk_to_machine(vm_name, interface, format_, sparse, storage_domain,
                        **kwargs):
    """
    Description: Adds disk to a running VM by shuting VM down, adding disk
    and turing it on again
    Params:
        * vm_name - name of the VM
        * interface - disk interface type (ide, virtio)
        * format_ - disk type (raw, cow)
        * sparse - whether disk should be sparse
        * host - hsm or spm
        * storage_domain - on which storage domain should be disk placed
    """
    start = False
    vm_obj = VM_API.find(vm_name)
    if vm_obj.status.state == ENUMS['vm_state_up']:
        start = True
        LOGGER.info("Shutting down vm %s to add disk", vm_name)
        if not vms.shutdownVm(True, vm_name):
            raise errors.VMException("Shutdown of vm %s failed" % vm_name)
    vms.waitForVMState(vm_name, state=ENUMS['vm_state_down'], timeout=60)

    LOGGER.info("AddDisk to vm %s", vm_name)
    if not vms.addDisk(True, vm_name, 5*GB, storagedomain=storage_domain,
                       format=format_, interface=interface, sparse=sparse,
                       **kwargs):
        raise errors.VMException("addDisk to vm %s failed" % vm_name)

    vm_obj = VM_API.find(vm_name)
    if start and vm_obj.status.state == ENUMS['vm_state_down'] and \
            not vms.startVm(True, vm_name, wait_for_ip=True):
        raise errors.VMException("startVm of vm %s failed" % vm_name)


@is_action()
def shutdown_vm_if_up(vm_name):
    """
    Description: Shutdowns vm if it's in up status
    Parameters:
        * vm_name - name of the vm
    """
    vm_obj = VM_API.find(vm_name)
    if vm_obj.status.state == ENUMS['vm_state_up'] and\
            not vms.shutdownVm(True, vm_name):
        raise errors.VMException("Shutdown of vm %s failed" % vm_name)
    return vms.waitForVMState(vm_name, state=ENUMS['vm_state_down'])


def check_vm_migration(vm_names, orig_host, vm_user, host_password,
                       vm_password, os_type, dest_host=None, nic=None):

    '''
        Function that tests migration in 2 scenarios
        1) By turning down NIC with required network
        2) By calling migrateVm function
        **Author**: gcheresh
        **Parameters**:
            *  *vm_names* - vm/vms to be migrated
            *  *orig_host* - host from where the vm should migrate
            *  *dest_host* - host where the vm should be migrated to
            *  *vm_user* - user for the VM machine
            *  *host_password* - password for the host machine
            *  *vm_password* - password for the vm machine
            *  *os_type* - type of the OS of VM (for example 'rhel')
            *  *nic* - NIC with required network.
                Will start the migration when turned down
        **Returns**: True if vm migration succeeded, otherwise False
    '''

    # Anyone using this function should take care of checking that all the VMs
    # are located on the same physical host before the test

    #support vm_names parameter received as list or string
    vm_names = [vm_names] if isinstance(vm_names, basestring) else vm_names

    # causes VM migration by turning down NIC with required network
    if nic:
        LOGGER.info("Turn down the required Network NIC to start migration")
        if not hosts.ifdownNic(host=orig_host, root_password=host_password,
                               nic=nic):
            LOGGER.error("Coudn't disconnect the NIC %s ", nic)
            return False

        LOGGER.info("Check that Host has become NON_OPERATIONAL")
        if not hosts.waitForHostsStates(True, names=orig_host,
                                        states='nonoperational',
                                        timeout=TIMEOUT):
            LOGGER.error("Host %s is not in non-operational state", orig_host)
            return False

        LOGGER.info("Wait till VM/VMs come UP after migration")
        for vm in vm_names:
            if not vms.waitForVMState(vm=vm, state='up', sleep=INTERVAL,
                                      timeout=TIMEOUT):
                LOGGER.error("VM %s is not up after migration", vm)
                return False

        LOGGER.info("Checking that the VM switched hosts")
        for vm in vm_names:
            rc, out = vms.getVmHost(vm)
            # if specific host was selected as destination
            if dest_host:
                if out['vmHoster'] != dest_host:
                    LOGGER.error("VM %s isn't located on dest host after "
                                 "migration", vm)
                    return False

            # if no specific host was selected as destination
            else:
                if out['vmHoster'] == orig_host:
                    LOGGER.error("VM %s is located on orignal host after "
                                 "migration", vm)
                    return False

        # Turn on the NIC with required network and activate Host.
        # Return the state of the original Host as before the migration
        LOGGER.info("Put the NIC in the UP state and activate the Host")
        if not hosts.ifupNic(host=orig_host, root_password=host_password,
                             nic=nic, wait=False):
            LOGGER.error("Couldn't put NIC %s in up state", nic)
            return False

        if not hosts.activateHost(True, host=orig_host):
            LOGGER.error("Couldn't activate host %s", orig_host)
            return False

    # call migrateVm function to migrate the VMs one by one
    else:
        for vm in vm_names:
            if not vms.migrateVm(True, vm=vm, host=dest_host):
                LOGGER.error("Couldn't migrate VM %s", vm)
                return False

    #check VM connectivity for both cases
    LOGGER.info("Check VM connectivity after migration finished")
    for vm in vm_names:
        if not vms.checkVMConnectivity(True, vm=vm, osType=os_type,
                                       attempt=ATTEMPTS, interval=INTERVAL,
                                       user=vm_user, password=vm_password):
            LOGGER.error("Check connectivity to %s failed", vm)
            return False
    return True
