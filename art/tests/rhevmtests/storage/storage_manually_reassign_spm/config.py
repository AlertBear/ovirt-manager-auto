from rhevmtests.storage.config import * # flake8: noqa

__test__ = False

# TODO: remvoe this
HOST_USER = HOSTS_USER
HOST_PASSWORD = HOSTS_PW
TESTNAME = 'manual_spm'

DEFAULT_SPM_PRIORITY = '5'
LOW_SPM_PRIORITY = '1'

# move all storage details to same keys from separated keys created by
# auto_devices, so all domains will be created by build_setup

# ISCSI
# TODO: how to handle this?
if not GOLDEN_ENV:
    if STORAGE_TYPE == ENUMS['storage_type_iscsi']:
        PARAMETERS['lun'] = [PARAMETERS['lun'], PARAMETERS['another_lun']]
        PARAMETERS['lun_address'] = [PARAMETERS['lun_address'],
                                     PARAMETERS['another_lun_address']]
        PARAMETERS['lun_target'] = [PARAMETERS['lun_target'],
                                    PARAMETERS['another_lun_target']]
    # NFS
    elif STORAGE_TYPE == ENUMS['storage_type_nfs']:
        PARAMETERS['data_domain_path'] = [
            PARAMETERS['data_domain_path'],
            PARAMETERS['another_data_domain_path'],
        ]
        PARAMETERS['data_domain_address'] = [
            PARAMETERS['data_domain_address'],
            PARAMETERS['another_data_domain_address'],
        ]
