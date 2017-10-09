# -*- coding: utf-8 -*-

"""
Pytest conftest file for storage tests
"""

import pytest


@pytest.fixture(scope="session", autouse=True)
def prepare_env_storage(request):
    """
    Prepare env
    """
    from rhevmtests.storage import config
    from rhevmtests.storage.helpers import assign_storage_params

    def fin():
        """
        Run teardown inventory
        """
        pytest.config.hook.pytest_rhv_teardown(team="storage")
    request.addfinalizer(fin)

    pytest.config.hook.pytest_rhv_setup(team="storage")

    config.FIRST_HOST = config.HOSTS[0]
    assign_storage_params(
        config.NFS_DOMAINS_KWARGS,
        ('address', 'path'),
        config.UNUSED_DATA_DOMAIN_ADDRESSES,
        config.UNUSED_DATA_DOMAIN_PATHS,
    )
    assign_storage_params(
        config.ISCSI_DOMAINS_KWARGS,
        ('lun_address', 'lun_target', 'lun'),
        config.UNUSED_LUN_ADDRESSES,
        config.UNUSED_LUN_TARGETS,
        config.UNUSED_LUNS,
    )
    assign_storage_params(
        config.GLUSTER_DOMAINS_KWARGS,
        ('address', 'path'),
        config.UNUSED_GLUSTER_DATA_DOMAIN_ADDRESSES,
        config.UNUSED_GLUSTER_DATA_DOMAIN_PATHS,
    )
    assign_storage_params(
        config.FC_DOMAINS_KWARGS,
        ('fc_lun',),
        config.UNUSED_FC_LUNS,
    )
