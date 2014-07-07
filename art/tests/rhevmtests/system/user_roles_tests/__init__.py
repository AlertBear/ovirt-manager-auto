#!/usr/bin/env python
from art.rhevm_api.tests_lib.high_level import storagedomains as h_sd
from art.rhevm_api.tests_lib.low_level import storagedomains
from art.rhevm_api.tests_lib.low_level import clusters
from art.rhevm_api.tests_lib.low_level import datacenters
from art.rhevm_api.tests_lib.low_level import hosts
from art.rhevm_api.tests_lib.low_level import mla

from rhevmtests.system.user_roles_tests import config
import inspect
import test_actions
import test_admin_negative
import test_admin_positive
import test_user_negative
import test_user_positive


def getActionGroups(role_name):
    roleObj = mla.util.find(role_name)
    return [p.get_name() for p in mla.util.getElemFromLink(
            roleObj, link_name='permits', attr='permit')]


allActions = getActionGroups('SuperUser')
for role in mla.util.get(absLink=False):
    role_name = role.get_name()
    filter_ = not role.get_administrative()
    roleActions = getActionGroups(role_name)
    if 'login' not in roleActions:
        continue

    module = None
    cases = inspect.getmembers(test_actions)
    for name, obj in cases:
        if not inspect.isclass(obj) or not obj.__name__[:5].startswith('Case'):
            continue

        case_name = obj.__name__[5:]
        positive = inspect.isclass(obj) and case_name in roleActions

        my_obj = type('%s_%s' % (role_name, case_name), (obj,), {})
        my_obj.role = role_name
        my_obj.filter_ = filter_
        my_obj.perms = roleActions
        my_obj.positive = positive

        if positive and filter_:
            module = test_user_positive
        elif positive and not filter_:
            module = test_admin_positive
        elif not positive and filter_:
            module = test_user_negative
        else:
            module = test_admin_negative

        setattr(module, '%s_%s' % (role_name, case_name), my_obj)


def setup_package():
    """ Prepare environment """
    reload(config)
    cv = 'compatibility_version'
    assert datacenters.addDataCenter(True, name=config.MAIN_DC_NAME,
                                     storage_type=config.MAIN_STORAGE_TYPE,
                                     version=config.PARAMETERS.get(cv))
    assert clusters.addCluster(True, name=config.MAIN_CLUSTER_NAME,
                               cpu=config.PARAMETERS.get('cpu_name'),
                               data_center=config.MAIN_DC_NAME,
                               version=config.PARAMETERS.get(cv))
    assert hosts.addHost(
        True, config.MAIN_HOST_NAME, root_password=config.HOST_ROOT_PASSWORD,
        address=config.HOST_ADDRESS, cluster=config.MAIN_CLUSTER_NAME)
    assert h_sd.addNFSDomain(config.MAIN_HOST_NAME, config.MAIN_STORAGE_NAME,
                             config.MAIN_DC_NAME, config.NFS_STORAGE_ADDRESS,
                             config.NFS_STORAGE_PATH)


def teardown_package():
    """ Clean environment """
    reload(config)
    storagedomains.cleanDataCenter(True, config.MAIN_DC_NAME)
