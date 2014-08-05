'''
Testing copy permissions feauture.
1 Host, 1 DC, 1 Cluster, 1 SD will be created.
Every case create vm/template and check if permissions from it are/aren't
copied, when copy_permissions flag is/isn't provided.
'''

__test__ = True

import logging
from art.unittest_lib import BaseTestCase as TestCase
from nose.tools import istest
from rhevmtests.system.user_roles_tests import config
from rhevmtests.system.user_roles_tests.roles import role
from art.test_handler.tools import tcms
from art.rhevm_api.tests_lib.low_level import vms, users, templates, mla

TCMS_PLAN_ID = '9798'
LOGGER = logging.getLogger(__name__)

USER1_VM_ROLES = [role.UserRole, role.PowerUserRole]
USER2_VM_ROLES = [role.TemplateAdmin]
USER1_TEMPLATE_ROLES = [role.UserRole, role.UserTemplateBasedVm,
                        role.TemplateAdmin]
USER2_TEMPLATE_ROLES = [role.TemplateOwner, role.DiskCreator]


def setUpModule():
    users.addUser(True, user_name=config.USER_NAME, domain=config.USER_DOMAIN)
    users.addUser(True, user_name=config.USER_NAME2, domain=config.USER_DOMAIN)
    vms.createVm(True, config.VM_NAME, '', cluster=config.MAIN_CLUSTER_NAME,
                 storageDomainName=config.MAIN_STORAGE_NAME, size=config.GB,
                 network=config.MGMT_BRIDGE)
    templates.createTemplate(True, vm=config.VM_NAME,
                             name=config.TEMPLATE_NAME,
                             cluster=config.MAIN_CLUSTER_NAME)

    # ## Add permissions to vm ##
    # ClusterAdmin role on cluster to user1 (should no be copied)
    mla.addClusterPermissionsToUser(True, config.USER_NAME,
                                    config.MAIN_CLUSTER_NAME)
    # ClusterAdmin role on cluster to user2 (should no be copied)
    mla.addClusterPermissionsToUser(True, config.USER_NAME2,
                                    config.MAIN_CLUSTER_NAME,
                                    role=role.UserRole)
    # Add UserRole on vm to user1 (should be copied)
    mla.addVMPermissionsToUser(True, config.USER_NAME, config.VM_NAME,
                               role=role.UserRole)
    # Add UserTemplateBasedVm on vm to user1 (should be copied)
    mla.addVMPermissionsToUser(True, config.USER_NAME, config.VM_NAME,
                               role=role.UserTemplateBasedVm)
    # Add TemplateAdmin on vm to user1 (should be copied)
    mla.addVMPermissionsToUser(True, config.USER_NAME, config.VM_NAME,
                               role=role.TemplateAdmin)
    # Add TemplateAdmin on vm to user2 (should be copied)
    mla.addVMPermissionsToUser(True, config.USER_NAME2, config.VM_NAME,
                               role=role.TemplateOwner)
    # Add DiskCreator on vm to user2 (should be copied)
    mla.addVMPermissionsToUser(True, config.USER_NAME2, config.VM_NAME,
                               role=role.DiskCreator)

    # ## Add permissions to template ##
    # PowerUserRole on template to user1 (should be copied)
    mla.addPermissionsForTemplate(True, config.USER_NAME, config.TEMPLATE_NAME,
                                  role=role.PowerUserRole)
    # UserRole on template to user1 (should be copied)
    mla.addPermissionsForTemplate(True, config.USER_NAME, config.TEMPLATE_NAME,
                                  role=role.UserRole)
    # TemplateAdmin on template to user2 (should be copied)
    mla.addPermissionsForTemplate(True, config.USER_NAME2,
                                  config.TEMPLATE_NAME,
                                  role=role.TemplateAdmin)
    # UserTemplateBasedVm on template to user1 (should not be copied)
    mla.addPermissionsForTemplate(True, config.USER_NAME, config.TEMPLATE_NAME,
                                  role=role.UserTemplateBasedVm)
    # TemplateOwner on template to user2 (should not be copied)
    mla.addPermissionsForTemplate(True, config.USER_NAME2,
                                  config.TEMPLATE_NAME,
                                  role=role.TemplateOwner)
    # DataCenterAdmin on template to user2 (should not be copied)
    mla.addPermissionsForDataCenter(True, config.USER_NAME2,
                                    config.MAIN_DC_NAME,
                                    role=role.DataCenterAdmin)


def tearDownModule():
    users.removeUser(True, config.USER_NAME)
    users.removeUser(True, config.USER_NAME2)
    vms.removeVm(True, config.VM_NAME)
    templates.removeTemplate(True, config.TEMPLATE_NAME)


def _compare(exists, user_name, roles_list, predefined):
    msg = "\nPermission copied for user %s are:\n%s\nshould be:\n%s"
    LOGGER.info(msg % (user_name, roles_list[user_name],
                       predefined if exists else []))
    if not exists:
        assert len(roles_list[user_name]) == 0
        return

    assert set(roles_list[user_name]) == set(predefined) and \
        len(roles_list[user_name]) == len(predefined)


def checkForVmPermissions(exists):
    vm_perms = {config.USER_NAME: [], config.USER_NAME2: []}
    vm_id = vms.VM_API.find(config.VM_NAME1).get_id()

    for user_name in [config.USER_NAME, config.USER_NAME2]:
        user = users.util.find(user_name)
        objPermits = mla.permisUtil.getElemFromLink(user, get_href=False)

        for perm in objPermits:
            if perm.get_vm() and perm.get_vm().get_id() == vm_id:
                rl = users.rlUtil.find(perm.get_role().get_id(), 'id')
                vm_perms[user_name].append(rl.get_name())

    _compare(exists, config.USER_NAME, vm_perms, USER1_VM_ROLES)
    _compare(exists, config.USER_NAME2, vm_perms, USER2_VM_ROLES)


def checkForTemplatePermissions(exists):
    template_perms = {config.USER_NAME: [], config.USER_NAME2: []}
    tmp_id = templates.TEMPLATE_API.find(config.TEMPLATE_NAME2).get_id()

    for user_name in [config.USER_NAME, config.USER_NAME2]:
        user = users.util.find(user_name)
        objPermits = mla.permisUtil.getElemFromLink(user, get_href=False)

        for perm in objPermits:
            if perm.get_template() and perm.get_template().get_id() == tmp_id:
                rl = users.rlUtil.find(perm.get_role().get_id(), 'id')
                template_perms[user_name].append(rl.get_name())

    _compare(exists, config.USER_NAME, template_perms, USER1_TEMPLATE_ROLES)
    _compare(exists, config.USER_NAME2, template_perms, USER2_TEMPLATE_ROLES)


class CopyPermissions299326(TestCase):
    """ Check if permissions are copied to vm when enabled """
    __test__ = True

    @classmethod
    def setUpClass(self):
        vms.createVm(True, config.VM_NAME1, '', template=config.TEMPLATE_NAME,
                     cluster=config.MAIN_CLUSTER_NAME, copy_permissions=True,
                     network=config.MGMT_BRIDGE)

    @istest
    @tcms(TCMS_PLAN_ID, '299326')
    def createVmWithCopyPermissionsOption(self):
        """ create vm with copy permissions option """
        checkForVmPermissions(True)

    @classmethod
    def tearDownClass(self):
        vms.removeVm(True, config.VM_NAME1)


class CopyPermissions299330(TestCase):
    """ Check if permissions are copied to vm when disabled """
    __test__ = True

    @classmethod
    def setUpClass(self):
        vms.createVm(True, config.VM_NAME1, '', template=config.TEMPLATE_NAME,
                     cluster=config.MAIN_CLUSTER_NAME,
                     network=config.MGMT_BRIDGE)

    @istest
    @tcms(TCMS_PLAN_ID, '299330')
    def createVmWithoutCopyPermissionsOption(self):
        """ create vm without copy permissions option """
        checkForVmPermissions(False)

    @classmethod
    def tearDownClass(self):
        vms.removeVm(True, config.VM_NAME1)


class CopyPermissions299328(TestCase):
    """ Check if permissions are copied to template when enabled """
    __test__ = True

    @classmethod
    def setUpClass(self):
        templates.createTemplate(True, vm=config.VM_NAME,
                                 name=config.TEMPLATE_NAME2,
                                 cluster=config.MAIN_CLUSTER_NAME,
                                 copy_permissions=True)

    @istest
    @tcms(TCMS_PLAN_ID, '299328')
    def makeTemplateWithCopyPermissionsOption(self):
        """ make template with copy permissions option """
        checkForTemplatePermissions(True)

    @classmethod
    def tearDownClass(self):
        templates.removeTemplate(True, config.TEMPLATE_NAME2)


class CopyPermissions299331(TestCase):
    """ Check if permissions are not copied to template when disabled """
    __test__ = True

    @classmethod
    def setUpClass(self):
        templates.createTemplate(True, vm=config.VM_NAME,
                                 name=config.TEMPLATE_NAME2,
                                 cluster=config.MAIN_CLUSTER_NAME)

    @istest
    @tcms(TCMS_PLAN_ID, '299331')
    def makeTemplateWithoutCopyPermissionsOption(self):
        """ make template without copy permissions option """
        checkForTemplatePermissions(False)

    @classmethod
    def tearDownClass(self):
        templates.removeTemplate(True, config.TEMPLATE_NAME2)
