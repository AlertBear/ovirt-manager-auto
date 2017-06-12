import config


def setup_package():
    import rhevmtests.helpers as rhevm_helpers
    rhevm_helpers.storage_cleanup()

    config.NFS_DOMAIN.update({
        'address': config.NFS_DOMAINS_KWARGS[0]['address'],
        'path': config.NFS_DOMAINS_KWARGS[0]['path'],
    })
    config.ISCSI_DOMAIN_0.update({
        'lun': config.ISCSI_DOMAINS_KWARGS[0]['lun'],
        'lun_address': config.ISCSI_DOMAINS_KWARGS[0]['lun_address'],
        'lun_target': config.ISCSI_DOMAINS_KWARGS[0]['lun_target'],
    })
    config.ISCSI_DOMAIN_1.update({
        'lun': config.ISCSI_DOMAINS_KWARGS[1]['lun'],
        'lun_address': config.ISCSI_DOMAINS_KWARGS[1]['lun_address'],
        'lun_target': config.ISCSI_DOMAINS_KWARGS[1]['lun_target'],
    })
    config.GLUSTER_DOMAIN.update({
        'address': config.GLUSTER_DOMAINS_KWARGS[0]['address'],
        'path': config.GLUSTER_DOMAINS_KWARGS[0]['path'],
    })

    config.POSIX_DOMAIN['address'] = config.NFS_DOMAINS_KWARGS[0]['address']
    config.POSIX_DOMAIN['path'] = config.NFS_DOMAINS_KWARGS[0]['path']
