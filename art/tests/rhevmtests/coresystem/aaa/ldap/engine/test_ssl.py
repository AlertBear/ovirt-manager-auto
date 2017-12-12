"""
Test possible configuration option of properties file.
"""

import pytest

from art.rhevm_api.tests_lib.low_level import users, mla
from art.test_handler.tools import polarion
from art.unittest_lib import (
    tier2,
)
from art.unittest_lib import CoreSystemTest as TestCase, testflow

from rhevmtests.coresystem.aaa.ldap import config, common


@tier2
class TestADTLS(TestCase):
    """
    Test if start tls connection to AD succeed.
    """
    conf = config.ADTLS_EXTENSION

    @classmethod
    @pytest.fixture(autouse=True, scope="class")
    def setup_class(cls, request):
        def finalize():
            testflow.teardown("Tearing down class %s", cls.__name__)

            testflow.teardown("Login as user %s", config.VDC_ADMIN_USER)
            users.loginAsUser(
                config.VDC_ADMIN_USER,
                config.VDC_ADMIN_DOMAIN,
                config.VDC_PASSWORD,
                False,
            )

            testflow.teardown("Removing user %s", config.ADW2k12_USER1)
            for domain in config.ADW2K12_DOMAINS:
                principal = '%s@%s' % (config.ADW2k12_USER1, domain)
                assert users.removeUser(
                    True,
                    principal,
                    cls.conf['authz_name'],
                )

        request.addfinalizer(finalize)

        testflow.setup("Setting up class %s", cls.__name__)

        testflow.setup(
            "Assigning user permissions to user %s", config.ADW2k12_USER1
        )
        for domain in config.ADW2K12_DOMAINS:
            principal = '%s@%s' % (config.ADW2k12_USER1, domain)
            common.assignUserPermissionsOnCluster(
                principal,
                cls.conf['authz_name'],
                principal,
            )

    @polarion('RHEVM3-8099')
    @common.check(config.EXTENSIONS)
    def test_adtls(self):
        """ active directory start tsl """
        for domain in config.ADW2K12_DOMAINS:
            principal = '%s@%s' % (config.ADW2k12_USER1, domain)

            testflow.step("Login as user %s", config.ADW2k12_USER1)
            users.loginAsUser(
                principal,
                self.conf['authn_name'],
                config.ADW2k12_USER_PASSWORD,
                True,
            )

            testflow.step(
                "Testing connection with user %s", config.ADW2k12_USER1
            )
            assert common.connectionTest(), "User %s can't login." % principal


@tier2
class ADGroupWithSpacesInName(TestCase):
    """
    test login as user which is part of group with spaces in name
    Covers bz: https://bugzilla.redhat.com/show_bug.cgi?id=1186039
    """
    # They've decided to not fix, but I will let the case here for time
    # being as if some customer insist they will have to fix it.
    conf = config.ADTLS_EXTENSION
    group = config.ADW2k12_GROUP_SPACE
    princ = '%s@%s' % (config.ADW2k12_USER_SPACE, config.ADW2K12_DOMAINS[0])

    @classmethod
    @pytest.fixture(autouse=True, scope="class")
    def setup_class(cls, request):
        def finalize():
            testflow.teardown("Tearing down class %s", cls.__name__)

            testflow.teardown("Login as user %s", config.VDC_ADMIN_USER)
            users.loginAsUser(
                config.VDC_ADMIN_USER,
                config.VDC_ADMIN_DOMAIN,
                config.VDC_PASSWORD,
                False,
            )

            testflow.teardown("Removing user %s", cls.princ)
            assert users.removeUser(True, cls.princ, cls.conf['authz_name'])

            testflow.teardown("Removing group %s", cls.group)
            assert users.deleteGroup(True, cls.group)

        request.addfinalizer(finalize)

        testflow.setup("Setting up class %s", cls.__name__)

        testflow.setup("Adding group %s", cls.group)
        assert users.addGroup(True, cls.group, cls.conf['authz_name'])

        testflow.setup("Adding cluster permissions to group %s", cls.group)
        assert mla.addClusterPermissionsToGroup(
            True,
            cls.group,
            config.CLUSTER_NAME[0]
        )

    @polarion('RHEVM3-12865')
    @common.check(config.EXTENSIONS)
    def test_group_with_spaces(self):
        """ test login as user which is part of group with spaces in name """
        testflow.step("Login as user %s", self.princ)
        users.loginAsUser(
            self.princ,
            self.conf['authn_name'],
            config.ADW2k12_USER_PASSWORD,
            True,
        )

        testflow.step("Testing connection with user %s", self.princ)
        assert common.connectionTest(), "User %s can't login." % self.princ
