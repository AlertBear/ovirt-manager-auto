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

import art.rhevm_api.tests_lib.low_level.general as ll_general
from art.core_api.apis_utils import getDS
from art.core_api.validator import compareElements
from art.rhevm_api.utils.test_utils import get_api
from art.test_handler.settings import ART_CONFIG  # noqa

ELEMENT = 'user'
COLLECTION = 'users'
util = get_api(ELEMENT, COLLECTION)
domUtil = get_api('domain', 'domains')
rlUtil = get_api('role', 'roles')
taglUtil = get_api('tag', 'tags')
groupUtil = get_api('group', 'groups')
permsUtil = get_api('permission', 'permissions')
SSH_PUBLIC_KEYS_API = get_api('ssh_public_key', 'sshpublickeys')

User = getDS('User')
Domain = getDS('Domain')
Groups = getDS('Groups')
Group = getDS('Group')
Roles = getDS('Roles')
Role = getDS('Role')
Tag = getDS('Tag')
Permission = getDS('Permission')
ssh_public_key = getDS('SshPublicKey')

logger = logging.getLogger("art.ll_lib.users")


def addUser(positive, **kwargs):
    '''
    Description: create new user
    Parameters:
       * user_name - user account name
       * domain - user domain
       * namespace - users namespace
       * principal - users principal
    Return: status (True if user was created properly, False otherwise)
    '''
    domain = kwargs.pop('domain')
    if domain != 'internal':
        logger.warn(
            "The function 'll.users.addUser' is deprecated for external "
            "domain (%s) ! Please use addExternalUser instead.", domain,
        )
    user_name = kwargs.pop('user_name')
    userDomain = Domain(name=domain)
    userName = user_name + "@" + domain
    namespace = kwargs.pop('namespace', None)
    principal = kwargs.pop('principal', None)

    user = User(domain=userDomain, user_name=userName,
                namespace=namespace, principal=principal)
    user, status = util.create(user, positive)

    return status


def addExternalUser(
    positive, user_name, domain, namespace=None, principal=None
):
    '''
    Create new user in external user database.

    :param user_name: user account name
    :type user_name: str
    :param domain: user domain
    :type domain: str
    :param namespace: users namespace
    :type namespace: str or None
    :param principal: users principal
    :type principal: str or None
    :return: status
    :rtype: bool
    '''
    user = User(
        user_name=user_name,
        domain=Domain(name=domain),
        namespace=namespace,
        principal=principal,
    )
    log_info, log_error = ll_general.get_log_msg("create", "user", user_name)
    logger.info(log_info)
    # https://bugzilla.redhat.com/show_bug.cgi?id=1147900
    _, status = util.create(user, positive, compare=False)
    if status:
        return True
    logger.error(log_error)
    return False


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


def removeUser(positive, user, domain=None, namespace=None):
    '''
    Description: remove existed user
    Parameters:
       * user - name of user that should be removed
    Return: status (True if user was removed properly, False otherwise)
    '''
    if domain is not None:
        user_name = '%s@%s' % (user, domain)
        users = util.query('{0}={1}'.format('usrname', user_name))
        if len(users) <= 0:
            return not positive
        if len(users) > 0 and namespace is not None:
            namespace = namespace.lower()
            user = filter(lambda u: u.get_namespace().lower() == namespace,
                          users) or [None]
            userObj = user[0]
        else:
            userObj = users[0]
    else:
        userObj = util.find(user)
    log_info, log_error = ll_general.get_log_msg("delete", "user", user)
    logger.info(log_info)
    if util.delete(userObj, positive):
        return True
    logger.error(log_error)
    return False


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


def search_user(authz, key, value):
    """
    Search for user in authz by key=value

    :param authz: name of authz where user should be searched
    :type authz: str
    :param key: key by which user should be search
    :type key: str
    :param value: value of the key
    :type value: str
    :return: found user object or None if not found
    """
    query_users = util.query(
        "%s=%s" % (key, value),
        href='%s/%s/%s' % (
            domUtil.links[domUtil.collection_name],
            domUtil.find(authz).id,
            'users?search={query}',
        ),
    )
    if query_users:
        return query_users[0]

    return None


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


def addGroup(positive, group_name, domain=None, namespace=None):
    '''
    Description: create new domain group
    Parameters:
       * group_name - name of domain group
    Return: status (True if group was created properly, False otherwise)
    '''
    if domain:
        domain = Domain(name=domain)
    group = Group(name=group_name, domain=domain, namespace=namespace)
    group, status = groupUtil.create(group, positive)

    return status


def deleteGroup(positive, group_name):
    '''
    Description: Delete group with the given name
    Author: jvorcak
    Parameters:
       * group_name - name of the group to be deleted
    Return: status (True if group was deleted, False otherwise)
    '''
    groupObj = groupUtil.find(group_name)
    return groupUtil.delete(groupObj, positive)


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
    msg = "Logged in as %s@%s(filter=%s), with password: %s"
    global ART_CONFIG
    ART_CONFIG['REST_CONNECTION']['filter'] = filter
    ART_CONFIG['REST_CONNECTION']['user'] = user
    ART_CONFIG['REST_CONNECTION']['user_domain'] = domain
    ART_CONFIG['REST_CONNECTION']['password'] = password
    logger.info(msg, user, domain, filter, password)


def get_user_obj(user_name):
    """
    Get user object.

    Args:
        user_name (str): Name of the user

    Returns:
        User: specific user object
    """
    return util.find(user_name)


def get_ssh_private_keys(user_name):
    """
    Get ssh private keys from user options on engine web page.

    Args:
        user_name (str): name of authorization user to get keys for.

    Returns:
        list: list of SshPublicKey class objects
    """
    return SSH_PUBLIC_KEYS_API.getElemFromLink(get_user_obj(user_name))


def del_ssh_private_key(ssh_obj):
    """
    Delete ssh private keys from user options on engine web page.
    Args:
        ssh_obj (obj): object of ssh private key.

    Returns:
        bool: True/False depending on the action result.
    """
    return SSH_PUBLIC_KEYS_API.delete(ssh_obj, positive=True)


def set_ssh_private_key(user_name, key):
    """
    Set ssh private keys from user options on engine web page.
    Args:
        user_name (str): name of authorization user to get keys for.
        key (str): public key which will be uploaded.

    Returns:
        tuple: with 2 elements, object of Action class from data structures and
               bool with result - True/False
    """
    collection = SSH_PUBLIC_KEYS_API.getElemFromLink(
        get_user_obj(user_name),
        get_href=True
    )
    key_obj = ssh_public_key(content=key)

    return SSH_PUBLIC_KEYS_API.create(
        key_obj,
        positive=True,
        collection=collection,
        async=True
    )


def get_user_id(user_name):
    """
    Get user id

    Args:
        user_name(str): User name

    Returns:
        str: user id
    """
    return util.find(user_name).get_id()
