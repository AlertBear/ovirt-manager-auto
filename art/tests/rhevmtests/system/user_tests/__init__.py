import test_user
import test_admin
import test_actions

from rhevmtests.system.user_tests import config
from art.rhevm_api.tests_lib.low_level import storagedomains, mla
from art.rhevm_api.tests_lib.high_level import datacenters


def get_action_groups(role_name):
    role_obj = mla.util.find(role_name)
    permits = mla.util.getElemFromLink(
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
for role in mla.util.get(absLink=False):
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
            'perms': role_actions
        }
    )

    module = test_user if filter_ else test_admin
    setattr(module, '%s_%s' % (role_name, case_name), role_case)


def setup_module():
    if not config.GOLDEN_ENV:
        datacenters.build_setup(config=config.PARAMETERS,
                                storage=config.PARAMETERS,
                                storage_type=config.STORAGE_TYPE,
                                basename=config.TEST_NAME)
    config.MASTER_STORAGE = storagedomains.get_master_storage_domain_name(
        config.DC_NAME[0]
    )


def teardown_module():
    if not config.GOLDEN_ENV:
        storagedomains.cleanDataCenter(True, config.DC_NAME[0],
                                       vdc=config.VDC_HOST,
                                       vdc_password=config.VDC_ROOT_PASSWORD)
