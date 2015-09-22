from rhevmtests.storage import config


def assign_storgage_params(targets, keywords, *args):
    for i, target in enumerate(targets):
        for j, key in enumerate(keywords):
            target[key] = args[j][i]


def setup_package():
    config.FIRST_HOST = config.HOSTS[0]
    assign_storgage_params(
        config.NFS_DOMAINS_KWARGS,
        ('address', 'path'),
        config.UNUSED_DATA_DOMAIN_ADDRESSES,
        config.UNUSED_DATA_DOMAIN_PATHS,
    )
    assign_storgage_params(
        config.ISCSI_DOMAINS_KWARGS,
        ('lun_address', 'lun_target', 'lun'),
        config.UNUSED_LUN_ADDRESSES,
        config.UNUSED_LUN_TARGETS,
        config.UNUSED_LUNS,
    )
    assign_storgage_params(
        config.GLUSTER_DOMAINS_KWARGS,
        ('address', 'path'),
        config.UNUSED_GLUSTER_DATA_DOMAIN_ADDRESSES,
        config.UNUSED_GLUSTER_DATA_DOMAIN_PATHS,
    )
