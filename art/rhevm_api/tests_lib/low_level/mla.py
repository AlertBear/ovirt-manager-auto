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

from art.core_api.apis_utils import getDS
import os
from utilities.utils import readConfFile
from art.rhevm_api.utils.test_utils import get_api, split
from art.core_api import is_action

ELEMENTS=os.path.join(os.path.dirname(__file__), '../../../conf/elements.conf')
ENUMS = readConfFile(ELEMENTS, 'RHEVM Enums')
CONF_PERMITS = readConfFile(ELEMENTS, 'RHEVM Permits')

Role = getDS('Role')
Permits = getDS('Permits')
Permit = getDS('Permit')
Permission = getDS('Permission')

ELEMENT = 'role'
COLLECTION = 'roles'
util = get_api(ELEMENT, COLLECTION)
dcUtil = get_api('data_center', 'datacenters')
hostUtil = get_api('host', 'hosts')
permitUtil = get_api('permit', 'capabilities')
vmUtil = get_api('vm', 'vms')
userUtil = get_api('user', 'users')
hostUtil = get_api('host', 'hosts')
sdUtil = get_api('storage_domain', 'storagedomains')
clUtil = get_api('cluster', 'clusters')
templUtil = get_api('template', 'templates')
dcUtil = get_api('data_center', 'datacenters')
poolUtil = get_api('vmpool', 'vmpools')
domUtil = get_api('domain', 'domains')
groupUtil = get_api('group', 'groups')
permisUtil = get_api('permission', 'permissions')
versionCaps = permitUtil.get(absLink=False)
if isinstance(versionCaps, list):
    versionCaps = versionCaps[0]
PERMITS = versionCaps.get_permits().get_permit()


@is_action()
def checkSystemPermits(positive):
    '''
    Description: check existed system permissions
    Author: edolinin
    Parameters:
       No
    Return: status (True if all system permissions exist, False otherwise)
    '''

    status = True

    confPermits = CONF_PERMITS.values()

    for permit in PERMITS:
        if permit.get_name() not in confPermits:
            util.logger.error("Permit '{0}' doesn't appear in permission list: {1}" \
                    .format(permit.get_name(), CONF_PERMITS.values()))
            status = False
        else:
            util.logger.info(permit.get_name())
            confPermits.remove(permit.get_name())

    if confPermits:
        util.logger.error("The following permissions don't appear: {1}" \
                    .format(confPermits))
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
        permitsList = split(permits)
        for permit in permitsList:
            permitObj = permitUtil.find(permit, collection=PERMITS)
            rolePermits.add_permit(permitObj)
        role.set_permits(rolePermits)

    administrative = kwargs.pop('administrative', None)
    if administrative:
        role.set_administrative(administrative)

    return role


@is_action()
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
    role,status = util.create(role, positive)

    return status


@is_action()
def updateRole(positive, role, **kwargs):
    '''
    Description: update existed role
    Author: edolinin
    Parameters:
       * role - name of role that should be updated
       * name - new role name
    Return: status (True if role was updated properly, False otherwise)
    '''

    roleObj = util.find(role)
    roleNew = _prepareRoleObject(**kwargs)
    roleObj,status = util.update(roleObj, roleNew, positive)

    return status


@is_action()
def addRolePermissions(positive, role, permit):
    '''
    Description: add permission to role
    Author: edolinin
    Parameters:
       * role - name of role that should be updated
       * permit - name of permission that should be added
    Return: status (True if permission was added properly, False otherwise)
    '''

    roleObj = util.find(role)
    permitObj = permitUtil.find(permit, collection=PERMITS)
    rolePermits = util.getElemFromLink(roleObj, link_name='permits',
                                            attr='permit', get_href=True)
    rolePermit = Permit()
    rolePermit.set_id(permitObj.get_id())
    role, status = permitUtil.create(rolePermit, positive, collection=rolePermits)
    return status


@is_action()
def removeRolePermissions(positive, role, permit):
    '''
    Description: remove permission from role
    Author: edolinin
    Parameters:
       * role - name of role that should be updated
       * permit - name of permission that should be removed
    Return: status (True if permission was removed properly, False otherwise)
    '''

    roleObj = util.find(role)
    permitObj = util.getElemFromElemColl(roleObj, permit, 'permits', 'permit')
    return util.delete(permitObj, positive)


@is_action()
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


def addPermitsToUser(positive, user, role, obj, attr):

    userObj = userUtil.find(user)
    roleObj = util.find(role)

    permit = Permission()
    permit.set_role(roleObj)
    getattr(permit, 'set_' + attr)(obj)
    userPermits = permisUtil.getElemFromLink(userObj, get_href=True)
    permit, status = permisUtil.create(permit, positive, collection=userPermits)

    return status


def addPermitsToGroup(positive, group, role, obj, attr):

    groupObj = groupUtil.find(group)
    roleObj = util.find(role)

    permit = Permission()
    permit.set_role(roleObj)
    getattr(permit, 'set_' + attr)(obj)
    groupPermits = permisUtil.getElemFromLink(groupObj, get_href=True)
    permit, status = permisUtil.create(permit, positive, collection=groupPermits)

    return status


@is_action()
def addVMPermissionsToUser(positive, user, vm, role=ENUMS['role_name_user_vm_manager']):
    '''
    Description: add vm permissios to user
    Author: edolinin
    Parameters:
       * user - name of user
       * vm - name of vm
       * role - role to add
    Return: status (True if permission was added properly, False otherwise)
    '''

    vmObj = vmUtil.find(vm)
    return addPermitsToUser(positive, user, role, vmObj, 'vm')


@is_action()
def addHostPermissionsToUser(positive, user, host, role="HostAdmin"):
    '''
    Description: add host permissios to user
    Author: edolinin
    Parameters:
       * user - name of user
       * host - name of host
       * role - role to add
    Return: status (True if permission was added properly, False otherwise)
    '''

    hostObj = hostUtil.find(host)
    return addPermitsToUser(positive, user, role, hostObj, 'host')


@is_action()
def addStoragePermissionsToUser(positive, user, storage, role="StorageAdmin"):
    '''
    Description: add storage domain permissios to user
    Author: edolinin
    Parameters:
       * user - name of user
       * storage - name of storage domain
       * role - role to add
    Return: status (True if permission was added properly, False otherwise)
    '''

    sdObj = sdUtil.find(storage)
    return addPermitsToUser(positive, user, role, sdObj, 'storage_domain')


@is_action()
def addClusterPermissionsToUser(positive, user, cluster, role="ClusterAdmin"):
    '''
    Description: add cluster permissios to user
    Author: edolinin
    Parameters:
       * user - name of user
       * cluster - name of cluster
       * role - role to add
    Return: status (True if permission was added properly, False otherwise)
    '''

    clObj = clUtil.find(cluster)
    return addPermitsToUser(positive, user, role, clObj, 'cluster')


@is_action()
def addClusterPermissionsToGroup(positive, group, cluster, role="ClusterAdmin"):
    '''
    Description: add cluster permissios to group
    Author: jvorcak
    Parameters:
       * group - name of the group
       * cluster - name of cluster
       * role - role to add
    Return: status (True if permission was added properly, False otherwise)
    '''

    clusterObj = util.find(cluster)
    return addPermitsToGroup(positive, group, role, clusterObj, 'cluster')


def addUserPermitsForObj(positive, user, role, obj, group=False):

    userObj = groupUtil.find(user) if group else userUtil.find(user)
    roleObj = util.find(role)

    permit = Permission()
    permit.set_role(roleObj)
    permit.set_group(userObj) if group else permit.set_user(userObj)
    objPermits = permisUtil.getElemFromLink(obj, get_href=True)
    permit, status = permisUtil.create(permit, positive, collection=objPermits)

    return status


@is_action()
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


@is_action()
def addTemplatePermissionsToGroup(positive, group, template, role="TemplateAdmin"):
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


@is_action()
def addPermissionsForTemplateToGroup(positive, group, template, role="TemplateAdmin"):
    '''
    Description: add template permissions to group using group link
    Author: jvorcak
    Parameters:
       * group - name of group
       * template - name of template
       * role - role to add
    Return: status (True if permission was added properly, False otherwise)
    '''
    templateObj = templUtil.find(template)
    return addPermitsToGroup(positive, group, role, templateObj, 'template')


@is_action()
def addPermissionsForDataCenter(positive, user, data_center, role="TemplateAdmin"):
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


@is_action()
def removeAllPermissionsFromUser(positive, user):
    '''
    Description: remove all permissions from user
    Author: edolinin
    Parameters:
       * user - name of user
    Return: status (True if permissions were removed properly, False otherwise)
    '''

    status = True
    userObj = userUtil.find(user)
    userPermits = permisUtil.getElemFromLink(userObj, get_href=False)

    for perm in userPermits:
        if not permisUtil.delete(perm, positive):
            status = False

    return status


@is_action()
def addVmPoolPermissionToUser(positive, user, vmpool, role):
    '''
    Description: add permission to the user for specified vm pool object
    Author: jvorcak
    Parameters:
       * user - user name
       * vmpool - vmpool name
       * role - role name
    Return: status (True if permission has been granted, False otherwise)
    '''

    poolObj = poolUtil.find(vmpool)
    return addPermitsToUser(positive, user, role, poolObj, 'vmpool')


@is_action()
def checkDomainsId():
    '''
    Check whether domain resource in domains collection is displayed
    correctly, in order to make this test meaningful, there should be at
    least two domains in /domains collection
    Author: jvorcak
    return (True/False)
    '''

    domains = domUtil.get(absLink=False)

    if len(domains) < 2:
        util.logger.warn("Size of the domains collection is < 2, \
                test case should have at least 2 domains in \
                the domains collection availible")

    ret = True

    for domain in domains:
        domainId = domain.get_id()
        domainHref = domain.get_href()
        domainHrefId = domainHref.split('/')[-1]

        if domainHrefId != domainId:
            util.logger.error("Domain resource %s has wrong id, %s found but %s expected"\
                    % (domain.get_name(), domainId, domainHrefId))
            ret = False

    return ret

