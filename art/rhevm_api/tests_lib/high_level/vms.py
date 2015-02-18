"""
High-level functions above virtual machines
"""

import logging
from concurrent.futures import ThreadPoolExecutor
from art.core_api import is_action
import art.rhevm_api.tests_lib.low_level.vms as vms
import art.rhevm_api.tests_lib.low_level.hosts as hosts
from art.rhevm_api.utils.test_utils import get_api, setPersistentNetwork
from art.test_handler import exceptions
from art.test_handler.settings import opts
import art.test_handler.exceptions as errors

LOGGER = logging.getLogger(__name__)
ENUMS = opts['elements_conf']['RHEVM Enums']

VM_API = get_api('vm', 'vms')

MB = 1024 ** 2
GB = 1024 ** 3
TIMEOUT = 120
ATTEMPTS = 600
INTERVAL = 2
MIGRATION_TIMEOUT = 300

ProvisionContext = vms.ProvisionContext


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
    if not vms.addDisk(True, vm_name, 5 * GB, storagedomain=storage_domain,
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


def restore_snapshot(vm_name, snap_description):
    """
    Description: Restores vm to given snapshot
    Parameters:
        * vm_name - name of the vm
        * snap_description - snapshot's description
    Throws:
        APITimeout - in case snapshot won't reach 'ok' status
        VMException - in case restoreSnapshot returns False or vm shutdown
                      fails
    """
    shutdown_vm_if_up(vm_name)
    vms.wait_for_vm_snapshots(vm_name, states=['ok'])
    if not vms.restoreSnapshot(True, vm=vm_name, description=snap_description):
        raise errors.VMException(
            "restoreSnapshot returned False for vm %s and snapshot %s" %
            (vm_name, snap_description))


def prepare_vm_for_rhel_template(vm_name, vm_password, image):
    """
    Prepare vm to create rhel with agent template from it
    **Author**: alukiano

    **Parameters**:
        * *vm_name* - vm to prepare
        * *vm_password* - vm connection password
        * *image* - image to install on vm
    **Returns**: True if method success, otherwise False
    """
    logging.info("Install image %s on vm %s", vm_name, image)
    try:
        if not vms.unattendedInstallation(True, vm_name, image):
            logging.error("Installation of image %s on vm %s failed",
                          image, vm_name)
            return False
        logging.info("Wait for vm %s ip", vm_name)
        status, result = vms.waitForIP(vm_name)
        if not status:
            logging.error("Vm %s still not have ip", vm_name)
            return False
    finally:
        ProvisionContext.clear()
    logging.info("Seal vm %s", vm_name)
    if not setPersistentNetwork(result.get('ip'), vm_password):
        logging.error("Failed to seal vm %s", vm_name)
        return False
    logging.info("Stop vm %s")
    if not vms.stopVm(True, vm_name):
        logging.error("Failed to stop vm %s", vm_name)
        return False
    return True


def get_vm_ip(vm_name, start_vm=True):
    """
    Start vm and return vm ip
    **Author**: alukiano

    **Parameters**:
        * *vm_name* - vm name
    **Returns**: vm ip as string
    """
    logging.info("Check vm %s status", vm_name)
    if vms.checkVmState(True, vm_name, ENUMS['vm_state_down']) and start_vm:
        logging.info("Start vm %s", vm_name)
        if not vms.startVm(True, vm_name):
            raise errors.VMException("Failed to start vm %s" %
                                     vm_name)
    logging.info("Wait until vm %s up and fetch ip", vm_name)
    status, result = vms.waitForIP(vm_name)
    if not status:
        raise errors.VMException("Vm %s still not have ip" %
                                 vm_name)
    return result.get('ip')


def start_vm_on_specific_host(vm, host, wait_for_ip=False):
    """
    Start vm on specific host
    :param vm: vm name
    :type vm: str
    :param host: host name in the engine
    :type host: str
    :param wait_for_ip: Wait for VM IP
    :type wait_for_ip: bool
    :return: True if vm started successfully on host otherwise False
    :rtype: bool
    """
    logging.info("Update vm %s to run on host %s", vm, host)
    if not vms.updateVm(True, vm, placement_host=host):
        return False

    logging.info("Start vm %s", vm)
    if vms.startVm(True, vm, wait_for_ip=wait_for_ip):
        vm_host = vms.getVmHost(vm)[1]["vmHoster"]
        if not host == vm_host:
            logging.error(
                "VM should start on %s instead off %s", host, vm_host)
            return False
    return True


def start_vms_on_specific_host(
        vm_list, max_workers, host,
        wait_for_status=ENUMS['vm_state_powering_up'],
        wait_for_ip=True):
    """
    Description: Starts all vms in vm_list. Throws an exception if it fails

    Parameters:
        * vm_list - List of vm names
        * max_workers - In how many threads should vms start
        * host name
        * wait_for_status - from ENUMS, to which state we wait for
        * wait_for_ip - Boolean, wait to get an ip from the vm
    """
    logging.info("Update vms %s to run on host %s", vm_list, host)
    for vm_name in vm_list:
        if not vms.updateVm(True, vm_name, placement_host=host):
            return False
    return vms.start_vms(vm_list, max_workers, wait_for_status, wait_for_ip)


def calculate_memory_for_memory_filter(hosts_list):
    """
    Calculate memory for vms to prevent more that one vm run on per host

    :param hosts_list list of hosts names
    :type hosts_list: list
    :returns: list of memory for vms from big to small
    :rtype: dict
    """
    mem_hosts = map(
        lambda host: hosts.get_host_free_memory(host), hosts_list
    )
    mem_hosts = map(
        lambda host_memory: (host_memory - GB) - host_memory % MB, mem_hosts
    )
    return sorted(mem_hosts, reverse=True)


def migrate_by_maintenance(
    vms_list, src_host, vm_os_type, vm_user, vm_password
):
    """
    Migrate VMs by setting host to maintenance

    :param vms_list: VMs to migrate
    :type vms_list: list
    :param src_host: Host to set to maintenance
    :type src_host: str
    :param vm_user: User for the VM machine
    :type vm_user: str
    :param vm_password: Password for the vm machine
    :type vm_password: str
    :param vm_os_type: Type of the OS of VM
    :type vm_os_type: str
    :return: True/False
    :rtype: bool
    """
    status = True
    LOGGER.info("Setting %s into maintenance", src_host)
    if not hosts.deactivateHost(positive=True, host=src_host):
        LOGGER.error("Failed to set %s into maintenance", src_host)
        return False

    LOGGER.info("Checking VMs after migration")
    if not check_vms_after_migration(
        vms_list=vms_list, src_host=src_host, vm_os_type=vm_os_type,
        vm_user=vm_user, vm_password=vm_password
    ):
        status = False

    LOGGER.info("Activating %s", src_host)
    if not hosts.activateHost(True, host=src_host):
        LOGGER.error("Couldn't activate host %s", src_host)
        return False
    return status


def migrate_by_nic_down(
    vms_list, src_host, password, nic, vm_os_type, vm_user, vm_password
):
    """
    Migrate VMs by set down required network on host

    :param vms_list: VMs to migrate
    :type vms_list: list
    :param src_host: Host to set the NIC down
    :type src_host: str
    :param password: Host password
    :type password: str
    :param nic: NIC name to put down
    :type nic: str
    :param vm_user: User for the VM machine
    :type vm_user: str
    :param vm_password: Password for the vm machine
    :type vm_password: str
    :param vm_os_type: Type of the OS of VM
    :type vm_os_type: str
    :return: True/False
    :rtype: bool
    """
    status = True
    LOGGER.info("Setting %s down on %s", nic, src_host)
    if not hosts.setHostToNonOperational(
        orig_host=src_host, host_password=password, nic=nic
    ):
        LOGGER.error(
            "Couldn't start migration by disconnecting the NIC with "
            "required network on it"
        )
        return False

    LOGGER.info("Checking VMs after migration")
    if not check_vms_after_migration(
        vms_list=vms_list, src_host=src_host, vm_os_type=vm_os_type,
        vm_user=vm_user, vm_password=vm_password
    ):
        status = False

    LOGGER.info(
        "Put the %s in the UP state and activate the %s", nic, src_host
    )
    ip = hosts.getHostIP(src_host)
    if not hosts.ifupNic(host=ip, root_password=password, nic=nic, wait=False):
        LOGGER.error("Couldn't put NIC %s in up state on %s", nic, src_host)
        return False

    LOGGER.info("Activating %s", src_host)
    if not hosts.activateHost(True, host=src_host):
        LOGGER.error("Couldn't activate host %s", src_host)
        return False
    return status


def check_vms_after_migration(
    vms_list, src_host, vm_os_type, vm_user, vm_password, dst_host=None
):
    """
    Check status of VMs after migration.
    Check connectivity and check that the VMs moved hosts

    :param vms_list: VMs that migrated
    :type vms_list: list
    :param src_host: Host from where VMs migrated
    :type src_host: str
    :param vm_user: User for the VM machine
    :type vm_user: str
    :param vm_password: Password for the vm machine
    :type vm_password: str
    :param vm_os_type: Type of the OS of VM
    :type vm_os_type: str
    :param dst_host: Destination host for migration
    :type dst_host: str
    :return: True/False
    :rtype: bool
    """
    vms_host = []
    for vm in vms_list:
        LOGGER.info("Waiting for %s to be UP after migration", vm)
        vm_obj = VM_API.find(vm)
        if not VM_API.waitForElemStatus(vm_obj, "up", MIGRATION_TIMEOUT):
            LOGGER.info("%s is not UP after migration", vm)
            return False

        LOGGER.info("Check %s connectivity after migration finished", vm)
        if not vms.checkVMConnectivity(
            True, vm=vm, osType=vm_os_type, attempt=ATTEMPTS,
            interval=INTERVAL, user=vm_user, password=vm_password,
            timeout=MIGRATION_TIMEOUT
        ):
            LOGGER.error("Check connectivity to %s failed", vm)
            return False

        LOGGER.info("Checking that the %s switched hosts", vm)
        vms_host.append(vms.getVmHost(vm)[1]["vmHoster"])

    if dst_host:
        LOGGER.info(
            "Checking that all VMs moved to destination host (%s)", dst_host
        )
        if not all([True if i == dst_host else False for i in vms_host]):
            LOGGER.error(
                "Not all VMs are located on destination host (%s)", dst_host
            )
            return False
    else:
        LOGGER.info(
            "Checking that all VMs are not located on the source host (%s)",
            src_host
        )
        if not all([True if i != src_host else False for i in vms_host]):
            LOGGER.error("Some VMs are located on source host (%s)", src_host)
            return False
    return True


def migrate_vms(
    vms_list, src_host, vm_os_type, vm_user, vm_password, dst_host=None,
    max_workers=None
):
    """
    Migrate VMs at once
    :param vms_list: VMs to migrate
    :type vms_list: list
    :param dst_host: Destination host for migration
    :type dst_host: str
    :param max_workers: Max workers for migrate VMs
    :type max_workers: int
    :param vm_user: User for the VM machine
    :type vm_user: str
    :param vm_password: Password for the vm machine
    :type vm_password: str
    :param vm_os_type: Type of the OS of VM
    :type vm_os_type: str
    :param src_host: Host from where the vm should migrate
    :type src_host: str
    :raises: VMException
    :return: True/False
    :rtype: bool
    """
    results = list()
    max_workers = len(vms_list) if not max_workers else max_workers
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        for machine in vms_list:
            LOGGER.info("migrating vm %s", machine)
            results.append(
                executor.submit(
                    vms.migrateVm, True, machine, dst_host, True, False)
            )
    for machine, res in zip(vms_list, results):
        if res.exception():
            LOGGER.error(
                "Got exception while migrate vm %s: %s",
                machine, res.exception()
            )
            raise res.exception()
        if not res.result():
            raise exceptions.VMException("Cannot migrate vm %s" % machine)

    LOGGER.info("Checking VMs after migration")
    if not check_vms_after_migration(
        vms_list=vms_list, src_host=src_host, vm_os_type=vm_os_type,
        vm_user=vm_user, vm_password=vm_password, dst_host=dst_host
    ):
        return False
    return True
