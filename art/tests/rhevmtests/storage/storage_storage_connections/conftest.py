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
    from art.rhevm_api.tests_lib.low_level import (
        hosts as ll_hosts,
    )
    config.HOST_FOR_MOUNT = config.HOSTS[-1]
    config.HOST_FOR_MOUNT_IP = ll_hosts.get_host_ip(config.HOST_FOR_MOUNT)
    config.HOSTS_FOR_TEST = config.HOSTS[:]
    config.HOSTS_FOR_TEST.remove(config.HOST_FOR_MOUNT)
    config.CONNECTIONS.append(config.ISCSI_STORAGE_ENTRIES.copy())
    config.CONNECTIONS.append(config.ISCSI_STORAGE_ENTRIES.copy())
    # After each test, we logout from all the targets by looping through
    # CONNECTIONS. Add the default target/ip so the host will also logout
    # from it
    config.CONNECTIONS.append({
        'lun_address': config.ISCSI_DOMAINS_KWARGS[0]['lun_address'],
        'lun_target':  config.ISCSI_DOMAINS_KWARGS[0]['lun_target'],
    })
