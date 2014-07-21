"""
Config module for storage sanity tests
"""
__test__ = False


from rhevmtests.storage.config import *  # flake8: noqa

EXTEND_LUN = PARAMETERS.get('extend_lun', None)

DC_VERSIONS = PARAMETERS.as_list('dc_versions')
DC_UPGRADE_VERSIONS = PARAMETERS.as_list('dc_upgrade_versions')

# TODO: remove
VM_USER = VMS_LINUX_USER
VM_PASSWORD = VMS_LINUX_PW

TMP_CLUSTER_NAME = 'tmp_cluster'
