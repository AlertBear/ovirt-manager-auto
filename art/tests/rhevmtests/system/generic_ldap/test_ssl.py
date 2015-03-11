"""
Test possible configuration option of properties file.
"""
__test__ = True

import logging

from rhevmtests.system.generic_ldap import config, common
from art.rhevm_api.tests_lib.low_level import users
from art.unittest_lib import attr, CoreSystemTest as TestCase
from nose.tools import istest


LOGGER = logging.getLogger(__name__)


@attr(tier=0)
class ADTLS(TestCase):
    """
    Test if start tls connection to AD succeed.
    """
    __test__ = True
    conf = config.ADTLS_EXTENSION

    def setUp(self):
        for domain in config.ADW2K12_DOMAINS:
            principal = '%s@%s' % (config.ADW2k12_USER1, domain)
            common.assignUserPermissionsOnCluster(principal,
                                                  self.conf['authz_name'],
                                                  principal)

    @classmethod
    def teardown_class(cls):
        users.loginAsUser(config.VDC_ADMIN_USER, config.VDC_ADMIN_DOMAIN,
                          config.VDC_PASSWORD, False)
        for domain in config.ADW2K12_DOMAINS:
            principal = '%s@%s' % (config.ADW2k12_USER1, domain)
            assert users.removeUser(True, principal, cls.conf['authz_name'])

    @istest
    @common.check(config.EXTENSIONS)
    def adtls(self):
        """ active directory start tsl """
        for domain in config.ADW2K12_DOMAINS:
            principal = '%s@%s' % (config.ADW2k12_USER1, domain)
            users.loginAsUser(principal, self.conf['authn_name'],
                              config.ADW2k12_USER_PASSWORD, True)
            self.assertTrue(common.connectionTest(),
                            "User %s can't login." % principal)
