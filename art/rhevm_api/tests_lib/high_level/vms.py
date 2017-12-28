#!/usr/bin/env python

"""
High-level functions above virtual machines
"""
import logging
import shlex
import urllib
from concurrent.futures import ThreadPoolExecutor
from art.core_api.timeout import TimeoutingSampler
from art.rhevm_api.tests_lib.low_level import (
    disks as disks,
    general as ll_general,
    hosts as hosts,
    storagedomains as storagedomains,
    vms as vms
)
import art.rhevm_api.tests_lib.high_level.hosts as hl_hosts
import art.test_handler.exceptions as errors
from art.rhevm_api.utils.name2ip import LookUpVMIpByName
from art.core_api.apis_exceptions import APITimeout
from art.rhevm_api import resources
from art.rhevm_api.utils.test_utils import getStat, get_api
from art.test_handler import exceptions
from art.test_handler.settings import ART_CONFIG
from time import sleep


logger = logging.getLogger("art.hl_lib.vms")
ENUMS = ART_CONFIG['elements_conf']['RHEVM Enums']
CLUSTER_API = get_api('cluster', 'clusters')

VM_API = get_api('vm', 'vms')
KB = 1024
MB = 1024 ** 2
GB = 1024 ** 3
TIMEOUT = 120
ATTEMPTS = 600
INTERVAL = 2
SLEEP_TIME = 30
MIGRATION_TIMEOUT = 300
WGT_INSTALL_TIMEOUT = 600
CHECK_MEMORY_COMMAND = "free -m | grep Mem | awk '{ print $2 }'"
SLEEP_TIME_HOTPLUG_DEVICE = 6
SLEEP_TIME_HOT_UNPLUG_DEVICE = 20


def get_vm_ip(vm_name, start_vm=True):
    """
    Start VM and return VM IP

    __Author__: alukiano

    Args:
        vm_name (str): vm name
        start_vm (bool): Start the VM before get IP

    Raises:
        VMException: VM didn't received an IP

    Returns:
        str: VM IP
    """
    logging.info("Check vm %s status", vm_name)
    if start_vm and vms.checkVmState(True, vm_name, ENUMS['vm_state_down']):
        logging.info("Start vm %s", vm_name)
        if not vms.startVm(True, vm_name):
            raise errors.VMException("Failed to start vm %s" % vm_name)

    logging.info("Wait until vm %s is up and fetch ip", vm_name)
    status, result = vms.wait_for_vm_ip(vm_name)
    if not status:
        raise errors.VMException("Vm %s didn't get IP" % vm_name)

    return result.get('ip')


def run_vm_once_specific_host(vm, host, wait_for_up_status=False):
    """
    Run VM once on specific host

    Args:
        vm (str): VM name
        host (str): Host name
        wait_for_up_status (bool): Wait for VM to be UP

    Returns:
        bool: True if action succeeded, False otherwise
    """
    logger.info("Check if %s is up", host)
    host_status = hosts.get_host_status(host)
    if not host_status == ENUMS["host_state_up"]:
        logger.error("%s status is %s, cannot run VM", host, host_status)
        return False

    if not vms.runVmOnce(positive=True, vm=vm, host=host):
        return False

    if wait_for_up_status:
        vms.wait_for_vm_states(vm_name=vm)

    logger.info("Check that %s was started on host %s", vm, host)
    vm_host = vms.get_vm_host(vm_name=vm)
    if not vm_host:
        return False
    if not host == vm_host:
        logger.error(
            "%s should run on %s instead of %s", vm, host, vm_host)
        return False
    return True


def calculate_memory_for_memory_filter(hosts_list, difference=10):
    """
    Calculate memory for VM's to prevent run more than one VM on each host

    Args:
        hosts_list (list): Hosts names
        difference (int): Leave some free memory on host

    Returns:
        list: Memory values for VM's ordered from big to small
    """
    mem_hosts = map(
        lambda host: hosts.get_host_max_scheduling_memory(host), hosts_list
    )
    host_memory_l = []
    for host_memory in mem_hosts:
        host_memory -= host_memory / difference
        host_memory -= host_memory % MB
        host_memory_l.append(host_memory)
    return sorted(host_memory_l, reverse=True)


def migrate_by_maintenance(
    vms_list, src_host, vm_os_type, vm_user, vm_password,
    connectivity_check=True, src_host_resource=None
):
    """
    Migrate VMs by setting host to maintenance

    Args:
        vms_list (list): VMs to migrate
        src_host (str): Host to set to maintenance
        vm_user (str): User for the VM machine
        vm_password (str): Password for the vm machine
        vm_os_type (str): Type of the OS of VM
        connectivity_check (bool): check VM connectivity after maintenance
        src_host_resource (Host resource): Host resource object of source host

    Returns:
        bool: True if migration succeeded, False otherwise.
    """
    status = True
    if not hosts.deactivate_host(positive=True, host=src_host):
        return False

    logger.info("Checking VMs after migration")
    if connectivity_check:
        if not check_vms_after_migration(
            vms_list=vms_list, src_host=src_host, vm_os_type=vm_os_type,
            vm_user=vm_user, vm_password=vm_password
        ):
            status = False
    if not hl_hosts.activate_host_if_not_up(
        host=src_host, host_resource=src_host_resource
    ):
        return False
    return status


def migrate_by_nic_down(
    vms_list, src_host, password, nic, vm_os_type, vm_user, vm_password
):
    """
    Migrate VMs by set down required network on host

    Args:
        vms_list (list): VMs to migrate
        src_host (str): Host to set the NIC down
        password (str): Host password
        nic (str): NIC name to put down
        vm_user (str): User for the VM machine
        vm_password (str): Password for the vm machine
        vm_os_type (str): Type of the OS of VM

    Returns
        bool: True is VM was migrate over Nic, else False
    """
    status = True
    logger.info("Setting %s down on %s", nic, src_host)
    host_ip = hosts.get_host_ip_from_engine(host=src_host)
    vds_resource = resources.VDS(ip=host_ip, root_password=password)
    if not hosts.set_host_non_operational_nic_down(
        host_resource=vds_resource, nic=nic
    ):
        logger.error(
            "Couldn't start migration by disconnecting the NIC with "
            "required network on it"
        )
        return False

    logger.info("Checking VMs after migration")
    if not check_vms_after_migration(
        vms_list=vms_list, src_host=src_host, vm_os_type=vm_os_type,
        vm_user=vm_user, vm_password=vm_password
    ):
        status = False

    logger.info(
        "Put the %s in the UP state and activate the %s", nic, src_host
    )
    if not vds_resource.network.if_up(nic=nic):
        logger.error("Couldn't put NIC %s in up state on %s", nic, src_host)
        return False

    if not hl_hosts.activate_host_if_not_up(host=src_host, host_resource=None):
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
    vms_host = list()
    for vm in vms_list:
        sampler = TimeoutingSampler(
            timeout=MIGRATION_TIMEOUT, sleep=1, func=vms.get_vm_host,
            vm_name=vm
        )
        logger.info(
            "Waiting for VM: %s to migrate from its source host: %s",
            vm, src_host
        )
        try:
            for sample in sampler:
                if sample != src_host:
                    vms_host.append(sample)
                    break
        except APITimeout as e:
            logger.error(e.message)
            return False

        vm_obj = VM_API.find(vm)
        if not VM_API.waitForElemStatus(vm_obj, "up", MIGRATION_TIMEOUT):
            logger.info("%s is not UP after migration", vm)
            return False

        logger.info("Check %s connectivity after migration finished", vm)
        if not vms.check_vm_connectivity(
            vm=vm, interval=INTERVAL, password=vm_password,
            timeout=MIGRATION_TIMEOUT
        ):
            logger.error("Check connectivity to %s failed", vm)
            return False

    if dst_host:
        logger.info(
            "Checking that all VMs moved to destination host (%s)", dst_host
        )
        if not all([True if i == dst_host else False for i in vms_host]):
            logger.error(
                "Not all VMs are located on destination host (%s)", dst_host
            )
            return False
    else:
        logger.info(
            "Checking that all VMs are not located on the source host (%s)",
            src_host
        )
        if not all([True if i != src_host else False for i in vms_host]):
            logger.error("Some VMs are located on source host (%s)", src_host)
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
            logger.info("migrating vm %s", machine)
            results.append(
                executor.submit(
                    vms.migrateVm, True, machine, dst_host, True, False)
            )
    for machine, res in zip(vms_list, results):
        if res.exception():
            logger.error(
                "Got exception while migrate vm %s: %s",
                machine, res.exception()
            )
            raise res.exception()
        if not res.result():
            raise exceptions.VMException("Cannot migrate vm %s" % machine)

    logger.info("Checking VMs after migration")
    if not check_vms_after_migration(
        vms_list=vms_list, src_host=src_host, vm_os_type=vm_os_type,
        vm_user=vm_user, vm_password=vm_password, dst_host=dst_host
    ):
        return False
    return True


def update_os_type(os_type, test_vms):
    """
    update os type for vms in list
    :param os_type: desire os type
    :type os_type: str
    :param test_vms: list of vms
    :type test_vms: list
    :return: True if os type set in vms
    :rtype bool
    """
    logger.info(
        "Set VMs %s os type to %s",
        test_vms,
        os_type
    )
    for vm in test_vms:
        logger.info(
            "update vm %s to os type: %s",
            vm,
            os_type
        )
        if not vms.updateVm(
            True,
            vm=vm,
            os_type=os_type
        ):
            logger.error(
                "Failed to update os type to vm %s",
                vm
            )
            return False
    return True


def get_vm_memory(vm):
    """
     return vm memory it will use as
     default memory to restore vm memory
    :param vm: vm name
    :type vm: str
    :return: vm memory
    :rtype: str
    """
    logger.info("store vm %s memory", vm)
    vm_obj = vms.get_vm(vm)
    logger.info("vm memory: %s", vm_obj.get_memory())
    return vm_obj.get_memory()


def set_vms_with_host_memory_by_percentage(
    test_hosts,
    test_vms,
    percentage=10
):
    """
    update vms in list memory with of hosts memory by percentage.
    :param test_hosts: host list
    :type test_hosts: list
    :param test_vms: vm list
    :type test_vms: list
    :param percentage: percentage of the host memory
    :type percentage: int
    :return: True/False if vms memory updated , index of host with max memory
    :rtype: tuple {bool,int}
    """
    logger.info(
        'update vms %s memory with %s percent of host memory'
        'for hosts: %s.' %
        (
            test_vms,
            str(percentage),
            test_hosts
        )
    )
    hosts_memory = [
        getStat(host, 'host', 'hosts', 'memory.total')
        for host in test_hosts
    ]
    host_index_max_mem = hosts_memory.index(max(hosts_memory))
    logger.info(
        "The host with the maximum memory: %s",
        test_hosts[host_index_max_mem]
    )
    logger.info(
        "update vms: %s  memory to host memory",
        test_vms
    )
    for vm in test_vms:
        for host_memory in hosts_memory:
            new_memory = (
                long(
                    long(host_memory.get('memory.total')) *
                    (float(percentage) / float(100))
                )
            )
            logger.info("normalization memory to MB: %s", str(new_memory))
            new_memory = (long(new_memory / MB)) * MB
            logger.info(
                "update vm: %s memory to %s",
                vm,
                str(new_memory)
            )
            if not vms.updateVm(
                True,
                vm=vm,
                memory=new_memory,
                max_memory=new_memory + 2 * GB,
                compare=False
            ):
                logger.error(
                    "Failed to update memory to vm %s",
                    vm
                )
                return False, -1
    return True, host_index_max_mem


def update_vms_memory(vms_list, memory, max_memory=None):
    """
    Update memory for vms in list

    Args:
        vms_list (list): list of vms for update
        memory (int): memory to update
        max_memory (int): max memory value if none will not update max memory

    Returns:
        bool:True if memory updated
    """
    for vm in vms_list:
        logger.info("update vm: %s memory to %d", vm, memory)
        if not vms.updateVm(
            True,
            vm=vm,
            memory=memory,
            memory_guaranteed=memory / 2,
            max_memory=max_memory,
            compare=False
        ):
            logger.error("Failed to update memory to vm %s", vm)
            return False
    return True


def create_vm_using_glance_image(
    glance_storage_domain_name, glance_image, **kwargs
):
    """
    Create a vm using an imported disk from glance repository

    :param glance_storage_domain_name: Name of the glance repository
    :type glance_storage_domain_name: str
    :param glance_image: Name of the desired image to use
    :type glance_image: str
    :return: True on success, False otherwise
    :rtype: bool
    """
    logger.info(
        "Verifies whether image %s exists in glance repository %s",
        glance_image, glance_storage_domain_name
    )
    if not storagedomains.verify_image_exists_in_storage_domain(
        glance_storage_domain_name, glance_image
    ):
        logger.error(
            "Glance image %s is not in glance storage domain %s",
            glance_image, glance_storage_domain_name
        )
        return False
    target_storage_domain = kwargs.get('storageDomainName')
    update_args = {
        'storageDomainName': None,  # To avoid installation process
        'installation': False,  # To avoid installation process
        'start': 'false'  # To avoid starting vm before attaching the image
        # to it
    }
    positive = kwargs.pop('positive', True)
    vm_name = kwargs.pop('vmName')
    vm_description = kwargs.pop('vmDescription', vm_name)
    kwargs.update(update_args)
    # Create a class instance for GlanceImage
    glance = storagedomains.GlanceImage(
        glance_image, glance_storage_domain_name
    )
    disk_alias = "{0}_Disk_glance".format(vm_name)
    logger.info("Importing image from %s", glance_storage_domain_name)
    if not glance.import_image(
        destination_storage_domain=target_storage_domain,
        cluster_name=kwargs.get('cluster'),
        new_disk_alias=disk_alias,
    ):
        logger.error(
            "Failed to import image %s from glance repository", glance_image
        )
        return False
    logger.info("Creating vm %s with nic", vm_name)
    if not vms.createVm(
        positive=positive, vmName=vm_name,
        vmDescription=vm_description, **kwargs
    ):
        logger.error("Failed to add vm %s", vm_name)
        return False
    logger.info("Attaching imported disk to vm")
    if not disks.attachDisk(True, disk_alias, vm_name):
        logger.error(
            "Failed to attach disk %s to vm %s", glance_image, vm_name
        )
        return False
    disk_interface = kwargs.get('diskInterface')
    logger.info("Updating disk's interface to: %s", disk_interface)
    if not disks.updateDisk(
        positive=True, vmName=vm_name, alias=disk_alias,
        interface=disk_interface, bootable=True
    ):
        logger.error("Failed to update disk's attributes")
        return False
    return True


def cancel_vm_migrate(vm, wait=True, timeout=MIGRATION_TIMEOUT):
    """
    Cancel VM Migrate

    :param vm: name of VM
    :type vm: str
    :param wait: if should wait until done
    :type wait: bool
    :return: True: if cancel migration finish with success
             False: if cancel migration did not success
    :rtype: bool
    """

    vm_obj = VM_API.find(vm)
    source_host_name = vms.get_vm_host(vm)
    logger.info("Cancel migration on VM %s", vm)
    log_err = "Failed to cancel migration on VM %s"
    if not VM_API.syncAction(vm_obj, "cancelmigration", True):
        logger.error(log_err, vm)
        return False

    if not wait:
        logger.warning("Not going to wait till Cancel VM migration completes.")
        return True

    if not VM_API.waitForElemStatus(vm_obj, ENUMS["vm_state_up"], timeout):
        logger.error(log_err, vm)
        return False
    destination_host_name = vms.get_vm_host(vm)
    logger.info(
        "Check that vm stay on the same host "
        "source host: %s destination host: %s",
        source_host_name, destination_host_name
    )
    return source_host_name == destination_host_name


def get_vms_objects_from_cluster(cluster):
    """
    Gets all VMs objects in given cluster
    :param cluster: cluster name
    :type cluster: str
    :return: List of VMs object
    :rtype: list
    """
    logging.info("Getting all vms in cluster %s", cluster)
    cluster_id = CLUSTER_API.find(cluster).get_id()
    all_vms = VM_API.get(abs_link=False)
    vms_in_cluster = [
        vm for vm in all_vms
        if vm.get_cluster().get_id() == cluster_id]
    return vms_in_cluster


def expand_vm_memory(vm_name, mem_size_to_expand, number_of_times=1):
    """
    Expand memory in multiple of given memory size

    Args:
        vm_name(str): VM name
        mem_size_to_expand(int): memory size in GB/MB
        number_of_times(int): number of time to expand vm memory

    Returns:
        tuple: memory size before hotplug on engine,
        memory size after hotplugging on engine,
        new memory size updated
    """

    memory_size_before = int(get_vm_memory(vm_name))
    new_memory_size = memory_size_before
    logger.info("VM memory before: %s", memory_size_before)
    for i in range(0, number_of_times):
        new_memory_size += mem_size_to_expand
        logger.info("Update vm memory to: %s", new_memory_size)
        if not vms.updateVm(
            positive=True,
            vm=vm_name,
            memory=new_memory_size,
            memory_guaranteed=new_memory_size,
            compare=False
        ):
            logger.error("Failed to update memory")
            return memory_size_before, -1, -1
        # Using sleep for the DIMM adding and removing command to succeed
        if number_of_times > 1:
            if mem_size_to_expand >= 0 and i > 2:
                sleep(SLEEP_TIME_HOTPLUG_DEVICE)
            else:
                sleep(SLEEP_TIME_HOT_UNPLUG_DEVICE)

    memory_size_after = get_vm_memory(vm_name)
    logger.info(
        "VM was update to %s:\n"
        "VM memory size before(on engine):%s \n"
        "VM memory size after(on engine): %s \n",
        new_memory_size, memory_size_before, memory_size_after
    )
    return memory_size_before, memory_size_after, new_memory_size


def create_windows_vm(
    disk_name,
    iso_name,
    agent_url,
    disk_interface=None,
    glance_domain=None,
    storage_name=None,
    use_sysprep=True,
    **vm_kwargs
):
    """
    Create vm with windows image from glance and install guest tools

    :param disk_name: Name of the disk with windows to use
    :type disk_name: str
    :param iso_name: ISO file with guest tools to install
    :type iso_name: str
    :param agent_url: URL where agent of guest tools is running
    :type agent_url: str
    :param disk_interface: Interface for disk to use
    :type disk_interface: str
    :param glance_domain: Name of glance domain to use
    :type glance_domain: str
    :param storage_name: Name of storage where import glance image
    :type storage_name: str
    :param vm_kwargs: kwargs to createVm method
    :type vm_kwargs: dictionary
    :param use_sysprep: True if sysprep should be used, False otheriwse
    :type use_sysprep: boolean
    :return: Tuple with status and failure message
    :rtype: tuple
    """
    WGT_SUCCESS_CODE = "3010"

    def __get_install_status(
        vm_id,
        sleep_time=SLEEP_TIME,
        max_time=WGT_INSTALL_TIMEOUT
    ):
        """
        Wait until installation is complete and check return code

        Args:
            vm_id (str): ID of a VM
            sleep_time (int): Sleep time between checks
            max_time (int): Maximum time to sleep

        Returns:
            str: WGT installation status code or None if something nasty
            happened (request returned neither 200 nor 404)
        """
        request = None
        logger.info("Quering for WGT installation status")

        for request in TimeoutingSampler(
            max_time,
            sleep_time,
            urllib.urlopen,
            agent_url.format(action='query', vm_id=vm_id),
        ):
            status = request.getcode()
            if status == 200:
                break
            elif status == 404:
                if LookUpVMIpByName('', '').get_ip(vm_name, check_mac=False):
                    break
                logger.info('Still waiting for results...')
            else:
                logger.error("Got invalid status: '%s'", status)
                request = None
                break
        else:
            vms.restartVm(vm_name, wait_for_ip=True)
            request = urllib.urlopen(
                agent_url.format(action='query', vm_id=vm_id))

        if request.getcode() == 200:
            return request.read()
        elif request.getcode() == 404 and (
            LookUpVMIpByName('', '').get_ip(vm_name, check_mac=False) or
            vms.wait_for_vm_ip(vm_name, timeout=60)
        ):
            return WGT_SUCCESS_CODE
        return None

    # import image from glance
    if glance_domain and storage_name:
        if not storagedomains.import_glance_image(
            glance_repository=glance_domain,
            glance_image=disk_name,
            target_storage_domain=storage_name,
            target_cluster=vm_kwargs.get('cluster'),
            new_disk_alias=disk_name,
        ):
            return False, "Failed to import image '%s'" % disk_name

    # create vm & start vm
    vm_name = vm_kwargs.get('vmName')
    if not vms.createVm(**vm_kwargs):
        return False, "Failed to create vm '%s'" % vm_name

    if not disks.attachDisk(
        True, disk_name, vm_name, interface=disk_interface
    ):
        return False, "Failed to attach disk to vm '%s'" % vm_name

    if not disks.updateDisk(
            True, vmName=vm_name, alias=disk_name, bootable=True
    ):
        return False, "Failed to update disk of vm '%s'" % vm_name

    if not vms.runVmOnce(
        positive=True,
        vm=vm_name,
        use_sysprep=use_sysprep,
        wait_for_state=ENUMS["vm_state_up"],
    ):
        return False, "Failed to start vm '%s'" % vm_name

    # Reset vm
    vm_id = vms.get_vm(vm_name).get_id()
    logger.info("Resseting vm '%s' record", vm_name)
    request = urllib.urlopen(
        agent_url.format(
            action='reset',
            vm_id=vm_id,
        )
    )
    if request.getcode() != 202:
        return False, 'Error resetting VM record'

    # Attach CD & run installation
    if not vms.changeCDWhileRunning(
        vm_name=vm_name,
        cdrom_image=iso_name,
    ):
        return False, "Failed to change CD to %s" % iso_name

    # Get install status and verify
    status_code = __get_install_status(vm_id)
    if status_code is None:
        return (
            False,
            "There was an error installing RHEV tools, please examine logs"
        )

    if status_code != WGT_SUCCESS_CODE:
        return (
            False,
            "RHEV Tools installation completed with code: '%s'" % status_code
        )
    vms.wait_for_vm_states(vm_name, states=[ENUMS['vm_state_up']])
    logger.info("RHEV Tools installation completed successfully")
    return True, "Vm '%s' successfully created" % vm_name


def wait_for_restored_stateless_snapshot(vm):
    """
    This function waits for the whole statless snapshot restoration flow to
    complete.
    1. Wait until statless snapshot is removed -> in practice 'Active VM'
    points to that snapshot.
    2. Wait until 'Active VM' is in state 'OK'.

    :param vm: Name of vm
    :type vm: str
    :return: True if 'stateless snapshot' was deleted and 'Active' snapshot is
    is in state 'ok', False otherwise.
    :rtype: bool
    """
    if not vms.wait_for_snapshot_gone(
        vm, ENUMS['snapshot_stateless_description']
    ):
        return False
    vms.wait_for_vm_snapshots(
        vm, ENUMS['snapshot_state_ok'],
        ENUMS['snapshot_active_vm_description']
    )
    return True


def stop_stateless_vm(vm):
    """
    Stops a stateless vm and verifies that the stateless snapshot
    is removed after the shut down and that that 'Active VM' is at satatus OK.

    :param vm: Name of vm.
    :type vm: str
    :return: True if vm stopped and restored to original snapshot state, False
    otherwise.
    :rtype: bool
    """
    log_info, log_error = ll_general.get_log_msg(
        log_action="stop", obj_type="VM", obj_name=vm,
    )
    logging.info(log_info)
    if not vms.stop_vms_safely([vm]):
        logging.error(log_error)
        return False
    if not wait_for_restored_stateless_snapshot(vm):
        logging.error(log_error)
        return False
    return True


def get_vm_cpu_consumption_on_the_host(vm_name):
    """
    Get the VM CPU consumption on the host

    :param vm_name: vm name
    :type vm_name: str
    :return: VM CPU consumption on the host
    :rtype: int
    """
    logger.info("Get VM %s cpu consumption", vm_name)
    stats = getStat(vm_name, "vm", "vms", ["cpu.current.total"])
    vm_cpus = vms.get_vm_processing_units_number(vm_name)
    return int(stats["cpu.current.total"]) / vm_cpus


def get_vm_macs(vm, nics):
    """
    Get MACs from VM.

    Args:
        vm (str): VM name.
        nics (List):  List of NICs to get the MACs for.

    Returns:
        List: VM MACs.
    """
    vm_macs = []
    for nic in nics:
        vm_mac = vms.getVmMacAddress(positive=True, vm=vm, nic=nic)
        vm_macs.append(vm_mac[1]["macAddress"])

    return vm_macs


def move_vm_disks(vm_name, target_storage_domain):
    """
    Moves all disks of vm to another storage domain

    __author__ = "slitmano"

    :param vm_name: The VM whose disk will be moved
    :type vm_name: str
    :param target_storage_domain: Name of the storage domain into
    which the disk should be moved
    :type target_storage_domain: str
    :raise VMException
    """
    vm_disks_ids = [
        disk.get_id() for disk in vms.getVmDisks(vm_name) if
        disk.get_storage_type() == ENUMS['storage_dom_type_image']
        ]
    for disk_id in vm_disks_ids:
        disks.move_disk(
            disk_id=disk_id, target_domain=target_storage_domain,
            wait=False
        )
    for disk_id in vm_disks_ids:
        disks.wait_for_disk_storage_domain(disk_id, target_storage_domain)
    if not vms.waitForVmsDisks(vm_name):
        raise errors.VMException(
            "The disks of vm: %s failed to move to state 'ok'" % vm_name
        )


def get_memory_on_vm(vm_resource):
    """
    Return the memory on VM using free command
    Args:
         vm_resource(RemoteExecutor): VM executor

    Returns:
        str: VM memory in KB
    """
    logger.info("Getting vm actual memory with free command")
    rc, out, _ = vm_resource.run_cmd(
        cmd=shlex.split(CHECK_MEMORY_COMMAND),
    )
    if rc:
        logger.error("Failed to get VM memory")
        return ""
    actual_memory = int(shlex.split(out)[1]) * KB
    logger.info("VM actual memory: %s", actual_memory)
    return actual_memory


def remove_all_vms_from_cluster(cluster_name, skip=[], wait=False):
    """
    Stop (if need) and remove all exists vms from specific cluster

    Args:
        cluster_name(str): cluster name
        skip(list): list of names of vms which should be left
        wait(bool) : If True we will wait for each remove VM to complete
                     else the remove will be asynchronous
    Returns:
        bool: True, if all vms removed from cluster, False otherwise
    """
    all_removed = True
    logger_message = "Remove VMs from cluster %s" % cluster_name
    if skip:
        logger_message += " except %s" % ", ".join(skip)
    logger.info(logger_message)
    vms_in_cluster = [
        vm.get_name() for vm in get_vms_objects_from_cluster(cluster_name)
        if vm.get_name() not in skip
    ]
    if vms_in_cluster:
        vms.stop_vms_safely(vms_in_cluster)
        log = "" if wait else "asynchrony"
        logger.info("Remove VMs %s", log)
        for vm in vms_in_cluster:
            if not vms.removeVm(True, vm, wait=False):
                all_removed = False
        if wait and all_removed:
            try:
                vms.waitForVmsGone(True, vms_in_cluster)
            except APITimeout:
                all_removed = False
    if not all_removed:
        logger.error(
            "Failed to remove all vms: %s from cluster: %s",
            vms_in_cluster, cluster_name
        )
    return all_removed


@ll_general.generate_logs(step=True)
def clone_vm(positive, vm, clone_vm_name, wait=True):
    """
    Clone vm to clone_vm_name

    Args:
        positive (bool): True if clone action should succeed, False otherwise
        vm (str): base vm name
        clone_vm_name (str): clone vm name
        wait (bool): True if walt for status of disks, False otherwise

    Returns:
        bool: True if vm was cloned properly, False otherwise
    """
    action_params = {}
    vm_obj = VM_API.find(vm)
    new_vm = vms.data_st.Vm()
    new_vm.set_name(clone_vm_name)
    action_params['vm'] = new_vm
    action_params['async'] = True

    res = VM_API.syncAction(vm_obj, 'clone', positive, **action_params)
    if res:
        if not wait:
            logger.warning(
                "Not going to wait till VM clone completes. wait=%s, "
                "positive=%s" % (str(wait), positive)
            )
            return positive
        if wait:  # checks disks status
            if not VM_API.waitForElemStatus(
                vms.get_vm(clone_vm_name), "down",
                vms.VM_DISK_CLONE_TIMEOUT
            ):
                return False
            base_vm_disks = vms.get_vm_disks_ids(vm=vm)
            clone_vm_disks = vms.get_vm_disks_ids(vm=clone_vm_name)
            disks_list = base_vm_disks + clone_vm_disks
            disks_status = vms.wait_for_disks_status(
                disks_list, key='id', timeout=vms.CLONE_FROM_SNAPSHOT
            )
            return disks_status and positive
    return False


def get_boot_device_logical_name(vm_name):
    """
    Get the boot device logical name of a given VM

    Args:
        vm_name (str): The name of the VM

    Returns:
        str: The boot device of the VM
    """
    boot_disk = vms.get_vm_bootable_disk(vm_name)
    return vms.get_vm_disk_logical_name(vm_name, boot_disk)


def reboot_to_state(vm, state='up'):
    """
    Reboot VM to a chosen state. Default is up state.

    Args:
        vm(str): name of vm
        state(str): vm status should wait for
        [unassigned, up, down, powering_up, powering_down,
        paused, migrating_from, migrating_to, unknown,
        not_responding, wait_for_launch, reboot_in_progress,
        saving_state, restoring_state, suspended,
        image_illegal, image_locked]

    Returns:
        bool: True if vm was rebooted properly to the chosen state,
        False otherwise.
    """
    if not vms.reboot_vm(positive=True, vm=vm):
        return False
    return vms.waitForVMState(vm=vm, state=state)
