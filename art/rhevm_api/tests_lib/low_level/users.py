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
from art.rhevm_api.utils.test_utils import get_api, split
from art.core_api.validator import compareElements, compareCollectionSize
from art.core_api import is_action
from art.test_handler.settings import opts

ELEMENT = 'user'
COLLECTION = 'users'
util = get_api(ELEMENT, COLLECTION)
domUtil = get_api('domain', 'domains')
rlUtil = get_api('role', 'roles')
taglUtil = get_api('tag', 'tags')
groupUtil = get_api('group', 'groups')
permsUtil = get_api('permission', 'permissions')

User = getDS('User')
Domain = getDS('Domain')
Groups = getDS('Groups')
Group = getDS('Group')
Roles = getDS('Roles')
Role = getDS('Role')
Tag = getDS('Tag')
Permission = getDS('Permission')

logger = logging.getLogger(__name__)


@is_action()
def addUser(positive, **kwargs):
    '''
    Description: create new user
    Parameters:
       * user_name - user account name
       * domain - user domain
    Return: status (True if user was created properly, False otherwise)
    '''

    user_name = kwargs.pop('user_name')
    domain = kwargs.pop('domain')
    userDomain = Domain(name=domain)
    userName = user_name + "@" + domain

    user = User(domain=userDomain, user_name=userName)
    user, status = util.create(user, positive)

    return status


@is_action()
def addRoleToUser(positive, user, role):
    '''
    Description: add role to user
    Parameters:
       * user - user name
       * role - role to add
    Return: status (True if role was added properly, False otherwise)
    '''
    userObj = util.find(user)
    roleObj = rlUtil.find(role)

    permit = Permission()
    permit.set_role(roleObj)
    permit.set_user(userObj)
    permit, status = permsUtil.create(permit, positive)

    return status


@is_action()
def removeUser(positive, user, domain=None):
    '''
    Description: remove existed user
    Parameters:
       * user - name of user that should be removed
    Return: status (True if user was removed properly, False otherwise)
    '''
    if domain is not None:
        user_name = '%s@%s' % (user, domain)
        userObj = util.query('{0}={1}'.format('usrname', user_name))[0]
    else:
        userObj = util.find(user)
    return util.delete(userObj, positive)


@is_action()
def addTagToUser(positive, user, tag):
    '''
    Description: add tag to a user
    Parameters:
       * user - name of user
       * tag - name of tag to add
    Return: status (True if tag was added properly, False otherwise)
    '''
    userObj = util.find(user)
    usersTags = util.getElemFromLink(userObj, link_name='tags', attr='tag',
                                     get_href=True)

    tagObj = Tag(name=tag)
    tagObj, status = taglUtil.create(tagObj, positive, collection=usersTags)

    return status


@is_action('verifyUser')
def verifyADUserProperties(positive, domain, user, expected_username=None,
                           expected_department=None):
    '''
    Description: verify properties of user from active directory
    Parameters:
       * domain - domain name
       * user - name of user
       * expected_username - expected username
       * expected_department - expected user department
    Return: status (True if all user properties are as expected,
            False otherwise)
    '''
    domainObj = domUtil.find(domain)
    query_user = util.getElemFromElemColl(domainObj, user)
    # query_users = util.query(domainObj.links.get(name='users/search').href,
    #                          "name=" + user)

    userExpected = User(
        user_name=expected_username, department=expected_department)

    return compareElements(userExpected, query_user, util.logger, ELEMENT)


@is_action()
def searchForUserInAD(positive, query_key, query_val, key_name, domain):
    '''
    Description: search for users by desired property in active directory
    Parameters:
       * query_key - name of property to search for
       * query_val - value of the property to search for
       * key_name - name of the property in user object equivalent to
                   query_key, required if expected_count is not set
       * domain - name of active directory domain
    Return: status (True if expected number of users equal to found by search,
            False otherwise)
    '''
    # Get what's needed.
    domainObj = domUtil.find(domain)
    users = util.getElemFromLink(domainObj)

    # Do the matching.
    matches = []
    for user in users:
        try:
            if query_val == getattr(user, key_name):
                matches.append(user)
        except AttributeError:
            pass

    # query for all existed users, for debug purpose
    util.query("")

    # Compare it with the RHEVM results.
    contsraint = "{0}={1}".format(query_key, query_val)
    query_users = util.query(contsraint)
    return compareCollectionSize(query_users, len(matches), util.logger)


@is_action()
def groupExists(positive, group_name):
    '''
    Description: checks whether groups exists or not
    Author: jvorcak
    Parameters:
       * group_name - name of the group to be checked
    Return: status (True if group does exist, False otherwise)
    '''
    groupUtil.find(group_name)
    return True


@is_action()
def addGroup(positive, group_name):
    '''
    Description: create new domain group
    Parameters:
       * group_name - name of domain group
    Return: status (True if group was created properly, False otherwise)
    '''
    group = Group(name=group_name)
    group, status = groupUtil.create(group, positive)

    return status


@is_action()
def deleteGroup(positive, group_name):
    '''
    Description: Delete group with the given name
    Author: jvorcak
    Parameters:
       * group_name - name of the group to be deleted
    Return: status (True if group was deleted, False otherwise)
    '''
    groupObj = groupUtil.find(group_name)
    return util.delete(groupObj, positive)


def loginAsUser(user, domain, password, filter):
    """
    Login as user. User will be used in next REST API call.
    Parameters:
     * user - name of user
     * domain - domain of user
     * password - password of user
     * filter - true if user has non-admin role, false if user has admin role
    """
    get_api.logoff_api()
    msg = "Logged in as %s@%s(filter=%s)"
    global opts
    opts['filter'] = filter
    opts['user'] = user
    opts['user_domain'] = domain
    opts['password'] = password
    logger.info(msg, user, domain, filter)


def fetchUserGroups(positive, user_name):
    '''
    Description: Fetch groups of user
    Parameters:
       * user_name - name of the user
    Return: list of Group objects
    '''
    userObj = util.query('{0}={1}'.format('usrname', user_name))[0]
    return userObj.get_groups().group
