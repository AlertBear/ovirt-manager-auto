"""
3.5 Feature: Configuration for OVF on any domain feature
"""
from rhevmtests.storage.config import *  # flake8: noqa

# The 1st two VMs are used by the majority of tests, the 3rd is only used by
# tests that specifically require a new VM created as part of their validations
POOL_NAME = "storage_ovf_pool_6262"
POOL_SIZE = 5
POOL_DESCRIPTION = "storage_ovf_pool_6262_description"

if STORAGE_TYPE_ISCSI in STORAGE_SELECTOR:
    EXTEND_LUN_ADDRESS = UNUSED_LUN_ADDRESSES
    EXTEND_LUN_TARGET = UNUSED_LUN_TARGETS
    EXTEND_LUN = UNUSED_LUNS

SQL_MARK_AS_ILLEGAL = (
    "UPDATE images SET imagestatus=4 where image_group_id=\'%s\';"
)
ENGINE_REGEX_VM_NAME = (
    "START, SetVolumeDescriptionVDSCommand("".|\n)*"
    "imageGroupGUID=%s(.|\n)*"
    "description={""\"Updated\":true(.|\n)*"
    "FINISH, SetVolumeDescriptionVDSCommand"
)
UPDATE_OVF_INTERVAL_CMD = "OvfUpdateIntervalInMinutes=%(minutes)s"
UPDATE_OVF_NUM_OVF_STORES_CMD = "StorageDomainOvfStoreCount=%(num_ovf_stores)s"
UPDATED_NUM_OVF_STORES_PER_SD = 4
DEFAULT_NUM_OVF_STORES_PER_SD = 2
OVF_STORE_DISK_NAME = "OVF_STORE"
CREATE_DIRECTORY_FOR_OVF_STORE = 'mkdir -p /tmp/ovf/%s'
REMOVE_DIRECTORY_FOR_OVF_STORE = 'rm -rf /tmp/ovf/%s'
BLOCK_COPY_OVF_STORE = 'cp /dev/%s/%s /tmp/ovf/%s'
FILE_COPY_OVF_STORE = 'cp /rhev/data-center/%s/%s/images/%s/%s /tmp/ovf/%s'
BLOCK_AND_FILE_EXTRACT_OVF_STORE = 'cd /tmp/ovf/%s && tar -xvf %s'
EXTRACTED_OVF_FILE_LOCATION = "/tmp/ovf/%s/%s.ovf"
COUNT_NUMBER_OF_OVF_FILES = "ls /tmp/ovf/%s/*.ovf | wc -l"
OBJECT_NAME_IN_OVF = "<Name>%s</Name>"
# TODO: Restore timeout to 75 when OVF store update bug
# https://bugzilla.redhat.com/show_bug.cgi?id=1294447 is resolved
FIND_OVF_DISKS_TIMEOUT = 300
FIND_OVF_DISKS_SLEEP = 5
FIND_OVF_INFO_TIMEOUT = 300
FIND_OVF_INFO_SLEEP = 5
FIND_TEMPLATE_OVF_INFO_SLEEP = 120
ADD_DISK_PARAMS = {
        'shareable': True,
        'format': RAW_DISK,
        'sparse': False,
    }
