"""
High-level functions above virtual machines
"""
from art.rhevm_api import resources
import logging
import shlex
import urllib

from concurrent.futures import ThreadPoolExecutor
from art.core_api import is_action
import art.rhevm_api.tests_lib.low_level.vms as vms
import art.rhevm_api.tests_lib.low_level.hosts as hosts
import art.rhevm_api.tests_lib.low_level.disks as disks
import art.rhevm_api.tests_lib.low_level.storagedomains as storagedomains
import art.rhevm_api.tests_lib.low_level.general as ll_general
from art.rhevm_api.utils.test_utils import get_api, setPersistentNetwork
from art.test_handler import exceptions
from art.test_handler.settings import opts
import art.test_handler.exceptions as errors

from art.rhevm_api.utils.test_utils import getStat


from utilities.timeout import TimeoutingSampler

LOGGER = logging.getLogger("art.hl_lib.vms")
ENUMS = opts['elements_conf']['RHEVM Enums']
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
CHECK_MEMORY_COMMAND = "grep 'MemTotal' /proc/meminfo | awk '{ print $2 }'"

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
    if (
        vm_obj.status.state == ENUMS['vm_state_up'] and
        not vms.shutdownVm(True, vm_name)
    ):
        raise errors.VMException("Shutdown of vm %s failed" % vm_name)
    return vms.waitForVMState(vm_name, state=ENUMS['vm_state_down'])


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
    Start VM and return VM IP

    __Author__: alukiano

    Args:
        vm_name (str): vm name

    Returns:
        str: VM IP
    """
    logging.info("Check vm %s status", vm_name)
    if vms.checkVmState(True, vm_name, ENUMS['vm_state_down']) and start_vm:
        logging.info("Start vm %s", vm_name)
        if not vms.startVm(True, vm_name):
            raise errors.VMException("Failed to start vm %s" % vm_name)

    logging.info("Wait until vm %s is up and fetch ip", vm_name)
    status, result = vms.waitForIP(vm_name)
    if not status:
        raise errors.VMException("Vm %s didn't get IP" % vm_name)

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
    wait_for_ip=True
):
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
    Calculate memory for vms to prevent run more than one vm on each host

    :param hosts_list: list of host names
    :type hosts_list: list
    :returns: list of memory values for vms ordered from big to small
    :rtype: list
    """
    mem_hosts = map(
        lambda host: hosts.get_host_free_memory(host), hosts_list
    )
    host_memory_l = []
    for host_memory in mem_hosts:
        host_memory -= host_memory / 10
        host_memory -= host_memory % MB
        host_memory_l.append(host_memory)
    return sorted(host_memory_l, reverse=True)


def migrate_by_maintenance(
    vms_list, src_host, vm_os_type, vm_user, vm_password,
    connectivity_check=True
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
    :param connectivity_check: check VM connectivity after maintenance
    :type connectivity_check: bool
    :return: True/False
    :rtype: bool
    """
    status = True
    LOGGER.info("Setting %s into maintenance", src_host)
    if not hosts.deactivateHost(positive=True, host=src_host):
        LOGGER.error("Failed to set %s into maintenance", src_host)
        return False
    LOGGER.info("Checking VMs after migration")
    if connectivity_check:
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
    host_ip = hosts.get_host_ip_from_engine(host=src_host)
    vds_resource = resources.VDS(ip=host_ip, root_password=password)
    if not hosts.set_host_non_operational_nic_down(
        host_resource=vds_resource, nic=nic
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
    if not vds_resource.network.if_up(nic=nic):
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


def get_vms_os_type(test_vms):
    """
     get vms list and returns the os type of the vms as list
     if VM has no os the value return for this VM will be "Other"
     in case of exception return empty None
    :param test_vms: list of vms
    :type  test_vms: list
    :return: list of os type per vm
    :rtype: list
    """
    try:
        LOGGER.info("Get VMs os type")
        vms_obj = [vms.get_vm(vm) for vm in test_vms]
        return [vm.get_os().get_type().lower() for vm in vms_obj]
    except Exception, e:
        LOGGER.error("Failed to get os type for vms: %s" % test_vms)
        LOGGER.error("Failed to get os type, reason: %s" % e)
        return None


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
    LOGGER.info(
        "Set VMs %s os type to %s",
        test_vms,
        os_type
    )
    for vm in test_vms:
        LOGGER.info(
            "update vm %s to os type: %s",
            vm,
            os_type
        )
        if not vms.updateVm(
            True,
            vm=vm,
            os_type=os_type
        ):
            LOGGER.error(
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
    LOGGER.info("store vm %s memory", vm)
    vm_obj = vms.get_vm(vm)
    LOGGER.info("vm memory: %s", vm_obj.get_memory())
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
    LOGGER.info(
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
    LOGGER.info(
        "The host with the maximum memory: %s",
        test_hosts[host_index_max_mem]
    )
    LOGGER.info(
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
            LOGGER.info("normalization memory to MB: %s", str(new_memory))
            new_memory = (long(new_memory / MB)) * MB
            LOGGER.info(
                "update vm: %s memory to %s",
                vm,
                str(new_memory)
            )
            if not vms.updateVm(
                True,
                vm=vm,
                memory=new_memory
            ):
                LOGGER.error(
                    "Failed to update memory to vm %s",
                    vm
                )
                return False, -1
    return True, host_index_max_mem


def update_vms_memory(vms_list, memory):
    """
    Update memory for vms in list

    :param vms_list:list of vms for update
    :type vms_list: list
    :param memory: memory to update
    :type memory: int
    :return: True if memory updated
    :rtype: bool
    """
    for vm in vms_list:
        LOGGER.info(
            "update vm: %s memory to %d",
            vm,
            memory
        )
        if not vms.updateVm(
            True,
            vm=vm,
            memory=memory,
        ):
            LOGGER.error(
                "Failed to update memory to vm %s",
                vm
            )
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
    LOGGER.info(
        "Verifies whether image %s exists in glance repository %s",
        glance_image, glance_storage_domain_name
    )
    if not storagedomains.verify_image_exists_in_storage_domain(
        glance_storage_domain_name, glance_image
    ):
        LOGGER.error(
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
    LOGGER.info("Importing image from %s", glance_storage_domain_name)
    if not glance.import_image(
        destination_storage_domain=target_storage_domain,
        cluster_name=kwargs.get('cluster'),
        new_disk_alias=disk_alias,
    ):
        LOGGER.error(
            "Failed to import image %s from glance repository", glance_image
        )
        return False
    LOGGER.info("Creating vm %s with nic", vm_name)
    if not vms.createVm(
        positive=positive, vmName=vm_name,
        vmDescription=vm_description, **kwargs
    ):
        LOGGER.error("Failed to add vm %s", vm_name)
        return False
    LOGGER.info("Attaching imported disk to vm")
    if not disks.attachDisk(True, disk_alias, vm_name):
        LOGGER.error(
            "Failed to attach disk %s to vm %s", glance_image, vm_name
        )
        return False
    disk_interface = kwargs.get('diskInterface')
    LOGGER.info("Updating disk's interface to: %s", disk_interface)
    if not disks.updateDisk(
        positive=True, vmName=vm_name, alias=disk_alias,
        interface=disk_interface, bootable=True
    ):
        LOGGER.error("Failed to update disk's attributes")
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
    LOGGER.info("Cancel migration on VM %s", vm)
    log_err = "Failed to cancel migration on VM %s"
    if not VM_API.syncAction(vm_obj, "cancelmigration", True):
        LOGGER.error(log_err, vm)
        return False

    if not wait:
        LOGGER.warning("Not going to wait till Cancel VM migration completes.")
        return True

    if not VM_API.waitForElemStatus(vm_obj, ENUMS["vm_state_up"], timeout):
        LOGGER.error(log_err, vm)
        return False
    destination_host_name = vms.get_vm_host(vm)
    LOGGER.info(
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
    all_vms = VM_API.get(absLink=False)
    vms_in_cluster = [
        vm for vm in all_vms
        if vm.get_cluster().get_id() == cluster_id]
    return vms_in_cluster


def check_vm_memory(vm_resource, expected_mem_size):
    """
    Check VM memory, and compare to expected result

    :param vm_resource: vm resource
    :type vm_resource: Host
    :param expected_mem_size: the expected value in bytes
    :type expected_mem_size: int
    :return: True if memory as expected else False
    :rtype: bool
    """
    expected_memory = expected_mem_size / KB
    rc, out, _ = vm_resource.run_command(shlex.split(CHECK_MEMORY_COMMAND))
    if rc:
        return False
    actual_memory = shlex.split(out)[1]
    LOGGER.info("Expected memory(kb): %s", expected_memory)
    LOGGER.info("Actual memory(kb): %s", actual_memory)
    if (
            expected_memory * 0.98 < int(actual_memory) or
            expected_memory * 0.98 > int(actual_memory)
    ):
        return True
    else:
        LOGGER.error("memory check failed")
        return False


def expand_vm_memory(vm_name, mem_size_to_expand, number_of_times=1):
    """
    Expand memory in multiple of given memory size

    :param vm_name: vm name
    :type vm_name: str
    :param mem_size_to_expand: memory size in GB/MB
    :type mem_size_to_expand: int
    :param number_of_times: number of time to expend vm memory
    :type number_of_times: int
    :return: memory_size_before, memory_size_after, new_memory_size
    :rtype: tuple
    """

    memory_size_before = int(get_vm_memory(vm_name))
    new_memory_size = memory_size_before
    LOGGER.info("VM memory before: %s", memory_size_before)
    for i in range(0, number_of_times):
        new_memory_size += mem_size_to_expand
        LOGGER.info("Update vm memory to: %s", new_memory_size)
        if not vms.updateVm(
            positive=True,
            vm=vm_name,
            memory=new_memory_size
        ):
            LOGGER.error("Failed to update memory")
            return memory_size_before, -1, -1

    memory_size_after = get_vm_memory(vm_name)
    LOGGER.info(
        "After update: memory_size_before:%s \n"
        "memory_size_after: %s \n"
        "new_memory_size:%s "
        % (memory_size_before, memory_size_after, new_memory_size)
    )
    return memory_size_before, memory_size_after, new_memory_size


def create_windows_vm(
    disk_name,
    iso_name,
    agent_url,
    glance_domain=None,
    storage_name=None,
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
    :param glance_domain: Name of glance domain to use
    :type glance_domain: str
    :param storage_name: Name of storage where import glance image
    :type storage_name: str
    :param vm_kwargs: kwargs to createVm method
    :type vm_kwargs: dictionary
    :return: Tuple with status and failure message
    :rtype: tuple
    """
    def __get_install_status(
        vm_id,
        sleep_time=SLEEP_TIME,
        max_time=WGT_INSTALL_TIMEOUT
    ):
        request = None
        LOGGER.info("Quering for WGT installation status")

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
                LOGGER.info('Still waiting for results...')
            else:
                LOGGER.error("Got invalid status: '%s'", status)
                request = None
                break

        return request

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

    if not vms.addNic(
        positive=True,
        vm=vm_name,
        name='virtioNIC',
        network=vm_kwargs.get('network'),
        interface=ENUMS['nic_type_virtio'],
    ):
        return False, "Failed to add nic to vm '%s'" % vm_name

    if not disks.attachDisk(True, disk_name, vm_name):
        return False, "Failed to attach disk to vm '%s'" % vm_name

    if not vms.startVm(True, vm_name, wait_for_status=ENUMS["vm_state_up"]):
        return False, "Failed to start vm '%s'" % vm_name

    # Reset vm
    vm_id = vms.get_vm(vm_name).get_id()
    LOGGER.info("Resseting vm '%s' record", vm_name)
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
    request = __get_install_status(vm_id)
    if request is None:
        return (
            False,
            "There was an error installing RHEV tools, please examine logs"
        )

    status_code = request.read()
    if status_code != '3010':
        return (
            False,
            "RHEV Tools installation completed with code: '%s'" % status_code
        )
    LOGGER.info("RHEV Tools installation completed successfully")
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
        action="stop", obj_type="VM", obj_name=vm,
    )
    logging.info(log_info)
    if not vms.stop_vms_safely([vm]):
        logging.error(log_error)
        return False
    if not wait_for_restored_stateless_snapshot(vm):
        logging.error(log_error)
        return False


def get_vm_cluster(vm_name):
    """
    Get the VM cluster name

    :param vm_name: vm name
    :type vm_name: str
    :return:cluster name
    :rtype: str
    """
    LOGGER.info("Get VM %s cluster name", vm_name)
    vm_obj = VM_API.find(vm_name)
    cluster_id = vm_obj.cluster.id
    return CLUSTER_API.find(cluster_id, attribute='id').name


def get_vm_cpu_consumption_on_the_host(vm_name):
    """
    Get the VM CPU consumption on the host

    :param vm_name: vm name
    :type vm_name: str
    :return: VM CPU consumption on the host
    :rtype: int
    """
    LOGGER.info("Get VM %s cpu consumption", vm_name)
    stats = getStat(vm_name, "vm", "vms", ["cpu.current.total"])
    vm_cpus = vms.get_vm_processing_units_number(vm_name)
    return int(stats["cpu.current.total"]) / vm_cpus


def get_vms_for_storage_type(datacenter_name, cluster_name, storage_type):
    """
    Returns a list of vm names with disks on storage domains of storage_type

    IMPORTANT: This function will check only the first vm's disk

    :param datacenter_name: Name of datacenter
    :type datacenter_name: str
    :param cluster_name: Name of cluster
    :type cluster_name: str
    :param storage_type: Type of storage (nfs, iscsi, glusterfs, fcp, ...)
    :type storage_type: str
    :return: List of vm names
    :rtype: list
    """
    vms_in_cluster = vms.get_vms_from_cluster(cluster_name)
    domains = storagedomains.getStorageDomainNamesForType(
        datacenter_name, storage_type
    )
    return [
        vm for vm in vms_in_cluster if (
            vms.get_vms_disks_storage_domain_name(vm) in domains
        )
    ]
