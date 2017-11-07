# -*- coding: utf-8 -*-

"""
Pytest conftest for networking tests
"""

import pytest
import logging

logger = logging.getLogger(__name__)


@pytest.fixture(scope="session", autouse=True)
def prepare_env_networking(request):
    """
    Run network cleanup
    Create dummies interfaces on 2 hosts
    Run setup inventory
    """
    import config
    import helper
    import fixtures

    def fin():
        """
        Run teardown inventory
        """
        for vds_host in config.VDS_HOSTS[:2]:
            vds_host.cache.clear()
            logger.info("Deleting dummy interfaces from %s", vds_host.fqdn)
            helper.delete_dummies(host_resource=vds_host)
    request.addfinalizer(fin)

    pytest.config.hook.pytest_rhv_setup(team="network")
    for vds_host in config.VDS_HOSTS[:2]:
        vds_host.cache.clear()
        num_dummy = 30 if vds_host.fqdn == config.VDS_HOSTS[0].fqdn else 8
        helper.prepare_dummies(host_resource=vds_host, num_dummy=num_dummy)
        logger.info("Host %s. NICs: %s", vds_host.fqdn, vds_host.nics)
    fixtures.NetworkFixtures()
