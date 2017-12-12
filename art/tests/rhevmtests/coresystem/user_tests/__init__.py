import copy
import logging
from functools import partial

from art.rhevm_api.tests_lib.low_level import mla as ll_mla

from art.test_handler.tools import bz

from rhevmtests.coresystem.user_tests import (
    test_user, test_admin, base
)

BASE_CLASS = base.CaseRoleActions


logger = logging.getLogger(__name__)


def add_bug(bug_id, roles, permits, bugs_dict=None):
    """
    Adds specific bugzilla id for user tests to given roles and permits.

    Args:
        bug_id (str): Bugzilla id to set.
        roles (list[str]): List of roles affected by bug.
        permits (list[str]): List of role permits affected by bug.
        bugs_dict (dict): Dictionary with sctucture bug_id->role->permit

    Returns:
        dict: Dictionary to apply on methods.
    """
    if bugs_dict is None:
        bugs_dict = dict()

    if not roles:
        return bugs_dict

    if not bugs_dict.get(bug_id):
        bugs_dict[bug_id] = dict()

    for role in roles:
        bugs_dict[bug_id][role] = permits

    return bugs_dict


def get_class_name(role, template):
    """
    Generates name for a class from given role and template string.

    Args:
        role (str): Role name.
        template (str): Template class string.

    Returns:
        str: Class name.
    """
    return "Test{0}{1}".format(role, template)


def get_role_permits(role_name):
    """
    Makes a list of names of role permits.

    Args:
        role_name (str): Role to get permits.

    Returns:
        list[str]: List of permits names.
    """
    role_obj = ll_mla.util.find(role_name)
    permits = ll_mla.util.getElemFromLink(
        role_obj,
        link_name='permits',
        attr='permit'
    )
    return [p.get_name() for p in permits]


def get_role_name(class_name):
    """
    Generates role name from given class name.
    E.g.: x <- TestSomeUserRoleActions
          f(x) <- x[4:-11]
          f(TestSomeUserRoleActions) -> SomeUser

    Args:
        class_name (str): Name of class.

    Returns:
        str: Role name.
    """
    return class_name[4:-11]


def get_test_name(permit):
    """
    Generates test method name from given permit.

    Args:
        permit (str): Permit name.

    Returns:
        str: Test method name.
    """
    return "test_{0}".format(permit)


def wrap_bz(cls=None, bzs=None):
    """
    Class wrapper to wrap each method of class by bugzilla wrapper if
    method's permit exists in bugs dictionary.

    Args:
        cls (class): Class to wrap
        bzs (dict): Dictionary with bugs ids, roles and permits.

    Returns:
        class: Wrapped class.
    """
    if not cls:
        return partial(wrap_bz, bzs=bzs)

    role_name = get_role_name(cls.__name__)

    for member_name, member_type in vars(cls).iteritems():
        if callable(member_type) and member_name.startswith("test_"):
            for bz_id in bzs:
                permits = bzs[bz_id].get(role_name)

                if permits is None:
                    continue

                for permit in permits:
                    if member_name != get_test_name(permit):
                        continue

                    method = getattr(cls, member_name)

                    if getattr(method, "bugzilla", None):
                        continue

                    setattr(cls, member_name, bz({bz_id: {}})(method.__func__))
    return cls


bugs = dict()

"""
Code below will create for each module(test_user, test_admin)
class with specific role and set mandatory attributes.
Then this class is injected into specific test module.
ie:
    class UserRole_RoleActions(CaseRoleActions):
        role = role_name
        filter_ = filter_
        perms = role_permits
"""
all_permits = get_role_permits('SuperUser')

"""
The name of the base class is CaseRoleActions.
So to get a template class name we need to remove the "Case" part of the
class name.
E.g. CaseRoleActions[4:] -> RoleActions
"""
class_template_name = BASE_CLASS.__name__[4:]


for role in ll_mla.util.get(abs_link=False):
    role_name = role.get_name()
    filter_ = not role.get_administrative()
    role_permits = get_role_permits(role_name)

    if 'login' not in role_permits:
        logger.info("Skipping role %s (can't login).", role_name)
        continue

    test_class = copy.deepcopy(BASE_CLASS)

    setattr(
        test_class, "__name__",
        get_class_name(role_name, class_template_name)
    )

    setattr(test_class, "role", role_name)
    setattr(test_class, "filter_", filter_)
    setattr(test_class, "perms", role_permits)

    module = test_user if filter_ else test_admin

    setattr(module, test_class.__name__, wrap_bz(bzs=bugs)(test_class))

    test_class = None  # Need set to None, else it will be case of this module
    del test_class
