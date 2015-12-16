import config


def setup_package():
    if not config.GOLDEN_ENV:
        config.NFS_DOMAIN.update({
            'address': config.ADDRESS[0],
            'path': config.PATH[0],
        })
        config.ISCSI_DOMAIN_0.update({
            'lun': config.LUN[0],
            'lun_address': config.LUN_ADDRESS[0],
            'lun_target': config.LUN_TARGET[0],
        })
        config.ISCSI_DOMAIN_1.update({
            'lun': config.LUN[1],
            'lun_address': config.LUN_ADDRESS[1],
            'lun_target': config.LUN_TARGET[1],
        })
        config.GLUSTER_DOMAIN.update({
            'address': config.GLUSTER_ADDRESS[0],
            'path': config.GLUSTER_PATH[0],
        })
    else:
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
