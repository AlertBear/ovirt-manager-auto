"""
Test possible configuration option of properties file.
"""
__test__ = True

from rhevmtests.system.aaa.ldap import config, common
from art.rhevm_api.tests_lib.low_level import users, mla
from art.test_handler.tools import polarion
from art.unittest_lib import attr, CoreSystemTest as TestCase


@attr(tier=2)
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

    @polarion('RHEVM3-8099')
    @common.check(config.EXTENSIONS)
    def test_adtls(self):
        """ active directory start tsl """
        for domain in config.ADW2K12_DOMAINS:
            principal = '%s@%s' % (config.ADW2k12_USER1, domain)
            users.loginAsUser(principal, self.conf['authn_name'],
                              config.ADW2k12_USER_PASSWORD, True)
            assert common.connectionTest(), "User %s can't login." % principal


@attr(tier=2)
class ADGroupWithSpacesInName(TestCase):
    """
    test login as user which is part of group with spaces in name
    Covers bz: https://bugzilla.redhat.com/show_bug.cgi?id=1186039
    """
    # They've decided to not fix, but I will let the case here for time
    # being as if some customer insist they will have to fix it.
    __test__ = False
    conf = config.ADTLS_EXTENSION
    group = config.ADW2k12_GROUP_SPACE
    princ = '%s@%s' % (config.ADW2k12_USER_SPACE, config.ADW2K12_DOMAINS[0])

    @classmethod
    def setup_class(cls):
        assert users.addGroup(True, cls.group, cls.conf['authz_name'])
        assert mla.addClusterPermissionsToGroup(
            True,
            cls.group,
            config.DEFAULT_CLUSTER_NAME
        )

    @classmethod
    def teardown_class(cls):
        users.loginAsUser(config.VDC_ADMIN_USER, config.VDC_ADMIN_DOMAIN,
                          config.VDC_PASSWORD, False)
        users.removeUser(True, cls.princ, cls.conf['authz_name'])
        users.deleteGroup(True, cls.group)

    @polarion('RHEVM3-12865')
    @common.check(config.EXTENSIONS)
    def test_group_with_spaces(self):
        """ test login as user which is part of group with spaces in name """
        users.loginAsUser(
            self.princ,
            self.conf['authn_name'],
            config.ADW2k12_USER_PASSWORD,
            True,
        )
        assert common.connectionTest(), "User %s can't login." % self.princ
