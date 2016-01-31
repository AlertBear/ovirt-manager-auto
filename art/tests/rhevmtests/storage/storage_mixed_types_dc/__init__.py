import config


def setup_package():
    import rhevmtests.helpers as rhevm_helpers
    rhevm_helpers.storage_cleanup()

    config.NFS_DOMAIN.update({
        'address': config.UNUSED_DATA_DOMAIN_ADDRESSES[0],
        'path': config.UNUSED_DATA_DOMAIN_PATHS[0],
    })
    config.ISCSI_DOMAIN_0.update({
        'lun': config.UNUSED_LUNS[0],
        'lun_address': config.UNUSED_LUN_ADDRESSES[0],
        'lun_target': config.UNUSED_LUN_TARGETS[0],
    })
    config.ISCSI_DOMAIN_1.update({
        'lun': config.UNUSED_LUNS[1],
        'lun_address': config.UNUSED_LUN_ADDRESSES[1],
        'lun_target': config.UNUSED_LUN_TARGETS[1],
    })
    config.GLUSTER_DOMAIN.update({
        'address': config.UNUSED_GLUSTER_DATA_DOMAIN_ADDRESSES[0],
        'path': config.UNUSED_GLUSTER_DATA_DOMAIN_PATHS[0],
    })

    config.POSIX_DOMAIN['address'] = config.UNUSED_DATA_DOMAIN_ADDRESSES[0]
    config.POSIX_DOMAIN['path'] = config.UNUSED_DATA_DOMAIN_PATHS[0]
