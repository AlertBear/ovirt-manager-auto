from rhevmtests.storage import config
import pytest


def assign_storgage_params(targets, keywords, *args):
    if len(args[0]) > 0:
        for i, target in enumerate(targets):
            for j, key in enumerate(keywords):
                target[key] = args[j][i]


def setup_package():
    pytest.config.hook.pytest_rhv_setup(team="storage")

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
    assign_storgage_params(
        config.FC_DOMAINS_KWARGS,
        ('fc_lun',),
        config.UNUSED_FC_LUNS,
    )


def teardown_package():
    """
    Run package teardown
    """
    pytest.config.hook.pytest_rhv_teardown(team="storage")
