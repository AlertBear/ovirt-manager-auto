'''
Sanity testing of upgrade.
'''

import logging

from art.rhevm_api.tests_lib.high_level.datacenters import clean_datacenter
from art.rhevm_api.tests_lib.low_level.vms import removeVm, checkVMConnectivity
from art.test_handler.exceptions import VMException
from art.test_handler.tools import polarion  # pylint: disable=E0611
from art.unittest_lib import CoreSystemTest as TestCase
from art.unittest_lib import attr
from art.rhevm_api.utils.test_utils import get_api

from rhevm_upgrade import config

LOGGER = logging.getLogger(__name__)
domUtil = get_api('domain', 'domains')
userUtil = get_api('user', 'users')


def teardown_module():
    """
    Clean datacenter
    """
    clean_datacenter(
        True, config.DC_NAME, vdc=config.VDC,
        vdc_password=config.VDC_PASSWORD
    )
    LOGGER.debug("tearDownClass: cleaned the DC")


@attr(tier=2)
class UpgradeSanityVerification(TestCase):
    """ Basic test """
    __test__ = True

    @classmethod
    def tearDownClass(cls):
        if not removeVm(positive=True, vm=config.VM_NAME, stopVM='true'):
            raise VMException("Cannot remove vm %s" % config.VM_NAME)
        LOGGER.info("Successfully removed %s.", config.VM_NAME)

    @polarion('RHEVM3-8127')
    def test_post_upgrade(self):
        """ Run tests after the upgrade """
        LOGGER.debug("post-upgrade tests")
        assert checkVMConnectivity(True, config.VM_NAME, 'rhel',
                                   nic=config.NIC_NAME,
                                   user=config.VM_LINUX_USER,
                                   password=config.VMS_LINUX_PW)

    @polarion('RHEVM3-12864')
    def test_legacy_providers(self):
        """ test if legacy providers are accessible after upgrade """
        domains = domUtil.get(absLink=False)
        for domain in domains:
            LOGGER.info("Fetching users from domain %s", domain.name)
            users = userUtil.getElemFromLink(
                domain,
                link_name='users',
                attr='user',
                get_href=False
            )
            LOGGER.debug(users)
            assert len(users) > 0, "Domain %s is not accesible." % domain.name
            LOGGER.info("Domain %s is accessible.", domain.name)

    @polarion('RHEVM3-12080')
    def test_aaa_jdbc(self):
        """ test if after upgrade there aaa-jdbc installed and working """
        with config.ENGINE_HOST.executor().session() as ss:
            assert not ss.run_cmd([
                'yum',
                'list',
                'installed',
                'ovirt-engine-extension-aaa-jdbc',
            ])
            assert not ss.run_cmd([
                'ovirt-aaa-jdbc-tool',
                'user',
                'show',
                'admin',
            ])
