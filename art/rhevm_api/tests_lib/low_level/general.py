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

from art.core_api.apis_utils import getDS
from art.core_api import validator
from art.rhevm_api.utils.test_utils import get_api
from art.rhevm_api.utils.xpath_utils import XPathMatch

util = get_api('', '')
vmUtil = get_api('vm', 'vms')
hostUtil = get_api('host', 'hosts')
domUtil = get_api('domain', 'domains')
userUtil = get_api('user', 'users')
sdUtil = get_api('storage_domain', 'storagedomains')
dcUtil = get_api('data_center', 'datacenters')
permitUtil = get_api('permit', 'capabilities')
versionCaps = permitUtil.get(absLink=False)

xpathMatch = XPathMatch(util)

VM = getDS('VM')


def getSystemVersion():
    '''
    Description: Gets the version of current system
    Author: jlibosva
    Return: Tuple containing version (major, minor)
    '''
    system_version = util.get(href='', absLink=False).get_product_info().get_version()
    system_major = system_version.get_major()
    system_minor = system_version.get_minor()

    return system_major, system_minor


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
            * False if test is not positive, or if some violation from the above
              found.
    '''
    # Check whether positive is sane for this test case.
    assert positive

    system_version = util.get(href='', absLink=False).get_product_info().get_version()
    system_major = system_version.get_major()
    system_minor = system_version.get_minor()
    system_revision = system_version.get_revision()
    system_build = system_version.get_build()

    if not system_version:
        ERR = "The tag product_info->version is either not unique or is not present."
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
        if version.get_current():
            major = version.get_major()
            minor = version.get_minor()

            ERR1 = "Current {0}: '{1}' in not the same as in capabilitites: {2}"
            ERR2 = "'{0}' not found in product info"
            if system_major != major or not convToInt(system_major, 'major version'):
                util.logger.error(ERR1.format('major version', system_major, major))
                error_found = True

            if system_minor != minor or not convToInt(system_minor, 'minor version'):
                util.logger.error(ERR1.format('minor version', system_minor, minor))
                error_found = True

            if system_revision is None or not convToInt(system_revision, 'revision'):
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
     vms = filter(lambda x: x.status.state == 'up', vms)
     util.logger.info('Comparing active vms number')
     if not validator.compareCollectionSize(vms, sumVmsAct, util.logger):
        status = False

     hosts= hostUtil.get(absLink=False)
     sumHostsTotal = getAll.get_summary().get_hosts().total
     util.logger.info('Comparing total hosts number')
     if not validator.compareCollectionSize(hosts, sumHostsTotal, util.logger):
        status = False

     hosts = hostUtil.get(absLink=False)
     sumHostsAct = getAll.get_summary().get_hosts().active
     hosts = filter(lambda x: x.get_status().get_state() == 'up', hosts)
     util.logger.info('Comparing active hosts number')
     if not validator.compareCollectionSize(hosts, sumHostsAct, util.logger):
        status = False

     users= userUtil.get(absLink=False)
     sumUsersTotal = getAll.get_summary().get_users().total
     util.logger.info('Comparing total users number')
     if not validator.compareCollectionSize(users, sumUsersTotal, util.logger):
        status = False

     users_active = []
     domainObj = domUtil.find(domain)
     for user in users:
        domainUser = util.getElemFromElemColl(domainObj, user.get_name(), 'users', 'user')
        if domainUser:
            users_active.append(user)

     util.logger.info('Comparing active users number')
     sumUsersActive = getAll.get_summary().get_users().active
     if not validator.compareCollectionSize(users_active, sumUsersActive, util.logger):
        status = False

     util.logger.info('Comparing total storages number')
     sumSDTotal = getAll.get_summary().get_storage_domains().total
     storageDomains = sdUtil.get(absLink=False)
     if not validator.compareCollectionSize(storageDomains, sumSDTotal, util.logger):
        status = False

     util.logger.info('Comparing active storages number')
     sumSDActive = getAll.get_summary().get_storage_domains().active
     sdActive = []
     dcs = dcUtil.get(absLink=False)
     for dc in dcs:
         dcStorages = util.getElemFromLink(dc, link_name='storagedomains',
                                            attr='storage_domain', get_href=False)
         for dcSd in dcStorages:
            try:
                if dcSd.status.state == 'active':
                    sdActive.append(dcSd)
            except AttributeError:
                pass

     if not validator.compareCollectionSize(storageDomains, sumSDActive, util.logger):
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
            util.logger.error("Response href: %s, status %d is not valid against xsd schema"
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
        product_name = util.get(href='', absLink=False).get_product_info().get_name()
    except IndexError:
        return False, {'product_name': ''}
    return True, {'product_name': product_name}


def checkProductName(positive, name):
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
    return product_name == name if positive else product_name != name
