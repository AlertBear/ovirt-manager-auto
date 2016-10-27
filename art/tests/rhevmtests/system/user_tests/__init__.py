import logging

from art.rhevm_api.utils.enginecli import EngineCLI
from art.rhevm_api.tests_lib.low_level import mla as ll_mla
from art.rhevm_api.tests_lib.low_level import storagedomains as ll_sd
from art.test_handler.tools import bz
from rhevmtests.system.user_tests import (
    config,
    test_user,
    test_admin,
    test_actions,
)

logger = logging.getLogger(__name__)


def get_action_groups(role_name):
    role_obj = ll_mla.util.find(role_name)
    permits = ll_mla.util.getElemFromLink(
        role_obj,
        link_name='permits',
        attr='permit'
    )
    return [p.get_name() for p in permits]

"""
    Code below will create for each module(test_user, test_admin)
    class with specific role and set mandatory attributes.
    Then this class is injected into specific test module.
    ie:
    class UserRole_RoleActions(CaseRoleActions):
        role = role_name
        filter_ = filter_
        perms = role_actions
"""
allActions = get_action_groups('SuperUser')
bzs = {
    '1209505': {
        'PowerUserRole': ['create_disk', 'create_template'],
        'TemplateCreator': ['create_template'],
        'TemplateAdmin': ['create_template'],
        'VmPoolAdmin': [
            'create_vm_pool',
            'edit_vm_pool_configuration',
        ],
    },
}

for role in ll_mla.util.get(absLink=False):
    role_name = role.get_name()
    filter_ = not role.get_administrative()
    role_actions = get_action_groups(role_name)
    if 'login' not in role_actions:
        continue

    case = test_actions.CaseRoleActions
    case_name = test_actions.CaseRoleActions.__name__[4:]
    role_case = type(
        '%s_%s' % (role_name, case_name),
        (case,),
        {
            'role': role_name,
            'filter_': filter_,
            'perms': role_actions,
            '__test__': True,
        }
    )

    module = test_user if filter_ else test_admin
    setattr(module, '%s_%s' % (role_name, case_name), role_case)
    """ Assign bz to specific cases """
    for bz_id, roles in bzs.iteritems():
        if role_name in roles:
            for perm in roles[role_name]:
                method_name = 'test_%s' % perm
                c = getattr(module, '%s_%s' % (role_name, case_name))
                m = getattr(c, method_name)
                bz({bz_id: {}})(m.__func__)

    role_case = None  # Need set to None, else it will be case of this module


TOOL = 'ovirt-aaa-jdbc-tool'


def setup_package():
    config.MASTER_STORAGE = ll_sd.get_master_storage_domain_name(
        config.DC_NAME[0]
    )
    with config.ENGINE_HOST.executor().session() as ss:
        user_cli = EngineCLI(tool=TOOL, session=ss).setup_module('user')
        for user in config.USERS[:-1]:
            # Workaround if environment is not clean
            try:
                user_cli.run("delete", user, )[0]
            except Exception as e:
                logger.warn("Caught exception %s" % e)
            assert user_cli.run(
                'add',
                user,
                attribute='firstName=%s' % user,
            )[0]
            assert user_cli.run(
                'password-reset',
                user,
                password='pass:%s' % config.USER_PASSWORD,
                password_valid_to='2050-01-01 00:00:00Z',
            )[0]


def teardown_package():
    with config.ENGINE_HOST.executor().session() as ss:
        user_cli = EngineCLI(tool=TOOL, session=ss).setup_module('user')
        for user in config.USERS[:-1]:
            assert user_cli.run(
                'delete',
                user,
            )[0]
