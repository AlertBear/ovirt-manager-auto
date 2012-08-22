#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (c) 2012 Red Hat, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#           http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

__test__ = True

import config
import common
import states
import unittest2 as unittest
import sys
from nose.tools import istest
from functools import wraps

from ovirtsdk.xml import params
from ovirtsdk.infrastructure import errors

import logging

LOGGER  = common.logging.getLogger(__name__)
API     = common.API


# Names of created objects. Should be removed at the end of this test module
# and not used by any other test module.
ALT_DC_NAME = 'user_info_access__dc'
ALT_CLUSTER_NAME = 'user_info_access__cluster'
VM1_NAME = 'user_info_access__vm1'
VM2_NAME = 'user_info_access__vm2'
VM3_NAME = 'user_info_access__vm3'
VM4_NAME = 'user_info_access__vm4'
TEMPLATE_NAME = 'user_info_access__template'
TEMPLATE2_NAME = 'user_info_access__template2'
ADMIN_TEMPLATE = 'template1admin'

def logger(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        LOGGER.info("Running: %s" % (func.__name__))
        try:
            result = func(*args, **kwargs)
            LOGGER.info("Case '%s' successed" % func.__name__)
            return result
        except Exception as err:
            LOGGER.info("!ERROR! => " + str(err))
            raise err

def setUpModule():
    common.addUser()
    common.createVm(VM1_NAME, createDisk=False)
    common.createVm(VM2_NAME, createDisk=False)
    common.createDataCenter(ALT_DC_NAME)
    common.createCluster(ALT_CLUSTER_NAME, ALT_DC_NAME)


def tearDownModule():
    common.removeVm(VM1_NAME)
    common.removeVm(VM2_NAME)
    common.removeUser()
    common.removeCluster(ALT_CLUSTER_NAME)
    common.removeDataCenter(ALT_DC_NAME)


class VmUserInfoTests(unittest.TestCase):
    """ Tests that will be run for each role in VM_ROLES """
    __test__ = False

    @classmethod
    def tearDownClass(self):
        common.removeAllPermissionFromVm(VM1_NAME)

    def setUp(self):
        common.loginAsUser()

    def tearDown(self):
        common.loginAsAdmin()

    @istest
    @logger
    def testFilter_vms(self):
        """ testFilter_vms """
        msgBlind = "The user can't see VM '%s' where he has permissions" \
                    % VM1_NAME
        msgVisible = "The user can see a VM he has no permissions for"

        vm1 = API.vms.get(VM1_NAME)
        self.assertTrue(vm1 is not None, msgBlind)
        vm2 = API.vms.get(VM2_NAME)
        self.assertTrue(vm2 is None, msgVisible)
        vms = API.vms.list()
        self.assertEqual(len(vms), 1, msgVisible)

        common.loginAsAdmin()
        common.removeAllPermissionFromVm(VM1_NAME)
        common.loginAsUser()

        vms = API.vms.list()
        self.assertEqual(len(vms), 0, msgVisible)
        vm1 = API.vms.get(VM1_NAME)
        self.assertTrue(vm1 is None, msgVisible)


    @istest
    @logger
    def testFilter_parentObjects(self):
        """ testFilter_parentObjects """
        DC = config.MAIN_DC_NAME
        CLUSTER = config.MAIN_CLUSTER_NAME

        msgBlind   = "User cannot see %s '%s' where he has permission."
        msgVisible = "User can see %s where he has no permissions. Can see %s"

        datacenters = API.datacenters.list()
        clusters = API.clusters.list()


        # can user see parent objects of the one with permission?
        dc = API.datacenters.get(config.MAIN_DC_NAME)
        assert dc is not None, msgBlind % ('datacenter', DC)
        cluster = API.clusters.get(config.MAIN_CLUSTER_NAME)
        assert cluster is not None, msgBlind % ('cluster', CLUSTER)

        # is user forbidden to see other objects?
        altDc = API.datacenters.get(ALT_DC_NAME)
        assert altDc is None, msgVisible % ('datacenter', ALT_DC_NAME)
        altCluster = API.clusters.get(ALT_CLUSTER_NAME)
        assert altCluster is None, msgVisible % ('cluster', ALT_CLUSTER_NAME)

        assert len(datacenters) == 1, \
            msgVisible % ('datacenters', niceList(datacenters))
        assert len(clusters) == 1, msgVisible % ('clusters', niceList(datacenters))

        if config.TWO_HOSTS_AVAILABLE:
            hosts = API.hosts.list()
            assert len(hosts) == 1, msgVisible % ('hosts', niceList(hosts))
            # TODO

    @istest
    @logger
    def testEventFilter_vmEvents(self):
        """ testEventFilter_vmEvents """
        msgBlind = "User cannot see VM events where he has permissions"
        msgVisible = "User can see VM events where he has no permissions." + \
                "Can see %s"

        common.startStopVm(VM1_NAME)
        common.startStopVm(VM2_NAME)

        eventsVM1 = API.events.list("Vms.name = " + VM1_NAME)
        assert len(eventsVM1) > 0, msgBlind

        eventsVM2 = API.events.list("Vms.name = " + VM2_NAME)
        assert len(eventsVM2) == 0, msgVisible % niceEventList(eventsVM2)

    # TODO:
    #@istest
    def testEventFilter_parentObjectEvents(self):
        """ testEventFilter_parentObjectEvents """
        msgBlind = "User cannot see events for %s where he has permissions"
        msgVisible = "User can see events for %s where he has no permissions." + \
                        "Can see %s"

    @istest
    @logger
    def testSpecificId(self):
        """ testSpecificId """
        msgBlind = "User cannot see VM where he has permmissions"
        msgVissible = "User can see VM where he has no permission. Can See '%s'"

        vm1 = API.vms.get(VM1_NAME)
        assert vm1 is not None, msgBlind

        vm2 = API.vms.get(VM2_NAME)
        assert vm2 is None, msgVissible % VM2_NAME

    @istest
    @logger
    def testAccessDenied(self):
        """ testAccessDenied """
        msg = "User can see %s where he has no permissions. Can see %s"

        storages = API.storagedomains.list()
        templates = API.templates.list()
        networks = API.networks.list()

        assert len(storages) == 0, msg %('storages', niceList(storages))
        assert len(templates) == 0, msg %('templates', niceList(templates))
        assert len(networks) == 0, msg %('networks', niceList(networks))

    @istest
    @logger
    def testHostPowerManagementInfo(self):
        """ testHostPowerManagementInfo """
        host = API.hosts.get(config.MAIN_HOST_NAME)
        pm = host.get_power_management() # or maybe an exception?
        assert pm is None, "User has access to power management info"


class VmCreatorInfoTests(unittest.TestCase):
    """ Test for VMcreator role """
    __test__ = True

    @classmethod
    def setUpClass(self):
        self.role = 'VmCreator'
        common.givePermissionToCluster(config.MAIN_CLUSTER_NAME, self.role)

    @classmethod
    def tearDownClass(self):
        common.removeAllPermissionFromCluster(config.MAIN_CLUSTER_NAME)

    def setUp(self):
        common.loginAsUser()

    def tearDown(self):
        common.loginAsAdmin()

    @istest
    @logger
    def vmCreatorClusterAdmin_filter_vms(self):
        """ vmCreatorClusterAdmin_filter_vms """
        common.loginAsAdmin()
        common.givePermissionToCluster(config.MAIN_CLUSTER_NAME, 'ClusterAdmin')
        common.createVm(VM3_NAME, createDisk=False, cluster=ALT_CLUSTER_NAME)
        common.createVm(VM4_NAME, createDisk=False, cluster=ALT_CLUSTER_NAME)
        common.loginAsUser()

        LOGGER.info("Checking right permission on vms")
        vms = [vm.get_name() for vm in API.vms.list()]
        assert VM1_NAME in vms, "User can't see " + VM1_NAME
        assert VM2_NAME in vms, "User can't see " + VM2_NAME
        assert VM3_NAME not in vms, "User can see " + VM3_NAME
        assert VM4_NAME not in vms, "User can see " + VM4_NAME


    @istest
    @logger
    def vmCreator_filter_vms(self):
        """ vmCreator_filter_vms """
        msg = "User can see vms where he has no permissions. Can see %s"

        vms = API.vms.list()
        assert len(vms) == 0, msg % (niceList(vms))

        common.createVm(VM3_NAME, createDisk=False)
        vms = API.vms.list()
        assert len(vms) == 1, msg % (niceList(vms))


class TemplateCreatorInfoTests(unittest.TestCase):
    """ Test for VMcreator role """
    __test__ = True

    @classmethod
    def setUpClass(self):
        self.role = 'TemplateCreator'
        common.givePermissionToVm(VM1_NAME, self.role)

    @classmethod
    def tearDownClass(self):
        common.removeAllPermissionFromVm(VM1_NAME)

    def setUp(self):
        common.loginAsUser()

    def tearDown(self):
        common.loginAsAdmin()

    @istest
    @logger
    def templateCreator_filter_templatesAndVms(self):
        """ templateCreator_filter_templatesAndVms """
        msgCant =  "User can't see %s '%s' which should see"
        msgCan = "User can see %s '%s' which shouldn't see"


        common.loginAsAdmin()
        common.givePermissionToDc(config.MAIN_DC_NAME, 'TemplateCreator')
        common.givePermissionToVm(VM1_NAME, 'UserRole')

        common.createTemplate(VM2_NAME, TEMPLATE_NAME)
        common.createTemplate(VM1_NAME, ADMIN_TEMPLATE)

        common.loginAsUser()
        LOGGER.info("Cheking right permissions for all vms")
        vms = [vm.get_name() for vm in API.vms.list()]
        assert VM1_NAME in vms, msgCant % ('VM', VM1_NAME)
        assert VM2_NAME not in vms, msgCan % ('VM', VM2_NAME)

        LOGGER.info("Cheking right permissions for all templates")
        tmps = [tmp.get_name() for tmp in API.templates.list()]
        assert TEMPLATE_NAME not in tmps, msgCan % ('Template', TEMPLATE_NAME)
        assert ADMIN_TEMPLATE not in tmps, msgCan % ('Template', ADMIN_TEMPLATE)

        common.createTemplate(VM1_NAME, TEMPLATE2_NAME)
        LOGGER.info("Cheking right permissions for " + TEMPLATE2_NAME)
        tmps = [tmp.get_name() for tmp in API.templates.list()]
        assert TEMPLATE2_NAME in tmps and len(tmps) == 1, msgCan % ('Templates', niceList(tmps))

    #TODO
    #@istest
    def templateCreatorDataCenterAdmin_filter_templates(self):
        """ templateCreatorDataCenterAdmin_filter_templates """
        pass

    # TODO
    #@istest
    def complexCombination1_filter_templatesAndVms(self):
        """ complexCombination1_filter_templatesAndVms """
        pass


class UserRoleInfoTests(VmUserInfoTests):
    __test__ = True

    @classmethod
    def setUpClass(self):
        self.role = 'UserRole'
        common.givePermissionToVm(VM1_NAME, self.role)


class PowerUserRoleInfoTests(VmUserInfoTests):
    __test__ = False

    @classmethod
    def setUpClass(self):
        self.role = 'PowerUserRole'
        common.givePermissionToVm(VM1_NAME, self.role)


class UserVmManagerInfoTests(VmUserInfoTests):
    __test__ = False

    @classmethod
    def setUpClass(self):
        self.role = 'UserVmManager'
        common.givePermissionToVm(VM1_NAME, self.role)


def niceList(theList):
    return ", ".join([l.name for l in theList])

def niceEventList(theList):
    return '\n[' + ',\n'.join([l.get_description() for l in theList]) + ']'
