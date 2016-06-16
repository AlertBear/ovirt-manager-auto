# Copyright (C) 2011 Red Hat, Inc.
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

from collections import namedtuple
from art.core_api import validator
from art.core_api.apis_utils import getDS
import art.test_handler.exceptions as exceptions
from art.rhevm_api.utils.test_utils import get_api

util = get_api('', '')
vmUtil = get_api('vm', 'vms')
hostUtil = get_api('host', 'hosts')
domUtil = get_api('domain', 'domains')
userUtil = get_api('user', 'users')
sdUtil = get_api('storage_domain', 'storagedomains')
dcUtil = get_api('data_center', 'datacenters')
permitUtil = get_api('permit', 'capabilities')
try:
    versionCaps = permitUtil.get(absLink=False)
except KeyError:
    util.logger.warn("Can't get list of permissions from capabilities")
    pass


VM = getDS('VM')


ProductVersion = namedtuple('ProductVersion', ['major',
                                               'minor',
                                               'build',
                                               'revision'])


def getSystemVersion():
    '''
    Description: Gets the version of current system
    Author: cmestreg
    Return: named tuple ProductVersion(major, minor, build, revision)
    '''
    system_version = util.get(
        href='', absLink=False).get_product_info().get_version()

    fields = (getattr(system_version, "get_%s" % field)()
              for field in ProductVersion._fields)
    return ProductVersion(*fields)


def checkSystemVersionTag(positive):
    '''
    Checks whether there are attributes named:
        revision build minor major
    in the api->system_version tag, whether it is unique and whether the
    subtags are unique and their values converts to integer numbers.

    Author: jhenner
    Parameters:
        None
    Return:
        bool
            * True iff error not detected
            * False if test is not positive, or if some violation from the
              above found.
    '''
    # Check whether positive is sane for this test case.
    assert positive

    system_version = util.get(href='',
                              absLink=False).get_product_info().get_version()
    system_major = system_version.get_major()
    system_minor = system_version.get_minor()
    system_revision = system_version.get_revision()
    system_build = system_version.get_build()

    if not system_version:
        ERR = "The tag product_info->version is either not unique or is not"
        " present."
        util.logger.error(ERR)
        return False
    MSG = "The tag product_info->version is unique and present."
    util.logger.info(MSG)

    # find the declared values for that.
    error_found = False
    version_caps = versionCaps
    if not isinstance(versionCaps, list):
        version_caps = versionCaps.get_version()
    for version in version_caps:
        if version.get_current() in [True, 'true']:
            major = version.get_major()
            minor = version.get_minor()

            ERR1 = "Current {0}: '{1}' in not the same as in capabilities: {2}"
            ERR2 = "'{0}' not found in product info"
            if system_major != major or not convToInt(system_major,
                                                      'major version'):
                util.logger.error(ERR1.format('major version', system_major,
                                              major))
                error_found = True

            if system_minor != minor or not convToInt(system_minor,
                                                      'minor version'):
                util.logger.error(ERR1.format('minor version', system_minor,
                                              minor))
                error_found = True

            if system_revision is None or not convToInt(system_revision,
                                                        'revision'):
                util.logger.error(ERR2.format('revision'))
                error_found = True

            if system_build is None or not convToInt(system_build, 'build'):
                util.logger.error(ERR2.format('build'))
                error_found = True

    return not error_found


def convToInt(num, attr):

    try:
        int(num)
    except ValueError as e:
        util.logger.error(e)
        ERR = "Couldn't convert '{0}' to a int number."
        util.logger.error(ERR.format(attr))
        return False

    return True


def checkSummary(positive, domain):
    '''
    Description: validate system summary statistics values
    Author: edolinin
    Parameters:
      no
    Return: status (True if all statistics values are correct, False otherwise)
    '''

    getAll = util.get(href='', absLink=False)
    status = True

    vms = vmUtil.get(absLink=False)
    sumVmsTotal = getAll.get_summary().get_vms().total
    util.logger.info('Comparing total vms number')
    if not validator.compareCollectionSize(vms, sumVmsTotal, util.logger):
        status = False

    vms = vmUtil.get(absLink=False)
    sumVmsAct = getAll.get_summary().get_vms().active
    vms = filter(lambda x: x.get_status() == 'up', vms)
    util.logger.info('Comparing active vms number')
    if not validator.compareCollectionSize(vms, sumVmsAct, util.logger):
        status = False

    hosts = hostUtil.get(absLink=False)
    sumHostsTotal = getAll.get_summary().get_hosts().total
    util.logger.info('Comparing total hosts number')
    if not validator.compareCollectionSize(hosts, sumHostsTotal, util.logger):
        status = False

    hosts = hostUtil.get(absLink=False)
    sumHostsAct = getAll.get_summary().get_hosts().active
    hosts = filter(lambda x: x.get_status() == 'up', hosts)
    util.logger.info('Comparing active hosts number')
    if not validator.compareCollectionSize(hosts, sumHostsAct, util.logger):
        status = False

    users = userUtil.get(absLink=False)
    sumUsersTotal = getAll.get_summary().get_users().total
    util.logger.info('Comparing total users number')
    if not len(users) <= sumUsersTotal:
        util.logger.error(
            "Collection size is wrong, "
            "actual should be smaller or equal to expected. "
            "expected is: %(exp)s, actual is: %(act)s",
            {'exp': sumUsersTotal, 'act': len(users)}
        )
        status = False
    else:
        util.logger.debug(
            "Collection size is correct: %(exp)s is bigger then %(act)s since "
            "the number of returned users is limited for performance reasons",
            {'exp': sumUsersTotal, 'act': len(users)}
        )

    util.logger.info('Comparing total storage number')
    sumSDTotal = getAll.get_summary().get_storage_domains().total
    storageDomains = sdUtil.get(absLink=False)
    if not validator.compareCollectionSize(
            storageDomains, sumSDTotal, util.logger):
        status = False

    util.logger.info('Comparing active storages number')
    sumSDActive = getAll.get_summary().get_storage_domains().active
    sdActive = []
    dcs = dcUtil.get(absLink=False)
    for dc in dcs:
        dcStorages = util.getElemFromLink(
            dc, link_name='storagedomains', attr='storage_domain',
            get_href=False)
        for dcSd in dcStorages:
            try:
                if dcSd.get_status() == 'active':
                    sdActive.append(dcSd)
            except AttributeError:
                pass

    if not validator.compareCollectionSize(sdActive, sumSDActive, util.logger):
        status = False

    return status


def removeNonExistingVm(positive, entity_id='non_existing_object_id'):
    '''
    Description: Tries to remove non-existing object
    Author: jvorcak
    Return: True if http request returned 404 status, False otherwise
    '''
    vm = VM()
    vm.set_id(entity_id)
    vm.set_href('vms/' + entity_id)
    return vmUtil.delete(vm, False)


def checkResponsesAreXsdValid():
    '''
    Checks for validations errors found out by restutils
    Author: jvorcak
    Return: True if all responses were valid against xsd schema
            False otherwise
    '''
    ret = True
    try:
        for error in util.xsd_schema_errors:
            href, ret, ex = error
            util.logger.error(
                "Response href: %s, status %d is not valid against xsd schema"
                % (href, ret['status']))
            util.logger.error("Response body: %s" % ret['body'])
            util.logger.error("Exception is: %s" % ex)
            ret = False
    except AttributeError:
        pass

    return ret


def getProductName():
    '''
    Get product name
    Author: atal
    Return True, dict(product name) is succeeded, Fals, dict('') otherwise
    '''
    try:
        product_name = util.get(
            href='', absLink=False).get_product_info().get_name()
    except IndexError:
        return False, {'product_name': ''}
    return True, {'product_name': product_name}


def checkProductName(name):
    '''
    Checks whether the product's name is the same as name parameter.
    Author: gleibovi
    Return True if the name is the same as product_name, False if not or
    failed to get product name.
    '''
    status, ret = getProductName()
    if not status:
        return status
    product_name = ret['product_name']

    if product_name != name:
        util.logger.error(
            "Product name is wrong, expected: '%s', actual: '%s'"
            % (name, product_name))
        return False

    util.logger.info("Product name is correct: '%s'" % name)
    return True


def prepare_ds_object(object_name, **kwargs):
    """
    Create new data structure object

    :param object_name: name of instance to create
    :param kwargs: parameters of instance
    :return: data structure object or raise exceptions
    """
    ds_object = getDS(object_name)()
    for key, val in kwargs.iteritems():
        if hasattr(ds_object, key):
            setattr(ds_object, key, val)
        else:
            raise exceptions.RHEVMEntityException(
                "%s object has no attribute: %s" % (object_name, key)
            )
    return ds_object


def get_object_name_by_id(object_api, object_id):
    """
    Get object name by object object_id

    :param object_api: Object API (CLUSTER_API for example)
    :type object_api: class
    :param object_id: Object ID
    :type id: str
    :return: Object name
    :rtype: str
    """
    return object_api.find(object_id, "id").get_name()


def get_log_msg(
    action, obj_type, obj_name, positive=True, extra_txt="", **kwargs
):
    """
    Generate info and error logs for action on object.

    Args:
        action (str): The action to perform on the object
            (create, update, remove)
        obj_type (str): Object type
        obj_name (str): Object name
        positive (bool): Expected results
        extra_txt (str): Extra text to add to the log
        kwargs (dict): Parameters for the action if any

    Returns:
        tuple: Log info and log error text
    """
    if kwargs:
        kwargs = prepare_kwargs_for_log(**kwargs)

    action = action.capitalize()
    with_kwargs = "with %s" % kwargs if kwargs else ""
    state = "Succeeded to" if not positive else "Failed to"
    info_text = "%s %s %s %s %s" % (
        action, obj_type, obj_name, with_kwargs, extra_txt
    )
    log_info_txt = info_text if positive else "Negative: %s" % info_text
    log_error_txt = ("%s %s" % (state, info_text))
    return log_info_txt, log_error_txt


def prepare_kwargs_for_log(**kwargs):
    """
    Prepare kwargs for get_log_msg()

    Args:
        kwargs (dict): kwargs to prepare

    Returns:
        dict: kwargs after prepare
    """
    new_kwargs = dict()
    for k, v in kwargs.iteritems():
        if v is None:
            continue
        try:
            new_kwargs[k] = v.name
        except AttributeError:
            new_kwargs[k] = v
    return new_kwargs
