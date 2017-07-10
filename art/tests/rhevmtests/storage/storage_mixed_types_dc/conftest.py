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
