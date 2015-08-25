import logging
import shlex
from threading import Thread
from time import sleep

import config
from art.core_api.apis_utils import TimeoutingSampler
from art.rhevm_api.resources import storage as storage_resources
from art.rhevm_api.tests_lib.low_level import (
    datacenters, disks, hosts, storagedomains,
)
from art.rhevm_api.utils import log_listener
from art.test_handler import exceptions
from utilities.machine import LINUX, Machine

logger = logging.getLogger(__name__)

FIND_SDS_TIMEOUT = 10
SD_STATUS_OK_TIMEOUT = 15
SPM_TIMEOUT = 300
SPM_SLEEP = 5
OVF_STORE_DISK_NAME = "OVF_STORE"
FILE_OVF_STORE_PATH = 'ls /rhev/data-center/%s/%s/images/%s'
ACTIVATE_BLOCK_VOLUME = 'lvchange -ay /dev/%s/%s'
DEACTIVATE_BLOCK_VOLUME = 'lvchange -an /dev/%s/%s'
CREATE_DIRECTORY_FOR_OVF_STORE = 'mkdir -p /tmp/ovf/%s'
REMOVE_DIRECTORY_FOR_OVF_STORE = 'rm -rf /tmp/ovf/%s'
BLOCK_COPY_OVF_STORE = 'cp /dev/%s/%s /tmp/ovf/%s'
FILE_COPY_OVF_STORE = 'cp /rhev/data-center/%s/%s/images/%s/%s /tmp/ovf/%s'
BLOCK_AND_FILE_EXTRACT_OVF_STORE = 'cd /tmp/ovf/%s && tar -xvf %s'
EXTRACTED_OVF_FILE_LOCATION = "/tmp/ovf/%s/%s.ovf"
COUNT_NUMBER_OF_OVF_FILES = "ls /tmp/ovf/%s/*.ovf | wc -l"


def get_first_ovf_store_id_and_obj(storage_domain):
    """
    Return the first encountered OVF store in the requested storage domain
    """
    all_disks = disks.getStorageDomainDisks(storage_domain, False)
    for disk in all_disks:
        if disk.get_name() == OVF_STORE_DISK_NAME:
            # For block storage, the OVF store's LVM uses the Image
            # ID, in File the Disk ID is used as the folder and then the
            # Image ID is used for the 3 files (store, .meta, .lease)
            return {'id': disk.get_id(), 'img_id': disk.get_image_id(),
                    'disk': disk}
    return None


def get_master_storage_domain_name():
    """
    Return the master storage domain name
    """
    found, master_domain = storagedomains.findMasterStorageDomain(
        True, config.DATA_CENTER_NAME
    )
    if not found:
        return None
    return master_domain['masterDomain']


def watch_engine_log_for_ovf_store(regex, vdsm_host, **function_name_and_args):
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

    __author__ = "glazarov"
    :param host: Name of the host with which to extract and return the OVF
    file path
    :type host: str
    :param is_block: Specifies whether storage type is block (True) or
    non-block (False)
    :type is_block: bool
    :param disk_or_template_or_vm_name: The disk alias which will be checked
    for within the OVF store of the specified VM
    :type disk_or_template_or_vm_name: str
    :param vm_or_template_id: The VM or Template ID of the VM which
    contains the disk which will be queried
    :type vm_or_template_id: str
    :param sd_id: The Storage domain ID containing the disk being
    verified
    :type sd_id: str
    :param ovf_id: The OVF ID of the storage domain containing the disk
    being verified
    :type ovf_id: str
    :param sp_id: Storage pool id (only needed for File)
    :type sp_id: str
    :param ovf_filename: The OVF store file name which will be copied
    and extracted to verify the VM OVF (only needed for File)
    :type ovf_filename: str
    :returns: The full path of the extracted OVF file name
    :rtype: str
    """
    host_to_use = storage_resources.get_host_resource(host)

    # Add the default results
    error_result = None
    result = {'ovf_file_path': None, 'number_of_ovf_files': None}

    logger.info(
        "Attempt to remove the OVF store directory for the VM or Template if "
        "they were left over from a prior run"
    )
    remove_ovf_store_extracted(host, disk_or_template_or_vm_name)

    logger.info("Creating a directory to extract the OVF store")
    rc, output, error = host_to_use.executor().run_cmd(
        cmd=shlex.split(
            CREATE_DIRECTORY_FOR_OVF_STORE % disk_or_template_or_vm_name
        )
    )
    if rc:
        logger.error(
            "Error while creating directory for OVF store, output is '%s', "
            "error is '%s'", output, error
        )
        return error_result

    if is_block:
        logger.info("Activating the OVF store image before copying and "
                    "extracting it")
        refresh_volumes = storage_resources.run_pvscan_command(host)
        if not refresh_volumes:
            logger.error(
                "Unable to refresh the physical volumes on host '%s'", host
            )
            return error_result

        activate_lv_status = storage_resources.lv_change(
            host, sd_id, ovf_id, activate=True
        )
        if not activate_lv_status:
            logger.error(
                "Unable to activate the OVF Store LV in order to allow for "
                "it to be copied"
            )
            return error_result

        rc, output, error = host_to_use.executor().run_cmd(
            cmd=shlex.split(
                BLOCK_COPY_OVF_STORE % (
                    sd_id, ovf_id, disk_or_template_or_vm_name
                )
            )
        )
        if rc:
            logger.error(
                "Error while copying OVF store for processing, output is "
                "'%s', error is '%s'", output, error
            )
            return error_result

        logger.info("Block OVF store, extracting OVF id '%s'", ovf_id)
        ovf_id_to_extract = ovf_id

    else:
        rc, output, error = host_to_use.executor().run_cmd(
            cmd=shlex.split(
                FILE_COPY_OVF_STORE % (
                    sp_id, sd_id, ovf_id, ovf_filename,
                    disk_or_template_or_vm_name
                )
            )
        )
        if rc:
            logger.error(
                "Error while copying OVF store for processing, output is "
                "'%s', error is '%s'", output, error
            )
            return error_result

        logger.info("File OVF store, extracting OVF id '%s'", ovf_filename)
        ovf_id_to_extract = ovf_filename

    logger.info("Extracting the OVF store")
    rc, output, error = host_to_use.executor().run_cmd(
        cmd=shlex.split(
            BLOCK_AND_FILE_EXTRACT_OVF_STORE % (
                disk_or_template_or_vm_name, ovf_id_to_extract
            )
        )
    )
    if rc:
        logger.error(
            "Error while extracting OVF store for processing, output is "
            "'%s', error is '%s'", output, error
        )
        return error_result

    logger.info(
        "Retrieving the VM or Template's OVF file path on the host's file "
        "system"
    )
    ovf_file_path = EXTRACTED_OVF_FILE_LOCATION % (
        disk_or_template_or_vm_name, vm_or_template_id
    )
    result['ovf_file_path'] = ovf_file_path

    logger.info(
        "Retrieving the total number of OVF files extracted from the OVF store"
    )
    rc, number_of_ovf_files, error = host_to_use.executor().run_cmd(
        cmd=shlex.split(
            COUNT_NUMBER_OF_OVF_FILES % disk_or_template_or_vm_name
        )
    )
    if rc:
        logger.error(
            "Error while extracting OVF store for processing, output is "
            "'%s', error is '%s'", output, error
        )
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

    :param host: Name of the host with which to remove the extracted OVF store
    :type host: str
    :param disk_or_template_or_vm_name: The directory name of the extracted
    OVF store (either disk or template)
    :type disk_or_template_or_vm_name: str
    """
    host_to_use = storage_resources.get_host_resource(host)
    logger.info("Removing directory created to extract the OVF store")
    rc, output, error = host_to_use.executor().run_cmd(
        cmd=shlex.split(
            REMOVE_DIRECTORY_FOR_OVF_STORE % disk_or_template_or_vm_name
        )
    )
    if rc:
        logger.info(
            "Failed to delete directory used for OVF store. The output is "
            "'%s' and the error is '%s'", output, error
        )


def machine_to_use(host_ip):
    """
    Return a Machine object allowing to execute commands directly on the host

    __author__ = "glazarov"
    :param host_ip: The IP of the host which will be used to execute commands
    :type host_ip: str
    :returns: Machine object on which commands can be executed
    :rtype: Machine
    """
    return Machine(
        host=host_ip, user=config.HOSTS_USER, password=config.HOSTS_PW
    ).util(LINUX)


def ensure_data_center_and_sd_are_active():
    """
    Wait for the Data center to become active, for an SPM host selection and
    for at least one storage domain to become active
    """
    logger.info("Wait for the Data center to become active")
    if not datacenters.waitForDataCenterState(config.DATA_CENTER_NAME):
        raise exceptions.DataCenterException(
            "The Data center was not up within 3 minutes, aborting test"
        )

    if not hosts.waitForSPM(config.DATA_CENTER_NAME, SPM_TIMEOUT, SPM_SLEEP):
        raise exceptions.StorageDomainException(
            "SPM host was not elected within 5 minutes, aborting test"
        )

    logger.info(
        "Waiting up to %s seconds for at least one sd of type %s to show up",
        FIND_SDS_TIMEOUT, config.STORAGE_TYPE_NFS
    )
    for storage_domains in TimeoutingSampler(
            timeout=FIND_SDS_TIMEOUT, sleep=1,
            func=storagedomains.getStorageDomainNamesForType,
            datacenter_name=config.DATA_CENTER_NAME,
            storage_type=config.STORAGE_TYPE_NFS
    ):
        if storage_domains:
            break
    if not storage_domains:
        raise exceptions.StorageDomainException(
            "There were no iSCSI storage domains present in data center %s "
            "within 10 seconds" % config.DATA_CENTER_NAME
        )

    logger.info(
        "Waiting up to %s seconds for sd %s to be active",
        SD_STATUS_OK_TIMEOUT, storage_domains[0]
    )
    if not storagedomains.waitForStorageDomainStatus(
            True, config.DATA_CENTER_NAME, storage_domains[0],
            config.SD_ACTIVE, SD_STATUS_OK_TIMEOUT, 1):
        raise exceptions.StorageDomainException(
            "iSCSI domain '%s' has not reached %s state after 15 seconds" %
            (storage_domains[0], config.SD_ACTIVE)
        )
