"""
Hotplug test helpers functions
"""
from concurrent.futures import ThreadPoolExecutor
import logging
import os
import config
from art.rhevm_api.tests_lib.low_level import (
    disks as ll_disks,
    general as ll_general,
)
from art.test_handler import exceptions
from rhevmtests.storage import helpers as storage_helpers


logger = logging.getLogger(__name__)


def create_vm_with_disks(storage_domain, storage_type):
    """
    Creates a VM and installs system on it, create 7 disks and attach them to
    the VM

    Args:
        storage_domain (str): Name of the storage-domains
        storage_type (str): Storage domain type

    Returns:
        str: Name of the vm created
    """
    object_name = "%s_%s" % (storage_domain, storage_type)
    vm_name = storage_helpers.create_unique_object_name(
        object_name, config.OBJECT_TYPE_VM
    )
    unattached_disk = 'unattached_disk_%s' % storage_type
    vm_args = config.create_vm_args.copy()
    vm_args['vmName'] = vm_name
    vm_args['vmDescription'] = vm_name
    vm_args['storageDomainName'] = storage_domain
    vm_args['memory'] = 1 * config.GB
    vm_args['start'] = 'true'
    if not storage_helpers.create_vm_or_clone(**vm_args):
        raise exceptions.VMException(
            "Failed to create VM '%s'" % vm_name
        )

    config.DISKS_TO_PLUG.update({storage_type: []})
    for index in xrange(7):
        config.DISKS_TO_PLUG[storage_type].append(
            (
                "disk_to_plug_%s_%s" % (storage_type, str(index))
            )
        )

    config.UNATTACHED_DISKS_PER_STORAGE_TYPE.update({storage_type: []})
    config.UNATTACHED_DISKS_PER_STORAGE_TYPE[storage_type].append(
        unattached_disk
    )

    all_disks_to_add = (
        config.DISKS_TO_PLUG[storage_type] +
        config.UNATTACHED_DISKS_PER_STORAGE_TYPE[storage_type]
    )
    with ThreadPoolExecutor(max_workers=len(all_disks_to_add)) as executor:
        for disk_name in all_disks_to_add:
            disk_args_copy = config.disk_args.copy()
            disk_args_copy['alias'] = disk_name
            disk_args_copy['storagedomain'] = storage_domain
            executor.submit(ll_disks.addDisk(True, **disk_args_copy))

    ll_disks.wait_for_disks_status(
        all_disks_to_add, timeout=config.DISKS_WAIT_TIMEOUT
    )
    for disk_name in config.DISKS_TO_PLUG[storage_type]:
        ll_disks.attachDisk(True, disk_name, vm_name, False)

    return vm_name


def create_local_files_with_hooks():
    """
    Creates all the hook files locally, in the tests these files are copied
    over
    """
    with open(config.HOOKFILENAME, "w+") as handle:
        handle.write("#!/bin/bash\nuuidgen>> %s\n" % config.FILE_WITH_RESULTS)

    # Easy hook with sleep
    with open(config.HOOKWITHSLEEPFILENAME, "w+") as handle:
        handle.write(
            "#!/bin/bash\nsleep 30s\nuuidgen>> %s\n" %
            config.FILE_WITH_RESULTS
        )

    # Hook with print 'Hello World!'
    with open(config.HOOKPRINTFILENAME, "w+") as handle:
        handle.write(
            "#!/bin/bash\necho %s>> %s\n" %
            (config.TEXT, config.FILE_WITH_RESULTS)
        )

    # jpeg file
    with open(config.HOOKJPEG, "w+") as handle:
        handle.write(config.ONE_PIXEL_FILE)


def remove_hook_files():
    """
    removes all the local copies of the hook files
    """
    os.remove(config.HOOKFILENAME)
    os.remove(config.HOOKWITHSLEEPFILENAME)
    os.remove(config.HOOKPRINTFILENAME)
    os.remove(config.HOOKJPEG)


def create_vm_from_template(class_name, storage_domain, storage_type):
    """
    Clones a VM from the template of the given image name with class name as
    part of the VM name

    Args:
        class_name (str): Polarion test case id
        storage_domain (str): Name of the storage-domain
        storage_type (str): Storage domain type

    Returns:
        str: created VM name
    """
    vm_name = config.CLASS_VM_NAME_FORMAT % (class_name, storage_type)
    vm_args = config.create_vm_args.copy()
    vm_args['vmName'] = vm_name
    vm_args['vmDescription'] = vm_name
    vm_args['storageDomainName'] = storage_domain
    if not storage_helpers.create_vm_or_clone(**vm_args):
        raise exceptions.VMException(
            "Unable to clone vm %s from template" % vm_name
        )
    return vm_name


@ll_general.generate_logs(error=False)
def run_cmd(executor, cmd):
    """
    Run given command on a given machine

    Args:
        machine (machine object): Machine object to run command on
        cmd (str): Command to run on the given machine

    Returns:
        str: command's output
    """
    rc, out, error = executor.run_command(cmd)
    assert not rc, "Command %s failed, out: %s , error:%s" % (cmd, out, error)
    return out


def clear_hooks(executor):
    """
    Clear all VDSM hot(un)plug hook directories

    Args:
        machine (machine object): Machine object to run command on
    """
    for hook_dir in config.ALL_AVAILABLE_HOOKS:
        remote_hooks = os.path.join(config.MAIN_HOOK_DIR, hook_dir, '*')
        run_cmd(executor, ['rm', '-f', remote_hooks])
