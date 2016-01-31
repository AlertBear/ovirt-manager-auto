import config


def setup_package():
    import rhevmtests.helpers as rhevm_helpers
    rhevm_helpers.storage_cleanup()

    config.ISO_NFS_DOMAIN['address'] = config.ADDRESS[0]
    config.ISO_NFS_DOMAIN['path'] = config.PATH[0]

    config.ISO_POSIX_DOMAIN['address'] = config.ADDRESS[0]
    config.ISO_POSIX_DOMAIN['path'] = config.PATH[0]

    config.ISO_LOCAL_DOMAIN['path'] = config.LOCAL_DOMAINS[1]
    config.LOCAL_DOMAIN['path'] = config.LOCAL_DOMAINS[0]

    config.ISCSI_DOMAIN['lun'] = config.LUNS[0]
    config.ISCSI_DOMAIN['lun_address'] = config.LUN_ADDRESS[0]
    config.ISCSI_DOMAIN['lun_target'] = config.LUN_TARGET[0]
