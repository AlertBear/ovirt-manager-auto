# -*- coding: utf-8 -*-

"""
Pytest conftest file for storage tests
"""

import pytest


@pytest.fixture(scope="session", autouse=True)
def prepare_package_environment(request):
    """
    Prepare package environment
    """
    import config

    config.ISO_NFS_DOMAIN['address'] = config.NFS_DOMAINS_KWARGS[0]['address']
    config.ISO_NFS_DOMAIN['path'] = config.NFS_DOMAINS_KWARGS[0]['path']
    config.ISO_POSIX_DOMAIN['address'] = (
        config.NFS_DOMAINS_KWARGS[0]['address']
    )
    config.ISO_POSIX_DOMAIN['path'] = config.NFS_DOMAINS_KWARGS[0]['path']
    config.ISO_LOCAL_DOMAIN['path'] = config.LOCAL_DOMAINS[1]
    config.LOCAL_DOMAIN['path'] = config.LOCAL_DOMAINS[0]
    config.ISCSI_DOMAIN['lun'] = config.ISCSI_DOMAINS_KWARGS[0]['lun']
    config.ISCSI_DOMAIN['lun_address'] = (
        config.ISCSI_DOMAINS_KWARGS[0]['lun_address']
    )
    config.ISCSI_DOMAIN['lun_target'] = (
        config.ISCSI_DOMAINS_KWARGS[0]['lun_target']
    )
