'''
Sanity testing of upgrade.
'''

import logging

from art.rhevm_api.tests_lib.high_level.datacenters import clean_datacenter
from art.rhevm_api.tests_lib.low_level.vms import removeVm, checkVMConnectivity
from art.test_handler.exceptions import VMException
from art.test_handler.tools import polarion
from art.unittest_lib import (
    IntegrationTest as TestCase,
    tier2,
)
from art.rhevm_api.utils.test_utils import get_api
from reports.sanity.test_local_installation_sanity import SanityServicesLogs

from rhevm_upgrade import config
from config import non_ge

logger = logging.getLogger(__name__)
domUtil = get_api('domain', 'domains')
userUtil = get_api('user', 'users')


def teardown_module():
    """
    Clean datacenter
    """
    clean_datacenter(True, config.DC_NAME, engine=config.ENGINE)
    logger.debug("tearDownClass: cleaned the DC")


@non_ge
@tier2
class UpgradeSanityVerification(TestCase):
    """ Basic test """
    __test__ = True

    @classmethod
    def teardown_class(cls):
        if not removeVm(positive=True, vm=config.VM_NAME, stopVM='true'):
            raise VMException("Cannot remove vm %s" % config.VM_NAME)
        logger.info("Successfully removed %s.", config.VM_NAME)

    @polarion('RHEVM3-8127')
    def test_post_upgrade(self):
        """ Run tests after the upgrade """
        logger.debug("post-upgrade tests")
        assert checkVMConnectivity(True, config.VM_NAME, 'rhel',
                                   nic=config.NIC_NAME,
                                   user=config.VM_LINUX_USER,
                                   password=config.VMS_LINUX_PW)

    @polarion('RHEVM3-12864')
    def test_legacy_providers(self):
        """ test if legacy providers are accessible after upgrade """
        domains = domUtil.get(abs_link=False)
        for domain in domains:
            logger.info("Fetching users from domain %s", domain.name)
            users = userUtil.getElemFromLink(
                domain,
                link_name='users',
                attr='user',
                get_href=False
            )
            logger.debug(users)
            assert len(users) > 0, "Domain %s is not accesible." % domain.name
            logger.info("Domain %s is accessible.", domain.name)

    @polarion('RHEVM3-12080')
    def test_aaa_jdbc(self):
        """ test if after upgrade there aaa-jdbc installed and working """
        with config.ENGINE_HOST.executor().session() as ss:
            assert not ss.run_cmd([
                'yum',
                'list',
                'installed',
                'ovirt-engine-extension-aaa-jdbc',
            ])[0]
            assert not ss.run_cmd([
                'ovirt-aaa-jdbc-tool',
                'user',
                'show',
                'admin',
            ])[0]


@non_ge
@tier2
class UpgradeSanityDWHReports(SanityServicesLogs):
    pass
