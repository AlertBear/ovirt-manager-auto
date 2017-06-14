import logging
import shlex
from threading import Thread
from time import sleep

import config
from art.rhevm_api.tests_lib.low_level import (
    disks as ll_disks,
)
from art.rhevm_api.utils import log_listener

logger = logging.getLogger(__name__)


def get_first_ovf_store_id_and_obj(storage_domain):
    """
    Return the first encountered OVF store in the requested storage domain
    """
    all_disks = ll_disks.getStorageDomainDisks(storage_domain, False)
    for disk in all_disks:
        if disk.get_name() == config.OVF_STORE_DISK_NAME:
            # For block storage, the OVF store's LVM uses the Image
            # ID, in File the Disk ID is used as the folder and then the
            # Image ID is used for the 3 files (store, .meta, .lease)
            return {
                'id': disk.get_id(), 'img_id': disk.get_image_id(),
                'disk': disk
            }
    return None


def watch_engine_log_for_ovf_store(
    regex, vdsm_host, **function_name_and_args
):
    """
    Start a thread to watch the engine log for the regex requested, run the
    function with the parameters provided
    """
    t = Thread(
        target=log_listener.watch_logs,
        args=(
            config.ENGINE_LOG, regex, None, 120, config.VDC,
            config.VDC_ROOT_USER, config.VDC_PASSWORD, vdsm_host,
            config.HOSTS_USER, config.HOSTS_PW
        )
    )
    t.start()
    sleep(5)

    # Copy the dictionary passed in, remove the function_name so that only
    # function arguments remain
    function_args = function_name_and_args.copy()
    del function_args['function_name']
    status = function_name_and_args['function_name'](**function_args)
    t.join()
    return status


def get_ovf_file_path_and_num_ovf_files(
        host, is_block, disk_or_template_or_vm_name, vm_or_template_id, sd_id,
        ovf_id, sp_id="", ovf_filename=""
):
    """
    Extract OVF store, return the location of the OVF file matching the
    input parameters as well as the total number of OVF files contained in
    the OVF store

    Args:
        host (host): Host resource object to use to extract and return the OVF
            file path
        is_block (bool): Specifies whether storage type is block (True) or
            non-block (False)
        disk_or_template_or_vm_name (str): The disk alias which will be checked
            for within the OVF store of the specified VM or template
        vm_or_template_id (str): The VM or Template ID of the VM which
            contains the disk which will be queried
        sd_id (str): The Storage domain ID containing the disk being verified
        ovf_id (str): The OVF ID of the storage domain containing the disk
            being verified
        sp_id (str): Storage pool id (only needed for File)
        ovf_filename (str): The OVF store file name which will be copied
            and extracted to verify the VM OVF (only needed for File)

    Returns:
        str: The full path of the extracted OVF file name

    """
    # Add the default results
    error_result = None
    result = {'ovf_file_path': None, 'number_of_ovf_files': None}

    logger.info(
        "Attempt to remove the OVF store directory for the VM or Template if "
        "they were left over from a prior run"
    )
    remove_ovf_store_extracted(host, disk_or_template_or_vm_name)

    logger.info("Creating a directory to extract the OVF store")
    rc, output, error = host.run_command(
        shlex.split(
            config.CREATE_DIRECTORY_FOR_OVF_STORE % disk_or_template_or_vm_name
        )
    )
    if rc:
        return error_result

    if is_block:
        logger.info(
            "Activating the OVF store image before copying and extracting it"
        )
        refresh_volumes = host.lvm.pvscan()
        if not refresh_volumes:
            logger.error(
                "Unable to refresh the physical volumes on host '%s'", host
            )
            return error_result

        activate_lv_status = host.lvm.lvchange(sd_id, ovf_id, activate=True)
        if not activate_lv_status:
            logger.error(
                "Unable to activate the OVF Store LV in order to allow for "
                "it to be copied"
            )
            return error_result

        rc, output, error = host.run_command(
            shlex.split(
                config.BLOCK_COPY_OVF_STORE % (
                    sd_id, ovf_id, disk_or_template_or_vm_name
                )
            )
        )
        if rc:
            return error_result

        logger.info("Block OVF store, extracting OVF id '%s'", ovf_id)
        ovf_id_to_extract = ovf_id

    else:
        rc, output, error = host.run_command(
            shlex.split(
                config.FILE_COPY_OVF_STORE % (
                    sp_id, sd_id, ovf_id, ovf_filename,
                    disk_or_template_or_vm_name
                )
            )
        )
        if rc:
            return error_result

        logger.info("File OVF store, extracting OVF id '%s'", ovf_filename)
        ovf_id_to_extract = ovf_filename

    logger.info("Extracting the OVF store")
    rc, output, error = host.run_command(
        shlex.split(
            config.BLOCK_AND_FILE_EXTRACT_OVF_STORE % (
                disk_or_template_or_vm_name, ovf_id_to_extract
            )
        )
    )
    if rc:
        return error_result

    logger.info(
        "Retrieving the VM or Template's OVF file path on the host's file "
        "system"
    )
    ovf_file_path = config.EXTRACTED_OVF_FILE_LOCATION % (
        disk_or_template_or_vm_name, vm_or_template_id
    )
    result['ovf_file_path'] = ovf_file_path

    logger.info(
        "Retrieving the total number of OVF files extracted from the OVF store"
    )
    rc, number_of_ovf_files, error = host.run_command(
        shlex.split(
            config.COUNT_NUMBER_OF_OVF_FILES % disk_or_template_or_vm_name
        )
    )
    if rc:
        return error_result

    number_of_ovf_files = int(number_of_ovf_files)
    result['number_of_ovf_files'] = number_of_ovf_files
    logger.info(
        "Returning the extracted OVF file path '%s' and the total number of "
        "OVF files extracted from the OVF store '%s'",
        ovf_file_path, number_of_ovf_files
    )
    return result


def remove_ovf_store_extracted(host, disk_or_template_or_vm_name):
    """
    Remove the directory created as part of function
    get_ovf_file_path_and_num_ovf_files in order to extract the
    OVF store

    Args:
        host (host): Host resource object to use to remove the extracted OVF
            store
        disk_or_template_or_vm_name (str): The directory name of the extracted
            OVF store (either disk or template)
    """
    logger.info("Removing directory created to extract the OVF store")
    rc, output, error = host.run_command(
        shlex.split(
            config.REMOVE_DIRECTORY_FOR_OVF_STORE % disk_or_template_or_vm_name
        )
    )
    if rc:
        logger.info(
            "Failed to delete directory used for OVF store. The output is "
            "'%s' and the error is '%s'", output, error
        )


def move_ovf_store(vm_name, disk_name, disk_id):
    """
    Move OVF file to a different storage domain

    Args:
        vm_name (str): Name of the VM the disk is attached to
        disk_name (str): The name of the disk to move
        disk_id (str): The ID of the disk to move

    Raises:
        AssertionError: If moving the OVF file succeeded
    """
    dest_sd = ll_disks.get_other_storage_domain(disk_name, vm_name)
    assert ll_disks.move_disk(
        target_domain=dest_sd, disk_id=disk_id, positive=False
    ), "Move OVF store disk succeeded"


def delete_ovf_store_disk(disk_id):
    """
    Delete OVF disk

    Args:
        disk_id (str): OVF disk id to delete

    Raises:
        AssertionError: If OVF store disk deletion succeeds
    """
    assert ll_disks.deleteDisk(
        positive=False, alias=config.OVF_STORE_DISK_NAME,
        disk_id=disk_id
    ), "Delete OVF store disk succeeded"


def export_ovf_store_to_glance(disk_name):
    """
    Export OVF store disk to Glance domain

    Args:
        disk_name (str): The name of the disk to export

    Raises:
        AssertionError: If the export of the disk succeeded
    """
    assert ll_disks.export_disk_to_glance(
        True, disk_name, config.GLANCE_DOMAIN
    )
