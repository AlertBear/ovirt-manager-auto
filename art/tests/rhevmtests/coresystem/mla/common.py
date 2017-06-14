import logging

import pytest

from art.rhevm_api.tests_lib.low_level import (
    mla, templates, users, vms
)
from art.unittest_lib import CoreSystemTest as TestCase
from rhevmtests.coresystem.mla import config


logger = logging.getLogger(__name__)

ENUMS = config.ENUMS


class BaseTestCase(TestCase):
    @classmethod
    @pytest.fixture(autouse=True, scope="class")
    def setup_class(cls, request):
        login_as_admin()


def add_user(positive, user_name, domain):
    return users.addExternalUser(
        positive=positive,
        user_name="{0}@{1}".format(user_name, domain),
        principal=user_name,
        domain=domain,
    )


def login_as_admin():
    users.loginAsUser(
        config.VDC_ADMIN_USER,
        config.VDC_ADMIN_DOMAIN,
        config.VDC_PASSWORD,
        filter=False
    )


def login_as_user(user_name=config.USER_NAMES[0], filter_=True):
    users.loginAsUser(
        user_name,
        config.PROFILE,
        config.USER_PASSWORD,
        filter=filter_
    )


def check_if_object_has_role(obj, role, admin=None):
    """
    Check if given object has given role

    Args:
        obj (object): object you want to check for role existance
        role (str): role you want to check if object has
        admin (role): administrative role object

    Returns:
        bool: if object has role return True, if not - False
    """
    obj_permits = mla.permisUtil.getElemFromLink(obj, get_href=False)
    role_id = users.rlUtil.find(role).get_id()
    if admin is not None:
        perms_ids = [perm.get_role().get_id() for perm in obj_permits]
        is_in = role_id in perms_ids
        return (not admin) == is_in
    return role_id in [perm.get_role().get_id() for perm in obj_permits]


def compare_permissions(exists, user_name, roles_list, predefined):
    """
    Checks if given list of user roles is equal to predefined
    list of roles.

    Args:
        exists (bool): expected result
        user_name (str): user name
        roles_list (dict): dictionary of roles (user -> list(roles))
        predefined (list[str]): dictionary of expected roles

    Returns:
         None
    """
    msg = "\nPermission copied for user %s are:\n%s\nshould be:\n%s"
    logger.info(
        msg,
        user_name,
        roles_list[user_name],
        predefined if exists else []
    )
    if not exists:
        assert len(roles_list[user_name]) == 0
        return

    assert set(roles_list[user_name]) == set(predefined) and len(
        roles_list[user_name]) == len(predefined)


def check_for_vm_permissions(exists, user_one_roles, user_two_roles):
    """
    Check if users have vm permissions

    Args:
        exists (bool): something
        user_one_roles (list[str]): First user roles to test
        user_two_roles (list[str]): Second user roles to test

    Returns:
        None: this function invokes compare_permissions function
    """
    vm_perms = dict(zip(config.USER_NAMES[:2], [[], []]))
    vm_id = vms.VM_API.find(config.VM_NAMES[0]).get_id()

    for user_name in config.USER_NAMES[:2]:
        user = users.util.find(user_name)
        obj_permits = mla.permisUtil.getElemFromLink(user, get_href=False)

        for perm in obj_permits:
            if perm.get_vm() and perm.get_vm().get_id() == vm_id:
                role = users.rlUtil.find(perm.get_role().get_id(), "id")
                vm_perms[user_name].append(role.get_name())

    compare_permissions(
        exists,
        config.USER_NAMES[0],
        vm_perms,
        user_one_roles
    )
    compare_permissions(
        exists,
        config.USER_NAMES[1],
        vm_perms,
        user_two_roles
    )


def check_for_template_permissions(exists, user_one_roles, user_two_roles):
    """
    Check if users have template permissions

    Args:
        exists (bool): something
        user_one_roles (list[str]): First user roles to test
        user_two_roles (list[str]): Second user roles to test

    Returns:
        None: this function invokes compare_permissions function
    """
    template_perms = dict(zip(config.USER_NAMES[:2], [[], []]))
    tmp_id = templates.TEMPLATE_API.find(config.TEMPLATE_NAMES[1]).get_id()

    for user_name in config.USER_NAMES[:2]:
        user = users.util.find(user_name)
        obj_permits = mla.permisUtil.getElemFromLink(user, get_href=False)

        for perm in obj_permits:
            if perm.get_template() and perm.get_template().get_id() == tmp_id:
                role = users.rlUtil.find(perm.get_role().get_id(), "id")
                template_perms[user_name].append(role.get_name())

    compare_permissions(
        exists,
        config.USER_NAMES[0],
        template_perms,
        user_one_roles
    )
    compare_permissions(
        exists,
        config.USER_NAMES[1],
        template_perms,
        user_two_roles
    )
