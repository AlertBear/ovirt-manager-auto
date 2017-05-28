#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Pytest conftest for networking tests
"""

import pytest
import logging

logger = logging.getLogger("GE_Network_cleanup")


@pytest.fixture(scope="session", autouse=True)
def prepare_env_networking(request):
    """
    Run network cleanup
    Create dummies interfaces on 2 hosts
    """
    from art.rhevm_api.utils.inventory import Inventory
    from rhevmtests.networking import config
    from rhevmtests.networking.helper import prepare_dummies, network_cleanup

    def finalizer():
        """
        Run inventory
        Remove dummies interfaces
        """
        network_cleanup()
        reporter = Inventory.get_instance()
        reporter.get_setup_inventory_report(
            print_report=True,
            check_inventory=True,
            rhevm_config_file=config
        )
    request.addfinalizer(finalizer)

    network_cleanup()
    for vds_host in config.VDS_HOSTS[:2]:
        num_dummy = 30 if vds_host.fqdn == config.VDS_HOSTS[0].fqdn else 8
        prepare_dummies(host_resource=vds_host, num_dummy=num_dummy)
        logger.info("Host %s. NICs: %s", vds_host.fqdn, vds_host.nics)
