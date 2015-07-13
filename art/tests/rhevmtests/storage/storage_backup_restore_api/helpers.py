"""
Storage backup restore API
https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
Storage/3_3_Storage_Backup_API
"""
import config
import logging
import shlex

from art.rhevm_api.tests_lib.low_level import vms as vms
from art.rhevm_api.utils.test_utils import get_api
from rhevmtests.storage.helpers import create_vm_or_clone
from utilities.machine import Machine

DISKS_API = get_api('disk', 'disks')
COPY_DISK_TIMEOUT = 2000


LOGGER = logging.getLogger(__name__)

VM_IP_ADDRESSES = dict()
BASE_SNAP_DESC = "base_snap"  # Base snapshot description
SNAPSHOT_TEMPLATE_DESC = 'snap_%s'
RESTORED_VM = "restored_vm"
VM_DISK_SIZE = 6 * config.GB
SHOULD_CREATE_SNAPSHOT = (True, False)
TRANSIENT_DIR_PATH = "/var/lib/vdsm/transient"
DD_COMMAND = 'dd if=/dev/%s of=/dev/%s bs=1M oflag=direct'

vm_args = {
    'positive': True,
    'vmName': "",
    'vmDescription': '',
    'cluster': config.CLUSTER_NAME,
    'nic': config.NIC_NAME[0],
    'nicType': config.NIC_TYPE_VIRTIO,
    'size': VM_DISK_SIZE,
    'diskInterface': config.INTERFACE_VIRTIO,
    'volumeFormat': config.DISK_FORMAT_COW,
    'volumeType': True,  # sparse
    'bootable': True,
    'type': config.VM_TYPE_DESKTOP,
    'os_type': config.OS_TYPE,
    'memory': config.GB,
    'cpu_socket': config.CPU_SOCKET,
    'cpu_cores': config.CPU_CORES,
    'display_type': config.DISPLAY_TYPE,
    'start': True,
    'installation': True,
    'user': config.COBBLER_USER,
    'password': config.COBBLER_PASSWD,
    'image': config.COBBLER_PROFILE,
    'network': config.MGMT_BRIDGE,
    'useAgent': config.USE_AGENT,
}


def prepare_vm(vm_name, create_snapshot=False, storage_domain=None):
    """
    Installs vm with disks and create snapshot by demand

    Parameters:
        * vm_name - vm name
        * create_snapshot - True if should create snapshot
        * storage_domain - name of the storage domain
        * vm_args:
        - vmName = VM name
        - vmDescription = Decription of VM
        - cluster = cluster name
        - nic = nic name
        - storageDomainName = storage doamin name
        - size = size of disk (in bytes)
        - volumeType = true its mean sparse (thin provision) ,
                     false - preallocated.
        - volumeFormat = format type (COW)
        - diskInterface = disk interface (VIRTIO or IDE ...)
        - bootable = True when disk bootable otherwise False
        - type - vm type (SERVER or DESKTOP)
        - start = in case of true the function start vm
        - display_type - type of vm display (VNC or SPICE)
        - installation - true for install os and check connectivity in the end
        - user - user to connect to vm after installation
        - password - password to connect to vm after installation
        - osType - type of OS as it appears in art/conf/elements.conf
        - useAgent - Set to 'true', if desired to read the ip from VM
                   (agent exist on VM)
        - network - The network that the VM's VNIC will be attached to. (If
                  'vnic_profile' is not specified as well, a profile without
                  port mirroring will be selected for the VNIC arbitrarily
                  from the network's profiles).
    """
    args = vm_args.copy()
    args['storageDomainName'] = storage_domain
    args['vmName'] = vm_name
    assert create_vm_or_clone(**args)

    vm_ip = vms.waitForIP(vm_name)[1]['ip']
    assert vm_ip is not None
    LOGGER.info("Storing ip address %s for vm %s", vm_ip, vm_name)

    VM_IP_ADDRESSES[vm_name] = vm_ip

    assert vms.stopVm(True, vm_name)

    if create_snapshot:
        assert vms.addSnapshot(
            True, vm=vm_name,
            description=SNAPSHOT_TEMPLATE_DESC % vm_name)


def is_transient_directory_empty(host):
    """
    Checking the transient folder
        * host - host ip or fqdn
    return:
        True if the directory is empty, False otherwise
    """
    LOGGER.info("Checking transient directory")
    vdsm_machine = Machine(
        host=host, user=config.HOSTS_USER,
        password=config.HOSTS_PW).util('linux')

    return vdsm_machine.is_dir_empty(dir_path=TRANSIENT_DIR_PATH)


def copy_backup_disk(vm_ip, source_disk, destination_disk,
                     timeout=COPY_DISK_TIMEOUT):
    """
    Copy disks using dd command in specified machine
    Parameters:
        * vm_ip - ip of vm that the operation should executes on
        * source_disk - name of source device (e.g. vdb)
        * destination_disk - name of destination device (e.g. vdc)
        * timeout - timeout for operation
    Return:
        True if operation succeeded, False otherwise
    """
    vm_machine = Machine(
        host=vm_ip,
        user=config.VMS_LINUX_USER,
        password=config.VMS_LINUX_PW).util('linux')

    command = DD_COMMAND % (source_disk, destination_disk)

    LOGGER.info("copying data from %s to %s on vm %s", source_disk,
                destination_disk, vm_ip)

    ecode, out = vm_machine.runCmd(shlex.split(command),
                                   timeout=timeout)

    LOGGER.debug("dd output: %s", out.strip())
    return ecode
