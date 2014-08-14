""" Test configuration - login data to the servers and test setup options.  """
__test__ = False

from rhevmtests.system.config import *  # flake8:  noqa
from art.test_handler.settings import opts

ENUMS = opts['elements_conf']['RHEVM Enums']
CREATE_VM = 'auto_create_vm'
RUNNING_VM = 'auto_create_vm_running'
DELETE_VM = 'auto_delete_vm'
CREATE_TEMPLATE = 'auto_create_template'
CREATE_TEMPLATE_NIC1 = 'auto_create_template_nic1'
CREATE_TEMPLATE_NIC2 = 'auto_create_template_nic2'
DELETE_TEMPLATE = 'auto_delete_template'
CREATE_POOL = 'auto_create_pool'
DELETE_POOL = 'auto_delete_pool'
DELETE_DC = 'auto_delete_dc'
DELETE_DISK = 'auto_delete_disk'
DELETE_CLUSTER = 'auto_delete_cluster'
DELETE_SD = 'auto_delete_sd'
CREATE_ROLE = 'create_role'
UPDATE_ROLE = 'update_role'
PERMIT_LOGIN = 'login'
CREATE_USER = 'user1'
REMOVE_USER = 'user2'
EVERYONE_GROUP = 'Everyone'

USER_DOMAIN = 'brq-openldap.rhev.lab.eng.brq.redhat.com'
USER_PASSWORD = '123456'
USER_SYSTEM = 'auto_user_system'
USER_DC = 'auto_user_dc'
USER_CLUSTER = 'auto_user_cluster'
USER_STORAGE = 'auto_user_storage'
USER_VM = 'auto_user_vm'
USER_TEST = 'user3'
USERS = [USER_SYSTEM, USER_DC, USER_CLUSTER, USER_STORAGE, USER_VM, USER_TEST]

UserVmManager = ENUMS['role_name_user_vm_manager']
UserTemplateBasedVm = ENUMS['role_name_user_template_based_vm']
UserRole = ENUMS['role_name_user_role']

MASTER_STORAGE = None