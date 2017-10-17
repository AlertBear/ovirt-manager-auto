#!/usr/bin/env python

# Copyright (C) 2010 Red Hat, Inc.
#
# This is free software; you can redistribute it and/or modify it
# under the terms of the GNU Lesser General Public License as
# published by the Free Software Foundation; either version 2.1 of
# the License, or (at your option) any later version.
#
# This software is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this software; if not, write to the Free
# Software Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA
# 02110-1301 USA, or see the FSF site: http://www.fsf.org.

import logging
from art.core_api.apis_utils import getDS
from art.core_api.apis_exceptions import EntityNotFound
from art.rhevm_api.utils.test_utils import get_api
from art.test_handler.settings import ART_CONFIG
from art.rhevm_api.tests_lib.low_level.networks import (
    find_network,
    get_vnic_profile_obj
)
import art.rhevm_api.tests_lib.low_level.general as ll_general

ENUMS = ART_CONFIG['elements_conf']['RHEVM Enums']
CONF_PERMITS = ART_CONFIG['elements_conf']['RHEVM Permits']

Role = getDS('Role')
Permits = getDS('Permits')
Permit = getDS('Permit')
Permission = getDS('Permission')

ELEMENT = 'role'
COLLECTION = 'roles'
util = get_api(ELEMENT, COLLECTION)
dcUtil = get_api('data_center', 'datacenters')
hostUtil = get_api('host', 'hosts')
permitUtil = get_api('cluster_level', 'clusterlevels')
vmUtil = get_api('vm', 'vms')
userUtil = get_api('user', 'users')
sdUtil = get_api('storage_domain', 'storagedomains')
clUtil = get_api('cluster', 'clusters')
templUtil = get_api('template', 'templates')
poolUtil = get_api('vm_pool', 'vmpools')
domUtil = get_api('domain', 'domains')
groupUtil = get_api('group', 'groups')
permisUtil = get_api('permission', 'permissions')
diskUtil = get_api('disk', 'disks')

logger = logging.getLogger("art.ll_lib.mla")


def getPermits():
    '''
    Description: collect permissions
    Author: imeerovi
    Parameters: None
    Return: Permissions list
    '''
    try:
        version_caps = permitUtil.get(abs_link=False)
        if isinstance(version_caps, list):
            version_caps = version_caps[0]
    except KeyError:
        raise EntityNotFound("Can't get list of permissions from capabilities")
    return version_caps.get_permits().get_permit()


def check_system_permits(positive):
    '''
    Description: check existed system permissions
    Author: edolinin
    Parameters:
       No
    Return: status (True if all system permissions exist, False otherwise)
    '''

    status = True

    conf_permits = CONF_PERMITS.values()

    for permit in getPermits():
        if permit.get_name() not in conf_permits:
            util.logger.error(
                "Permit '{0}' doesn't appear in permission list: {1}".format(
                    permit.get_name(), CONF_PERMITS.values()))
            status = False
        else:
            util.logger.info(permit.get_name())
            conf_permits.remove(permit.get_name())

    if conf_permits:
        util.logger.error(
            "The following permissions don't appear: {0}".format(conf_permits))
        status = False

    return status


def _prepareRoleObject(**kwargs):

    role = Role()
    name = kwargs.pop('name', None)
    if name:
        role.set_name(name)

    permits = kwargs.pop('permits', None)
    rolePermits = Permits()
    if permits:
        permitsList = permits.replace(',', ' ').split()
        for permit in permitsList:
            permitObj = permitUtil.find(permit, collection=getPermits())
            rolePermits.add_permit(permitObj)
        role.set_permits(rolePermits)

    administrative = kwargs.pop('administrative', None)
    if administrative:
        role.set_administrative(administrative)

    return role


def addRole(positive, administrative="false", **kwargs):
    '''
    Description: add new role
    Author: edolinin
    Parameters:
       * permits - permissions to add to role
       * administrative - if role has admin permissions or not
    Return: status (True if role was added properly, False otherwise)
    '''
    kwargs['administrative'] = administrative
    role = _prepareRoleObject(**kwargs)
    role, status = util.create(role, positive)

    return status


def updateRole(positive, role, **kwargs):
    '''
    Description: update existed role

    Parameters:
       * role - name of role that should be updated
       * name - new role name
    Return: status (True if role was updated properly, False otherwise)
    '''

    roleObj = util.find(role)
    roleNew = _prepareRoleObject(**kwargs)
    roleObj, status = util.update(roleObj, roleNew, positive)

    return status


def add_permission_to_role(positive, permission, role):
    """
    Description:
        Adds given permission to role given role
    Parameters:
        positive (bool): expected result
        permission (str): name of permission should be added
        role (str): name of role should be updated
    Returns:
        bool: True if permission was added properly, False otherwise
    """
    role_object = util.find(role)
    permission_object = permitUtil.find(
        permission,
        collection=getPermits()
    )
    role_permissions = util.getElemFromLink(
        role_object,
        link_name='permits',
        attr='permit',
        get_href=True
    )
    role_permission = Permit()
    role_permission.set_id(permission_object.get_id())
    role, status = permitUtil.create(
        role_permission,
        positive,
        collection=role_permissions,
        coll_elm_name='permit',
        expected_entity=permission_object
    )
    return status


def removeRole(positive, role):
    '''
    Description: remove role
    Author: edolinin
    Parameters:
       * role - name of role that should be removed
    Return: status (True if role was removed properly, False otherwise)
    '''

    roleObj = util.find(role)
    return util.delete(roleObj, positive)


def addPermitsToUser(positive, user, domain, role, obj, attr):
    """
    Add permissions to user for a specific object

    Args:
        positive (bool): True if create action is expected to succeed, False
            otherwise.
        user (str): Name of user which we add permission for.
        domain (str): Domain name where user is from.
        role (str): Name of role we want to give to the user
        obj (BaseResources): Object of the specific entity that the user gets
            it's permission on.
        attr (str): Name of the attribute of the object (e.g. 'vm')

    Returns:
        bool: True if result of creation is as expected, False otherwise.
    """
    extra_log_text = "to user %s for %s: %s" % (
        user, obj.__class__.__name__, obj.get_name()
    )
    log_info, log_error = ll_general.get_log_msg(
        "create", "permission", role, positive, extra_log_text
    )
    logger.info(log_info)
    if domain is not None:
        user_name = '%s@%s' % (user, domain)
        userObj = userUtil.query('{0}={1}'.format('usrname', user_name))[0]
    else:
        userObj = userUtil.find(user)
    roleObj = util.find(role)

    permit = Permission()
    permit.set_role(roleObj)
    getattr(permit, 'set_' + attr)(obj)
    userPermits = permisUtil.getElemFromLink(userObj, get_href=True)
    _, status = permisUtil.create(
        permit, positive, collection=userPermits
    )
    if not status:
        logger.error(log_error)
    return status


def addPermitsToGroup(positive, group, role, obj, attr):

    groupObj = groupUtil.find(group)
    roleObj = util.find(role)

    permit = Permission()
    permit.set_role(roleObj)
    getattr(permit, 'set_' + attr)(obj)
    groupPermits = permisUtil.getElemFromLink(groupObj, get_href=True)
    permit, status = permisUtil.create(permit, positive,
                                       collection=groupPermits)

    return status


def addVMPermissionsToUser(
        positive, user, vm, role=ENUMS['role_name_user_vm_manager'],
        domain=None):
    '''
    Description: add vm permissios to user
    Author: edolinin
    Parameters:
       * user - name of user
       * vm - name of vm
       * role - role to add
       * domain - domain of user
    Return: status (True if permission was added properly, False otherwise)
    '''

    vmObj = vmUtil.find(vm)
    return addPermitsToUser(positive, user, domain, role, vmObj, 'vm')


def addStoragePermissionsToUser(positive, user, storage, role="StorageAdmin",
                                domain=None):
    '''
    Description: add storage domain permissios to user
    Author: edolinin
    Parameters:
       * user - name of user
       * storage - name of storage domain
       * role - role to add
       * domain - domain of user
    Return: status (True if permission was added properly, False otherwise)
    '''

    sdObj = sdUtil.find(storage)
    return addPermitsToUser(
        positive, user, domain, role, sdObj, 'storage_domain')


def addClusterPermissionsToUser(positive, user, cluster, role="ClusterAdmin",
                                domain=None):
    '''
    Description: add cluster permissios to user
    Author: edolinin
    Parameters:
       * user - name of user
       * cluster - name of cluster
       * role - role to add
       * domain - domain of user
    Return: status (True if permission was added properly, False otherwise)
    '''

    clObj = clUtil.find(cluster)
    return addPermitsToUser(positive, user, domain, role, clObj, 'cluster')


def addClusterPermissionsToGroup(positive, group, cluster,
                                 role="ClusterAdmin"):
    '''
    Description: add cluster permissios to group
    Author: jvorcak
    Parameters:
       * group - name of the group
       * cluster - name of cluster
       * role - role to add
       * domain - domain of user
    Return: status (True if permission was added properly, False otherwise)
    '''

    clusterObj = clUtil.find(cluster)
    return addPermitsToGroup(positive, group, role, clusterObj, 'cluster')


def addUserPermitsForObj(positive, user, role, obj, group=False):
    extra_log_text = "for user %s on %s: %s" % (
        user, obj.__class__.__name__, obj.get_name()
    )
    log_info, log_error = ll_general.get_log_msg(
        "create", "permission", role, positive, extra_log_text
    )
    logger.info(log_info)
    userObj = groupUtil.find(user) if group else userUtil.find(user)
    roleObj = util.find(role)

    permit = Permission()
    permit.set_role(roleObj)
    permit.set_group(userObj) if group else permit.set_user(userObj)
    objPermits = permisUtil.getElemFromLink(obj, get_href=True)
    _, status = permisUtil.create(permit, positive, collection=objPermits)
    if not status:
        logger.error(log_error)
    return status


def addPermissionsForVnicProfile(positive, user, vnicprofile, network,
                                 data_center, role='VnicProfileUser'):
    '''
    Description: add permissions for user on vnicprofile
    Author: omachace
    Parameters:
      * user - name of user
      * vnicprofile - name of vnic profile
      * network - network name
      * data_center - name of datacenter of network
      * role - role to add
    Return: status (True if permission was added properly, False otherwise)
    '''
    vnicObj = get_vnic_profile_obj(
        vnicprofile, network, data_center=data_center
    )
    return addUserPermitsForObj(positive, user, role, vnicObj)


def addPermissionsForNetwork(positive, user, network, data_center,
                             role="NetworkAdmin"):
    '''
    Description: add permissions for user on network
    Author: omachace
    Parameters:
       * user - name of user
       * network - name of network
       * data_center - name of datacenter of network
       * role - role to add
    Return: status (True if permission was added properly, False otherwise)
    '''
    netObj = find_network(network, data_center)
    return addUserPermitsForObj(positive, user, role, netObj)


def addPermissionsForDisk(positive, user, disk, role="DiskOperator"):
    '''
    Description: add disk permissios to user
    Author: omachace
    Parameters:
       * user - name of user
       * disk - name(alias) of disk
       * role - role to add
    Return: status (True if permission was added properly, False otherwise)
    '''
    diskObj = diskUtil.find(disk)
    return addUserPermitsForObj(positive, user, role, diskObj)


def addPermissionsForTemplate(positive, user, template, role="TemplateAdmin"):
    '''
    Description: add template permissios to user
    Author: edolinin
    Parameters:
       * user - name of user
       * template - name of template
       * role - role to add
    Return: status (True if permission was added properly, False otherwise)
    '''

    templObj = templUtil.find(template)
    return addUserPermitsForObj(positive, user, role, templObj)


def addVnicProfilePermissionsToGroup(positive, group, vnicprofile, network,
                                     data_center, role='VnicProfileUser'):
    '''
    Description: add vnicprofile permissions to group
    Parameters:
       * group - name of group
       * vnicprofile - name of vnicprofile
       * role - role to add
    Return: status (True if permission was added properly, False otherwise)
    '''
    vnicObj = get_vnic_profile_obj(
        vnicprofile, network, data_center=data_center
    )
    return addUserPermitsForObj(positive, group, role, vnicObj, True)


def addTemplatePermissionsToGroup(positive, group, template,
                                  role="TemplateAdmin"):
    '''
    Description: add template permissions to group using template link
    Author: jvorcak
    Parameters:
       * group - name of group
       * template - name of template
       * role - role to add
    Return: status (True if permission was added properly, False otherwise)
    '''

    templObj = templUtil.find(template)
    return addUserPermitsForObj(positive, group, role, templObj, True)


def addPermissionsForDataCenter(positive, user, data_center,
                                role="TemplateAdmin"):
    '''
    Description: add data centers permissios to user
    Author: edolinin
    Parameters:
       * user - name of user
       * data_center - name of data center
       * role - role to add
    Return: status (True if permission was added properly, False otherwise)
    '''

    dcObj = dcUtil.find(data_center)
    return addUserPermitsForObj(positive, user, role, dcObj)


def remove_all_permissions_from_user(user):
    """
    Remove all permissions from a given user.

    Args:
        user (str): Name of a user.

    Returns:
        bool: True if permissions were removed properly, False otherwise.
    """

    user_object = userUtil.find(user)
    user_permissions = permisUtil.getElemFromLink(user_object, get_href=False)

    for permission in user_permissions:
        if not permisUtil.delete(permission, True):
            return False

    return True


def addVmPoolPermissionToUser(positive, user, vmpool, role, domain=None):
    '''
    Description: add permission to the user for specified vm pool object
    Author: jvorcak
    Parameters:
       * user - user name
       * vmpool - vmpool name
       * role - role name
       * domain - domain of user
    Return: status (True if permission has been granted, False otherwise)
    '''

    poolObj = poolUtil.find(vmpool)
    return addPermitsToUser(positive, user, domain, role, poolObj, 'vm_pool')


def findUserByUserName(user_name):
    '''
    Description: Find user by usernam:
    Parameters:
     * user_name: user_name of user
    return User object if found else None
    '''
    users = userUtil.query('{0}={1}'.format('usrname', user_name))
    user = filter(lambda u: u.get_user_name() == user_name, users) or [None]
    return user[0]


def removeUserRoleFromObject(positive, obj, user_name, role_name):
    '''
    Description: remove user's role from object
    Parameters:
      * obj - object where permissions should be removed
      * user_name - user name
      * role_name - role which should be removed
    '''
    extra_log_text = "for user/group %s on %s: %s" % (
        user_name, obj.__class__.__name__, obj.get_name()
    )
    log_info, log_error = ll_general.get_log_msg(
        "remove", "permission", role_name, extra_txt=extra_log_text
    )
    logger.info(log_info)
    status = True
    role_id = util.find(role_name).get_id()
    permits = permisUtil.getElemFromLink(obj, get_href=False)
    user = findUserByUserName(user_name)
    if user is None:
        return not positive

    user = user.get_id()
    for perm in permits:
        if (
            perm.get_user() and perm.get_user().get_id() == user and
            perm.get_role().get_id() == role_id
        ):
            if not permisUtil.delete(perm, positive):
                logger.error(log_error)
                status = False
    return status


def removeUsersPermissionsFromObject(positive, obj, user_names):
    '''
    Description: remove all permissions on obj of specified users
    Author: omachace
    Parameters:
       * obj - object where permissions should be removed
       * user_names - list with user names (ie.['user1@..', 'user2@..'])
    Return: status (True if permissions was removed, False otherwise)
    '''
    extra_log_text = "for users %s on %s: %s" % (
        user_names, obj.__class__.__name__, obj.get_name()
    )
    log_info, log_error = ll_general.get_log_msg(
        "remove", "permissions", 'All', extra_txt=extra_log_text
    )
    logger.info(log_info)
    status = True
    permits = permisUtil.getElemFromLink(obj, get_href=False)
    user_ids = [userUtil.query('{0}={1}'.format('usrname', user))[0].get_id()
                for user in user_names]

    for perm in permits:
        if (
            perm.get_user() and perm.get_user().get_id() in user_ids and not
            permisUtil.delete(perm, positive)
        ):
            logger.error(log_error)
            status = False

    return status


def removeUserPermissionsFromVnicProfile(positive, vnicprofile, network,
                                         data_center, user_name):
    '''
    Description: remove all permissions from vnicprofile of specified user
    Author: omachace
    Parameters:
       * vnicprofile - vnicprofile where permissions should be removed
       * network - network which is associated with vnicprofile
       * data_center - name of datacenter of network/vnicprofile
       * user_name - user name
    Return: status (True if permissions was removed, False otherwise)
    '''
    return removeUsersPermissionsFromNetwork(positive, network,
                                             data_center, [user_name])


def removeUsersPermissionsFromNetwork(positive, network, data_center,
                                      user_names):
    '''
    Description: remove all permissions on network of specified users
    Author: omachace
    Parameters:
       * network - network where permissions should be removed
       * data_center - name of datacenter of network
       * user_names - list with user names (ie.['user1@..', 'user2@..'])
    Return: status (True if permissions was removed, False otherwise)
    '''
    netObj = find_network(network, data_center)
    return removeUsersPermissionsFromObject(positive, netObj, user_names)


def removeUserPermissionsFromNetwork(positive, network, data_center,
                                     user_name):
    '''
    Description: remove all permissions on network of specified user
    Author: omachace
    Parameters:
       * network - network where permissions should be removed
       * data_center - name of datacenter of network
       * user_name - user name
    Return: status (True if permissions was removed, False otherwise)
    '''
    return removeUsersPermissionsFromNetwork(
        positive, network, data_center, [user_name])


def removeUsersPermissionsFromDatacenter(positive, data_center, user_names):
    '''
    Description: remove all permissions on datacenter of specified users
    Author: omachace
    Parameters:
       * data_center - datacenter where permissions should be removed
       * user_names - list with user names (ie.['user1@..', 'user2@..'])
    Return: status (True if permissions was removed, False otherwise)
    '''
    dcObj = dcUtil.find(data_center)
    return removeUsersPermissionsFromObject(positive, dcObj, user_names)


def removeUserPermissionsFromDatacenter(positive, data_center, user_name):
    '''
    Description: remove all permissions on datacenter of specified user
    Author: omachace
    Parameters:
       * data_center - datacenter where permissions should be removed
       * user_name - user name
    Return: status (True if permissions was removed, False otherwise)
    '''
    return removeUsersPermissionsFromDatacenter(
        positive, data_center, [user_name])


def removeUsersPermissionsFromCluster(positive, cluster, user_names):
    '''
    Description: remove all permissions on cluster of specified users
    Author: omachace
    Parameters:
       * cluster - cluster where permissions should be removed
       * user_names - list with user names (ie.['user1@..', 'user2@..'])
    Return: status (True if permissions was removed, False otherwise)
    '''
    clusterObj = clUtil.find(cluster)
    return removeUsersPermissionsFromObject(positive, clusterObj, user_names)


def removeUserPermissionsFromCluster(positive, cluster, user_name):
    '''
    Description: remove all permissions on cluster of specified user
    Author: omachace
    Parameters:
       * cluster - cluster where permissions should be removed
       * user_name - user name
    Return: status (True if permissions was removed, False otherwise)
    '''
    return removeUsersPermissionsFromCluster(positive, cluster, [user_name])


def removeUsersPermissionsFromVm(positive, vm, user_names):
    '''
    Description: remove all permissions on vm of specified users
    Author: omachace
    Parameters:
       * vm - vm where permissions should be removed
       * user_names - list with user names (ie.['user1@..', 'user2@..'])
    Return: status (True if permissions was removed, False otherwise)
    '''
    vmObj = vmUtil.find(vm)
    return removeUsersPermissionsFromObject(positive, vmObj, user_names)


def removeUserPermissionsFromVm(positive, vm, user_name):
    '''
    Description: remove all permissions on vm of specified user
    Author: omachace
    Parameters:
       * vm - vm where permissions should be removed
       * user_name - user name
    Return: status (True if permissions was removed, False otherwise)
    '''
    return removeUsersPermissionsFromVm(positive, vm, [user_name])


def removeUsersPermissionsFromTemplate(positive, template, user_names):
    '''
    Description: remove all permissions on template of specified users
    Author: omachace
    Parameters:
       * template - template where permissions should be removed
       * user_names - list with user names (ie.['user1@..', 'user2@..'])
    Return: status (True if permissions was removed, False otherwise)
    '''
    tmpObj = templUtil.find(template)
    return removeUsersPermissionsFromObject(positive, tmpObj, user_names)


def removeUserPermissionsFromTemplate(positive, template, user_name):
    '''
    Description: remove all permissions on template of specified user
    Author: omachace
    Parameters:
       * template - template where permissions should be removed
       * user_name - user name
    Return: status (True if permissions was removed, False otherwise)
    '''
    return removeUsersPermissionsFromTemplate(positive, template, [user_name])


def removeUserRoleFromDataCenter(positive, datacenter, user_name, role_name):
    '''
    Description: remove specific user's role from datacenter
    Parameters:
      * datacenter - datacenter where user's role should be removed
      * user_name - user name
      * role_name - name of role to be removed
    Return: status (True if permissions was removed, False otherwise)
    '''
    dcObj = dcUtil.find(datacenter)
    return removeUserRoleFromObject(positive, dcObj, user_name, role_name)


def removeUsersPermissionsFromSD(positive, storage_domain, user_names):
    '''
    Description: remove all permissions on storage domain of specified users
    Author: omachace
    Parameters:
       * storage_domain - storage domain where permissions should be removed
       * user_names - list with user names (ie.['user1@..', 'user2@..'])
    Return: status (True if permissions was removed, False otherwise)
    '''
    sdObj = sdUtil.find(storage_domain)
    return removeUsersPermissionsFromObject(positive, sdObj, user_names)


def removeUserPermissionsFromSD(positive, storage_domain, user_name):
    '''
    Description: remove all permissions on template of specified user
    Author: omachace
    Parameters:
       * storage_domain - storage domain where permissions should be removed
       * user_name - user name
    Return: status (True if permissions was removed, False otherwise)
    '''
    return removeUsersPermissionsFromSD(positive, storage_domain, [user_name])


def removeUserRoleFromVm(positive, vm, user_name, role_name):
    '''
    Description: remove specific user's role from vm
    Parameters:
      * vm - vm where user's role should be removed
      * user_name - user name
      * role_name - name of role to be removed
    Return: status (True if permissions was removed, False otherwise)
    '''
    vmObj = vmUtil.find(vm)
    return removeUserRoleFromObject(positive, vmObj, user_name, role_name)


def has_user_or_group_permissions_on_object(name, obj, role, group=False):
    def get_group_or_user(perm):
        return perm.get_group() if group else perm.get_user()
    extra_log_text = "for user/group %s on %s: %s" % (
        name, obj.__class__.__name__, obj.get_name()
    )
    log_info, log_error = ll_general.get_log_msg(
        "find", "permission", role, extra_txt=extra_log_text
    )
    logger.info(log_info)
    obj_permits = permisUtil.getElemFromLink(obj, get_href=False)
    role_n_aid = util.find(role).get_id()
    if group:
        user = groupUtil.find(name)
    else:
        user = findUserByUserName(name)

    if user is None:
        logger.error(log_error)
        return False

    perms = []
    for perm in obj_permits:
        mla_obj = get_group_or_user(perm)
        if mla_obj is not None:
            perms.append((mla_obj.get_id(), perm.get_role().get_id()))
    if not (user.get_id(), role_n_aid) in perms:
        logger.error(log_error)
        return False
    return True


def hasGroupPermissionsOnObject(group_name, obj, role):
    """
    Description: Check if group has permission on object.
    Author: omachace
    Parameters:
       * group_name - name of group
       * obj - object which should be checked
       * role - name of the role to search for
    Return: True if user has permissions on object False otherwise
    """
    return has_user_or_group_permissions_on_object(group_name, obj, role, True)


def has_user_permissions_on_object(user_name, obj, role):
    """
    Description: Check if user has permission on object.
    Author: omachace
    Parameters:
       * user_name - user name of user
       * obj - object which should be checked
       * role - name of the role to search for
    Return: True if user has permissions on object False otherwise
    """
    return has_user_or_group_permissions_on_object(user_name, obj, role)


def allows_view_children(role, database):
    """
    Paramters:
     * role - name of role we need to check
     * database - database object from rhevm_api.resources
    Return: True if user can view children False otherwise
    """
    psql_cmd = "select allows_viewing_children from roles where name = '%s'"
    try:
        return database.psql(psql_cmd % role)[0][0] == 't'
    except IndexError:
        return False
