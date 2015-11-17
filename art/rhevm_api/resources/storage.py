import logging
import shlex

from art.rhevm_api import resources
from art.rhevm_api.tests_lib.low_level import hosts
from rhevmtests import helpers as rhevm_helpers
from rhevmtests.storage import config
from rhevmtests.storage.helpers import get_vm_ip


logger = logging.getLogger(__name__)

LV_CHANGE_CMD = 'lvchange -a {active} {vg_name}/{lv_name}'
PVSCAN_CACHE_CMD = 'pvscan --cache'
PVSCAN_CMD = 'pvscan'
FIND_CMD = 'find / -name %s'
CREATE_FILE_CMD = 'touch %s/%s'


def get_host_resource(host_name):
    """
    Takes the host name and returns the Host resource on which commands can be
    executed

    __author__ = "glazarov"
    :param host_name: Name of the host
    :type host_name: str
    :return: Host resource on which commands can be executed
    :rtype: Host resource
    """
    host_obj = hosts.get_host_object(host_name)
    return resources.Host.get(host_obj.get_address())


def get_vm_executor(vm_name):
    """
    Takes the VM name and returns the VM resource on which commands can be
    executed

    :param vm_name:  The name of the VM for which Host resource should be
    created
    :type vm_name: str
    :return: Host resource on which commands can be executed
    :rtype: Host resource
    """
    logger.info("Get IP from VM %s", vm_name)
    vm_ip = get_vm_ip(vm_name)
    logger.info("Create VM instance with root user from vm with ip %s", vm_ip)
    return rhevm_helpers.get_host_executor(
        ip=vm_ip, password=config.VMS_LINUX_PW
    )


def _run_cmd_on_remote_machine(machine_name, command):
    """
    Executes Linux command on remote machine

    :param machine_name: The machine to use for executing the command
    :type machine_name: str
    :param command: The command to execute
    :type command: str
    :return: True if the command executed successfully, False otherwise
    """
    vm_executor = get_vm_executor(machine_name)
    rc, _, error = vm_executor.run_cmd(cmd=shlex.split(command))
    if rc:
        logger.error(
            "Failed to run command %s on %s, error: %s",
            command, machine_name, error
        )
        return False
    return True


def lv_change(host_name, vg_name, lv_name, activate=True):
    """
    Set the LV attribute 'active' (active or inactive)

    __author__ = "ratamir, glazarov"
    :param host_name: The host to use for setting the Logical volume state
    :type host_name: str
    :param vg_name: The name of the Volume group under which LV is contained
    :type vg_name: str
    :param lv_name: The name of the logical volume which needs to be
    activated or deactivated
    :type lv_name: str
    :returns: True if succeeded, False otherwise
    :rtype: bool
    """
    active = 'y' if activate else 'n'
    host = get_host_resource(host_name)

    logger.info("Setting the logical volume 'active=%s' attribute", activate)
    rc, output, error = host.executor().run_cmd(
        shlex.split(LV_CHANGE_CMD.format(
            active=active, vg_name=vg_name, lv_name=lv_name)
        )
    )
    if rc:
        logger.error(
            "Error while setting the logical volume 'active=%s' attribute. "
            "Output is '%s', error is '%s'", activate, output, error
        )
        return False
    return True


def run_pvscan_command(host_name):
    """
    Executes pvscan on the input host

    __author__ = "ratamir, glazarov"
    :param host_name: The host to use for executing the pvscan command
    :type host_name: str
    :returns: True if succeeded, False otherwise
    :rtype: bool
    """
    # Execute 'pvscan --cache' in order to get the latest list of volumes.
    # In case no data is returned (equivalent to no changes), run 'pvscan' by
    # itself. This combination appears to correctly retrieve the latest
    # volume listing
    host = get_host_resource(host_name)

    logger.info("Executing '%s' command", PVSCAN_CACHE_CMD)
    rc, output, error = host.executor().run_cmd(shlex.split(PVSCAN_CACHE_CMD))
    if rc:
        logger.error(
            "Error while executing the '%s' command, output is '%s', "
            "error is '%s'", PVSCAN_CACHE_CMD, output, error
        )
        return False

    if output == '':
        logger.info("Executing '%s' command", PVSCAN_CMD)
        rc, output, error = host.executor().run_cmd(shlex.split(PVSCAN_CMD))
        if rc:
            logger.error(
                "Error while executing the '%s' command, output is '%s', "
                "error is '%s'", PVSCAN_CMD, output, error
            )
            return False
    return True


def get_storage_devices(vm_name, filter='vd[a-z]'):
    """
    Retrieve list of storage devices in requested linux VM

    __author__ = "ratamir, glazarov"
    :param vm_name: The VM to use for retrieving the storage devices
    :type vm_name: str
    :param filter: The regular expression to use in retrieving the storage
    devices
    :type filter: str
    :returns: List of connected storage devices found on vm using specified
    filter (e.g. [vda, vdb, sda, sdb])
    :rtype: list
    """
    vm_executor = get_vm_executor(vm_name)

    command = 'ls /sys/block | egrep \"%s\"' % filter
    rc, output, error = vm_executor.run_cmd(cmd=shlex.split(command))
    if rc:
        logger.error(
            "Error while retrieving storage devices from VM '%s, output is "
            "'%s', error is '%s'", output, error
        )
        return False
    return output.split()


def does_file_exist(vm_name, file_name):
    """
    Check if file_name refers to an existing path

    __author__ = "ratamir"
    :param vm_name: The VM to use in checking whether file exists
    :type vm_name: str
    :param file_name: File name to look for
    :type file_name: str
    :returns: True if file exists, False otherwise
    :rtype: bool
    """
    command = FIND_CMD % file_name
    return _run_cmd_on_remote_machine(vm_name, command)


def create_file_on_vm(vm_name, file_name, path):
    """
    Creates a file on vm

    __author__ = "ratamir"
    :param vm_name: The VM to use in creating the file_name requested
    :type vm_name: str
    :param file_name: The file to create
    :type file_name: str
    :param path: The path that the file will create under
    :type path: str
    :returns: True if succeeded in creating file requested, False otherwise
    :rtype: bool
    """
    command = CREATE_FILE_CMD % (path, file_name)
    return _run_cmd_on_remote_machine(vm_name, command)
