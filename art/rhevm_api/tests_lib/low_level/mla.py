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
from art.core_api.apis_exceptions import EntityNotFound
from art.rhevm_api.utils.test_utils import get_api, split
from art.core_api import is_action
from art.test_handler.settings import opts
from networks import findNetwork, getVnicProfileObj

ENUMS = opts['elements_conf']['RHEVM Enums']
CONF_PERMITS = opts['elements_conf']['RHEVM Permits']

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
diskUtil = get_api('disk', 'disks')


def getPermits():
    '''
    Description: collect permissions
    Author: imeerovi
    Parameters: None
    Return: Permissions list
    '''
    try:
        versionCaps = permitUtil.get(absLink=False)
        if isinstance(versionCaps, list):
            versionCaps = versionCaps[0]
    except KeyError:
        raise EntityNotFound("Can't get list of permissions from capabilities")
    return versionCaps.get_permits().get_permit()


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

    for permit in getPermits():
        if permit.get_name() not in confPermits:
            util.logger.error(
                "Permit '{0}' doesn't appear in permission list: {1}".format(
                    permit.get_name(), CONF_PERMITS.values()))
            status = False
        else:
            util.logger.info(permit.get_name())
            confPermits.remove(permit.get_name())

    if confPermits:
        util.logger.error(
            "The following permissions don't appear: {0}".format(confPermits))
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
            permitObj = permitUtil.find(permit, collection=getPermits())
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
    role, status = util.create(role, positive)

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
    roleObj, status = util.update(roleObj, roleNew, positive)

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
    permitObj = permitUtil.find(permit, collection=getPermits())
    rolePermits = util.getElemFromLink(roleObj, link_name='permits',
                                       attr='permit', get_href=True)
    rolePermit = Permit()
    rolePermit.set_id(permitObj.get_id())
    role, status = permitUtil.create(rolePermit, positive,
                                     collection=rolePermits)
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


def addPermitsToUser(positive, user, domain, role, obj, attr):

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
    permit, status = permisUtil.create(permit, positive,
                                       collection=userPermits)

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


@is_action()
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


@is_action()
def addHostPermissionsToUser(positive, user, host, role="HostAdmin",
                             domain=None):
    '''
    Description: add host permissios to user
    Author: edolinin
    Parameters:
       * user - name of user
       * host - name of host
       * role - role to add
       * domain - domain of user
    Return: status (True if permission was added properly, False otherwise)
    '''

    hostObj = hostUtil.find(host)
    return addPermitsToUser(positive, user, domain, role, hostObj, 'host')


@is_action()
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


@is_action()
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


@is_action()
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

    userObj = groupUtil.find(user) if group else userUtil.find(user)
    roleObj = util.find(role)

    permit = Permission()
    permit.set_role(roleObj)
    permit.set_group(userObj) if group else permit.set_user(userObj)
    objPermits = permisUtil.getElemFromLink(obj, get_href=True)
    permit, status = permisUtil.create(permit, positive, collection=objPermits)

    return status


@is_action()
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
    vnicObj = getVnicProfileObj(vnicprofile, network, data_center=data_center)
    return addUserPermitsForObj(positive, user, role, vnicObj)


@is_action()
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
    netObj = findNetwork(network, data_center)
    return addUserPermitsForObj(positive, user, role, netObj)


@is_action()
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
    vnicObj = getVnicProfileObj(vnicprofile, network, data_center=data_center)
    return addUserPermitsForObj(positive, group, role, vnicObj, True)


@is_action()
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


@is_action()
def addPermissionsForTemplateToGroup(positive, group, template,
                                     role="TemplateAdmin"):
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
    return addPermitsToUser(positive, user, domain, role, poolObj, 'vmpool')


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
    status = True
    role_id = util.find(role_name).get_id()
    permits = permisUtil.getElemFromLink(obj, get_href=False)
    user = findUserByUserName(user_name)
    if user is None:
        return not positive

    user = user.get_id()
    for perm in permits:
        if perm.get_user().get_id() == user and \
                perm.get_role().get_id() == role_id and \
                not permisUtil.delete(perm, positive):
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
    status = True
    permits = permisUtil.getElemFromLink(obj, get_href=False)
    user_ids = [userUtil.query('{0}={1}'.format('usrname', user))[0].get_id()
                for user in user_names]

    for perm in permits:
        if perm.get_user().get_id() in user_ids and \
                not permisUtil.delete(perm, positive):
                    status = False

    return status


@is_action()
def removeUsersPermissionsFromVnicProfile(positive, vnicprofile, network,
                                          data_center, user_names):
    '''
    Description: remove all permissions from vnicprofile of specified users
    Author: omachace
    Parameters:
       * vnicprofile - vnicprofile where permissions should be removed
       * network - network which is associated with vnicprofile
       * data_center - name of datacenter of network/vnicprofile
       * user_names - list with user names (ie.['user1@..', 'user2@..'])
    Return: status (True if permissions was removed, False otherwise)
    '''
    vnicObj = getVnicProfileObj(vnicprofile, network, data_center=data_center)
    return removeUsersPermissionsFromObject(positive, vnicObj, user_names)


@is_action()
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


@is_action()
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
    netObj = findNetwork(network, data_center)
    return removeUsersPermissionsFromObject(positive, netObj, user_names)


@is_action()
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


@is_action()
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


@is_action()
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


@is_action()
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


@is_action()
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


@is_action()
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


@is_action()
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


@is_action()
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


@is_action()
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


@is_action()
def removeUserPermissionsFromDisk(positive, disk, user_name):
    '''
    Description: remove all permissions on disk of specified user
    Author: omachace
    Parameters:
       * disk - disk where permissions should be removed
       * user_name - user name
    Return: status (True if permissions was removed, False otherwise)
    '''
    diskObj = diskUtil.find(disk)
    return removeUsersPermissionsFromObject(positive, diskObj, [user_name])


@is_action()
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


@is_action()
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


@is_action()
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
            util.logger.error(
                "Domain resource %s has wrong id, %s found but %s expected"
                % (domain.get_name(), domainId, domainHrefId))
            ret = False

    return ret


def hasUserOrGroupPermissionsOnObject(name, obj, role, group=False):
    def getGroupOrUser(perm):
        return perm.get_group() if group else perm.get_user()

    objPermits = permisUtil.getElemFromLink(obj, get_href=False)
    roleNAid = util.find(role).get_id()
    if group:
        user = groupUtil.find(name)
    else:
        user = findUserByUserName(name)

    if user is None:
        return False

    perms = []
    for perm in objPermits:
        mlaObj = getGroupOrUser(perm)
        if mlaObj is not None:
            perms.append((mlaObj.get_id(), perm.get_role().get_id()))

    return (user.get_id(), roleNAid) in perms


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
    return hasUserOrGroupPermissionsOnObject(group_name, obj, role, True)


def hasUserPermissionsOnObject(user_name, obj, role):
    """
    Description: Check if user has permission on object.
    Author: omachace
    Parameters:
       * user_name - user name of user
       * obj - object which should be checked
       * role - name of the role to search for
    Return: True if user has permissions on object False otherwise
    """
    return hasUserOrGroupPermissionsOnObject(user_name, obj, role)
