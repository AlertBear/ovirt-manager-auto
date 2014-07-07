"""
-----------------
test_users_and_roles
-----------------

@author: Nelly Credi
"""

import logging

from nose.tools import istest
from art.unittest_lib import attr
from art.test_handler.settings import opts

from art.unittest_lib import BaseTestCase as TestCase
from art.rhevm_api.tests_lib.low_level import users, tags, general, mla
from art.rhevm_api.utils.xpath_utils import XPathMatch
from art.core_api.apis_exceptions import EngineTypeError
from art.test_handler.tools import bz as bzd  # pylint: disable=E0611

from .. import config

logger = logging.getLogger(__name__)
ENUMS = config.ENUMS
PERMITS = config.PERMITS
NFS = opts['elements_conf']['RHEVM Enums']['storage_type_nfs']


@attr(team='automationInfra', tier=0)
class TestCaseUserAndRoles(TestCase):
    """
    Scenario tests
    """

    __test__ = (NFS in opts['storages'])

    storages = set([NFS])

    bz = {'1213393': {'engine': ['cli'], 'version': ['3.6']}}

    @classmethod
    def setup_class(cls):
        status = users.addExternalUser(
            positive=True,
            user_name=config.USER_VDCADMIN,
            principal=config.USER_VDCADMIN,
            domain=config.USER_DOMAIN,
        )
        assert status, 'Create user %s' % config.USER_VDCADMIN

    @classmethod
    def teardown_class(cls):
        status = users.removeUser(
            positive=True,
            user=config.USER_VDCADMIN_NAME,
        )
        assert status, 'Remove user %s' % config.USER_VDCADMIN_NAME

    @istest
    def t01_check_everyone_group_exists(self):
        """
        test verifies group functionality
        test checks whether 'Everyone' group exists
        """
        logger.info('Check \'Everyone\' group exists')
        status = users.groupExists(positive=True, group_name='Everyone')
        self.assertTrue(status, "Check 'Everyone' group exists")

    @istest
    def t02_delete_everyone_group(self):
        """
        test verifies group functionality
        test tries to delete 'Everyone' group & verifies failure
        """
        logger.info('Delete \'Everyone\' group')
        status = users.deleteGroup(positive=False, group_name='Everyone')
        self.assertTrue(status, "Delete 'Everyone' group failed as expected")

    @istest
    def t03_create_user_with_no_role(self):
        """
        test verifies users functionality
        test creates a user with no roles
        """
        logger.info('Create user')
        status = users.addExternalUser(
            positive=True,
            user_name=config.USER_NO_ROLES,
            principal=config.USER_NO_ROLES,
            domain=config.USER_DOMAIN,
        )
        self.assertTrue(status, 'Create user')

    @istest
    def t04_create_user(self):
        """
        test verifies users functionality
        test creates a user
        """
        logger.info('Create user')
        status = users.addExternalUser(
            positive=True,
            user_name=config.USERNAME,
            principal=config.USERNAME,
            domain=config.USER_DOMAIN,
        )
        self.assertTrue(status, 'Create user')

    @istest
    def t05_create_user_with_wrong_domain(self):
        """
        test verifies users functionality
        test creates a user with no roles
        """
        logger.info('Create user - wrong domain')
        status = users.addExternalUser(
            positive=False,
            domain='bad_config',
            principal=config.USERNAME,
            user_name=config.USERNAME,
        )
        self.assertTrue(status, 'Create user - wrong domain')

    @istest
    def t06_create_user_not_in_domain(self):
        """
        test verifies users functionality
        test creates a user which does not exists in domain
        """
        logger.info('Create user which does not exists in domain')
        status = users.addExternalUser(
            positive=False,
            domain=config.USER_DOMAIN,
            user_name=config.USER_NON_EXISTING,
            principal=config.USER_NON_EXISTING,
        )
        self.assertTrue(status, 'Create user which does not exists in domain')

    @istest
    def t07_add_tag_to_user(self):
        """
        test verifies users functionality
        test adds a tag to user
        """
        logger.info('Create tag')
        status = tags.addTag(positive=True, name=config.TAG_1_NAME)
        self.assertTrue(status, 'Create tag')
        logger.info('Add tag to user')
        status = users.addTagToUser(
            positive=True,
            user=config.USER_NO_ROLES_NAME,
            tag=config.TAG_1_NAME
        )
        self.assertTrue(status, 'Add tag to user')

    @istest
    def t08_check_system_summary(self):
        """
        test verifies users functionality
        test checks system summary
        """
        logger.info('Check system summary')
        status = general.checkSummary(positive=True, domain=config.USER_DOMAIN)
        self.assertTrue(status, 'Check system summary')

    @istest
    def t09_check_existing_permissions(self):
        """
        test verifies users functionality
        test checks existing permissions
        """
        logger.info('Check existing permissions')
        status = mla.checkSystemPermits(positive=True)
        self.assertTrue(status, 'Check existing permissions')

    @istest
    def t10_add_admin_role(self):
        """
        test verifies roles functionality
        test checks add admin role
        """
        logger.info('Add role')
        permits_str = ' '.join([PERMITS['create_vm_permit'],
                                PERMITS['create_host_permit'],
                                PERMITS['manipulate_roles_permit'],
                                PERMITS['delete_cluster_permit']])
        status = mla.addRole(positive=True, name='Admin_role',
                             administrative='true', permits=permits_str)
        self.assertTrue(status, 'Add role')

    @istest
    def t11_add_non_admin_role(self):
        """
        test verifies roles functionality
        test checks add role
        """
        logger.info('Add role')
        permits_str = ' '.join([PERMITS['create_vm_permit'],
                                PERMITS['migrate_vm_permit'],
                                PERMITS['delete_vm_permit']])
        status = mla.addRole(positive=True, name='User_role',
                             administrative='false', permits=permits_str)
        self.assertTrue(status, 'Add role')

    @istest
    def t12_remove_non_admin_role(self):
        """
        test verifies roles functionality
        test checks remove non admin role
        """
        logger.info('Remove non admin role')
        status = mla.removeRole(positive=True, role='User_role')
        self.assertTrue(status, 'Remove non admin role')

    @istest
    def t13_add_role_with_admin_permits(self):
        """
        test verifies roles functionality
        test checks add role with admin permits & verifies failure
        """
        logger.info('Add role with admin permits fails as expected')
        permits_str = ' '.join([PERMITS['create_vm_permit'],
                                PERMITS['create_host_permit'],
                                PERMITS['manipulate_roles_permit'],
                                PERMITS['delete_cluster_permit']])
        status = mla.addRole(positive=False, name='Bad_role',
                             administrative='false', permits=permits_str)
        self.assertTrue(status, 'Add role with admin permits')

    @istest
    def t14_add_permissions_to_role(self):
        """
        test verifies roles functionality
        test checks add permissions to existing role
        """
        logger.info('Add permissions to existing role')
        status = mla.addRolePermissions(
            positive=True, role='Admin_role',
            permit=PERMITS['create_storage_domain_permit'])
        self.assertTrue(status, 'Add permissions to existing role')

    @istest
    def t15_remove_permissions_from_role(self):
        """
        test verifies roles functionality
        test checks remove permissions from existing role
        """
        logger.info('Remove permissions from existing role')
        status = mla.removeRolePermissions(
            positive=True, role='Admin_role',
            permit=PERMITS['create_storage_domain_permit'])
        self.assertTrue(status, 'Remove permissions from existing role')

    @istest
    def t16_remove_admin_role(self):
        """
        test verifies roles functionality
        test checks remove role
        """
        logger.info('Remove admin role')
        status = mla.removeRole(positive=True, role='Admin_role')
        self.assertTrue(status, 'Remove admin role')

    @istest
    def t17_remove_system_role(self):
        """
        test verifies roles functionality
        test checks remove system role
        """
        logger.info('Remove system role')
        status = mla.removeRole(positive=False, role='HostAdmin')
        self.assertTrue(status, 'Remove system role')

    @istest
    def t18_add_permissions_to_system_role(self):
        """
        test verifies roles functionality
        test checks add permissions to system role & verifies failure
        """
        logger.info('Add permissions to system role')
        status = mla.addRolePermissions(
            positive=False, role='HostAdmin',
            permit=PERMITS['create_storage_domain_permit'])
        self.assertTrue(status, 'Add permissions to system role')

    @istest
    def t19_remove_permissions_from_system_role(self):
        """
        test verifies roles functionality
        test checks remove permissions from system role
        """
        logger.info('Remove permissions from system role')
        status = mla.removeRolePermissions(
            positive=False, role='StorageAdmin',
            permit=PERMITS['create_storage_domain_permit'])
        self.assertTrue(status, 'Remove permissions from system role')

    @istest
    def t20_add_vm_permissions_to_user(self):
        """
        test verifies roles functionality
        test checks add vm permissions to user
        """
        logger.info('Add vm permissions to user')
        status = mla.addVMPermissionsToUser(
            positive=True, user=config.USERNAME_NAME, vm=config.VM_NAME)
        self.assertTrue(status, 'Add vm permissions to user')

    @istest
    def t21_add_host_permissions_to_user(self):
        """
        test verifies roles functionality
        test checks add host permissions to user
        """
        logger.info('Add host permissions to user')
        status = mla.addHostPermissionsToUser(
            positive=True, user=config.USERNAME_NAME, host=config.HOST_NAME)
        self.assertTrue(status, 'Add host permissions to user')

    @istest
    @bzd({'1193848': {'engine': ['sdk'], 'version': ['3.5']}})
    def t22_add_storage_permissions_to_user(self):
        """
        test verifies roles functionality
        test checks add storage permissions to user
        """
        logger.info('Add storage permissions to user')
        status = mla.addStoragePermissionsToUser(
            positive=True, user=config.USERNAME_NAME,
            storage=config.STORAGE_DOMAIN_NAME)
        self.assertTrue(status, 'Add storage permissions to user')

    @istest
    def t23_add_cluster_permissions_to_user(self):
        """
        test verifies roles functionality
        test checks add cluster permissions to user
        """
        logger.info('Add cluster permissions to user')
        status = mla.addClusterPermissionsToUser(
            positive=True, user=config.USERNAME_NAME,
            cluster=config.CLUSTER_1_NAME)
        self.assertTrue(status, 'Add cluster permissions to user')

    @istest
    def t24_add_cluster_permissions_to_group(self):
        """
        test verifies roles functionality
        test checks add cluster permissions to group
        """
        logger.info('Add cluster permissions to group')
        status = mla.addClusterPermissionsToGroup(
            positive=True, group=config.GROUP,
            cluster=config.CLUSTER_1_NAME)
        self.assertTrue(status, 'Add cluster permissions to group')

    @istest
    def t25_add_template_permissions_to_user(self):
        """
        test verifies roles functionality
        test checks add template permissions to user
        """
        logger.info('Add template permissions to user')
        status = mla.addPermissionsForTemplate(
            positive=True, user=config.USERNAME_NAME,
            template=config.TEMPLATE_NAME)
        self.assertTrue(status, 'Add template permissions to user')

    @istest
    def t26_add_template_permissions_to_group(self):
        """
        test verifies roles functionality
        test checks add template permissions to group
        """
        logger.info('Add template permissions to group')
        status = mla.addPermissionsForTemplateToGroup(
            positive=True, group=config.GROUP,
            template=config.TEMPLATE_NAME)
        self.assertTrue(status, 'Add template permissions to group')

    @istest
    def t27_check_system_version_tag(self):
        """
        test verifies system version tag
        """
        logger.info('Check system version tag')
        status = general.checkSystemVersionTag(positive=True)
        self.assertTrue(status, 'Check system version tag')

    @istest
    def t28_check_definition_of_blank_template(self):
        """
        test verifies definition of blank template
        """
        logger.info('Check definition of blank template')
        xpathMatch = XPathMatch(general.util)
        expr = (
            'count(/api/special_objects/link[@rel="templates/blank" and '
            '@href="/%s/templates/00000000-0000-0000-0000-000000000000"])' %
            config.ENGINE_ENTRY_POINT
        )
        try:
            status = xpathMatch(True, 'api', expr)
            self.assertTrue(status, 'Check definition of blank template')
        except EngineTypeError:
            logger.info('xPath is only supported for rest')

    @istest
    def t29_check_definition_of_tag_root_object(self):
        """
        test verifies definition of tag root object
        """
        logger.info('Check definition of tag root object')
        xpathMatch = XPathMatch(general.util)
        expr = (
            'count(/api/special_objects/link[@rel="tags/root" and '
            '@href="/%s/tags/00000000-0000-0000-0000-000000000000"])' %
            config.ENGINE_ENTRY_POINT
        )
        try:
            status = xpathMatch(True, 'api', expr)
            self.assertTrue(status, 'Check definition of tag root object')
        except EngineTypeError:
            logger.info('xPath is only supported for rest')

    @istest
    def t30_remove_tag(self):
        """
        test verifies tags functionality
        the test removes tag
        """
        logger.info('Remove tag')
        status = tags.removeTag(positive=True, tag=config.TAG_1_NAME)
        self.assertTrue(status, 'Remove tag')

    @istest
    def t31_remove_users(self):
        """
        test verifies users functionality
        the test removes users
        """
        users_to_remove = [config.USER_NO_ROLES_NAME, config.USERNAME_NAME]
        for username in users_to_remove:
            logger.info('Remove user %s', username)
            status = users.removeUser(positive=True, user=username)
            self.assertTrue(status, 'Remove user ' + username)

    @istest
    def t32_check_user_properties_in_active_directory(self):
        """
        test verifies users functionality
        the test verifies user properties in active directory
        """
        logger.info('Check user properties in active directory')
        status = users.verifyADUserProperties(
            positive=True,
            domain=config.USER_DOMAIN,
            user=config.USER_VDCADMIN_NAME,
            expected_username='%s@%s' % (
                config.USER_VDCADMIN_NAME, config.USER_DOMAIN
            ),
            expected_department='Quality Assurance'
        )
        self.assertTrue(status, 'Check user properties in active directory')

    @istest
    def t33_search_user_in_active_directory_by_name(self):
        """
        test verifies users functionality
        the test searches a user by name in AD
        """
        logger.info('Search user by name in active directory')
        status = users.searchForUserInAD(
            positive=True,
            query_key='name',
            query_val=config.USER_VDCADMIN_NAME,
            key_name='name',
            domain=config.USER_DOMAIN
        )
        self.assertTrue(status, 'Search user by name in active directory')

    @istest
    def t34_search_user_in_active_directory_by_username(self):
        """
        test verifies users functionality
        the test searches a user by username in AD
        """
        logger.info('Search user by username in active directory')
        status = users.searchForUserInAD(
            positive=True,
            query_key='usrname',
            query_val=config.USER_VDCADMIN,
            key_name='user_name',
            domain=config.USER_DOMAIN
        )
        self.assertTrue(status, 'Search user by username in active directory')

    @bzd({'1211050': {'engine': None, 'version': ['3.6']}})
    @istest
    def t35_check_xsd_schema_validations(self):
        """
        test verifies xsd functionality
        the test checks xsd schema validations
        """
        logger.info('Check xsd schema validations')
        status = general.checkResponsesAreXsdValid()
        self.assertTrue(status, 'Check xsd schema validations')
