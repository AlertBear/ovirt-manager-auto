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

from user_roles_tests import config
from user_roles_tests import common
from user_roles_tests import states
from user_roles_tests import roles
from nose.tools import istest
from functools import wraps
from ovirtsdk.xml import params
from ovirtsdk.infrastructure import errors

import unittest2 as unittest
import logging

try:
    from art.test_handler.tools import bz
except ImportError:
    from user_roles_tests.common import bz

try:
    from art.test_handler.tools import tcms
except ImportError:
    from user_roles_tests.common import tcms

LOGGER  = common.logging.getLogger(__name__)
API     = common.API

# Names of created objects. Should be removed at the end of this test module
# and not used by any other test module.
ALT_CLUSTER_NAME = 'user_info_access__cluster'

DC_NAME_B = 'user_info_access__dc_b'
CLUSTER_NAME_B = 'user_info_access__cluster_b'
VM_NAME_B = 'user_info_access__vm_b'

VM1_NAME = 'user_info_access__vm1'
VM2_NAME = 'user_info_access__vm2'
VM3_NAME = 'user_info_access__vm3'
VM4_NAME = 'user_info_access__vm4'
TEMPLATE_NAME = 'user_info_access__template'
TEMPLATE2_NAME = 'user_info_access__template2'
ADMIN_TEMPLATE = 'template1admin'

TCMS_PLAN_ID = 6283

def setUpModule():
    common.addUser()
    common.createVm(VM1_NAME)
    common.createVm(VM2_NAME)

    common.createCluster(ALT_CLUSTER_NAME, config.MAIN_DC_NAME)

    if config.ALT1_HOST_AVAILABLE:
        common.createDataCenter(DC_NAME_B)
        common.createCluster(CLUSTER_NAME_B, DC_NAME_B)
        common.createHost(CLUSTER_NAME_B, hostName=config.ALT1_HOST_ADDRESS,
                          hostAddress=config.ALT1_HOST_ADDRESS,
                          hostPassword=config.ALT1_HOST_ROOT_PASSWORD)
        common.createNfsStorage(storageName=config.ALT1_STORAGE_NAME,
                                address=config.ALT1_STORAGE_ADDRESS,
                                path=config.ALT1_STORAGE_PATH,
                                datacenter=DC_NAME_B,
                                host=config.ALT1_HOST_ADDRESS)
        common.attachActivateStorage(config.ALT1_STORAGE_NAME,
                                datacenter=DC_NAME_B, isMaster=True)

def tearDownModule():
    common.removeVm(VM1_NAME)
    common.removeVm(VM2_NAME)
    common.removeUser()
    common.removeCluster(ALT_CLUSTER_NAME)

    if config.ALT1_HOST_ADDRESS:
        common.removeMasterStorage(storageName=config.ALT1_STORAGE_NAME,
                                   datacenter=DC_NAME_B,
                                   host=config.ALT1_HOST_ADDRESS)
        common.removeHost(hostName=config.ALT1_HOST_ADDRESS)
        common.removeCluster(CLUSTER_NAME_B)
        common.removeDataCenter(DC_NAME_B)


class VmUserInfoTests(unittest.TestCase):
    """ Tests that will be run for each role in VM_ROLES """
    __test__ = False

    @classmethod
    def tearDownClass(self):
        common.loginAsAdmin()
        common.removeAllPermissionFromVm(VM1_NAME)

    def setUp(self):
        common.loginAsUser(filter_=True)

    @tcms(TCMS_PLAN_ID, 171076)
    def testFilter_vms(self):
        """ testFilter_vms """
        msgBlind = "The user can't see VM '%s' where he has permissions" \
                        % VM1_NAME
        msgVisible = "The user can see a VM he has no permissions for"

        vm1 = common.getObjectByName(API.vms, VM1_NAME)
        self.assertTrue(vm1 is not None, msgBlind)
        vm2 = common.getObjectByName(API.vms, VM2_NAME)
        self.assertTrue(vm2 is None, msgVisible)
        vms = API.vms.list()
        self.assertEqual(len(vms), 1, msgVisible)
        LOGGER.info("User can see only VM, he has permissions for.")
        common.loginAsAdmin()
        common.removeAllPermissionFromVm(VM1_NAME)
        common.loginAsUser(filter_=self.filter_)

        vms = API.vms.list()
        self.assertEqual(len(vms), 0, msgVisible)
        vm1 = API.vms.get(VM1_NAME)
        self.assertTrue(vm1 is None, msgVisible)
        LOGGER.info("After deleting permissions from VM, he cant see it anymore")
        common.loginAsAdmin()
        common.givePermissionToVm(VM1_NAME, self.role)

    @tcms(TCMS_PLAN_ID, 171878)
    def testFilter_parentObjects(self):
        """ testFilter_parentObjects """
        DC = config.MAIN_DC_NAME
        CLUSTER = config.MAIN_CLUSTER_NAME

        msgBlind   = "User cannot see %s '%s' where he has permission."
        msgVisible = "User can see %s where he has no permissions. Can see %s"

        datacenters = API.datacenters.list()
        clusters = API.clusters.list()

        # can user see parent objects of the one with permission?
        dc = common.getObjectByName(API.datacenters, config.MAIN_DC_NAME)
        assert dc is not None, msgBlind % ('datacenter', DC)
        cluster = common.getObjectByName(API.clusters, config.MAIN_CLUSTER_NAME)
        assert cluster is not None, msgBlind % ('cluster', CLUSTER)
        LOGGER.info("User can see object where he has permissions.")

        # is user forbidden to see other objects?
        altDc = common.getObjectByName(API.datacenters, DC_NAME_B)
        assert altDc is None, msgVisible % ('datacenter', DC_NAME_B)
        altCluster = common.getObjectByName(API.clusters, ALT_CLUSTER_NAME)
        assert altCluster is None, msgVisible % ('cluster', ALT_CLUSTER_NAME)
        LOGGER.info("User can't see object where he has permissions.")

        assert len(datacenters) == 1, \
            msgVisible % ('datacenters', niceList(datacenters))
        assert len(clusters) == 1, msgVisible % ('clusters', niceList(datacenters))

        # User roles can't see any host
        self.assertRaises(errors.RequestError, API.hosts.list)
        LOGGER.info("Case succed")

    @tcms(TCMS_PLAN_ID, 171077)
    @bz(881145)
    def testEventFilter_vmEvents(self):
        """ testEventFilter_vmEvents """
        msgBlind = "User cannot see VM events where he has permissions"
        msgVisible = "User can see VM events where he has no permissions." + \
                "Can see %s"

        common.loginAsAdmin()
        common.startStopVm(VM1_NAME)
        common.startStopVm(VM2_NAME)
        LOGGER.info("Events on VMs generated")
        common.loginAsUser(filter_=self.filter_)

        # BZ 869334
        eventsVM1 = API.events.list("Vms.name = " + VM1_NAME)
        assert len(eventsVM1) > 0, msgBlind
        LOGGER.info("User can see events from VM he has permissions for.")

        eventsVM2 = API.events.list("Vms.name = " + VM2_NAME)
        assert len(eventsVM2) == 0, msgVisible % niceEventList(eventsVM2)
        LOGGER.info("User can't see events from VM he has not permissions for.")

    @tcms(TCMS_PLAN_ID, 171856)
    @bz(881145)
    @unittest.skipIf(config.ALT1_HOST_AVAILABLE == False, "Requires two hosts")
    def testEventFilter_parentObjectEvents(self):
        """ testEventFilter_parentObjectEvents """
        msgBlind = "User cannot see events for %s where he has permissions"
        msgVisible = "User can see events for %s where he has no permissions." + \
                        "Can see %s"

        common.loginAsAdmin()
        common.createVm(VM_NAME_B, createDisk=False, cluster=CLUSTER_NAME_B)

        objsY = ["Clusters.name = " + config.MAIN_CLUSTER_NAME,
                "Vms.name = " + VM1_NAME,
                "Hosts.name = " + config.MAIN_HOST_NAME]

        objsN = ["Clusters.name = " + CLUSTER_NAME_B,
                "Vms.name = " + VM_NAME_B,
                "Hosts.name = " + config.ALT1_HOST_ADDRESS]

        try :
            common.loginAsUser(filter_=self.filter_)
            for o in objsY:
                events = API.events.list(o)
                assert len(events) > 0, msgBlind
                LOGGER.info("User can see events from object he has permissions for.")

            for o in objsN:
                events = API.events.list(o)
                assert len(events) == 0, msgVisible % niceEventList(events)
                LOGGER.info("User can't see events from VM he has not permissions for.")
        except Exception as err:
            raise err
        finally:
            common.loginAsAdmin()
            common.removeVm(VM_NAME_B)

    @tcms(TCMS_PLAN_ID, 171079)
    def testSpecificId(self):
        """ testSpecificId """
        msgBlind = "User cannot see VM where he has permmissions"
        msgVissible = "User can see VM where he has no permission. Can See '%s'"

        #vm1 = API.vms.get(VM1_NAME)
        vm1 = common.getObjectByName(API.vms, VM1_NAME)
        assert vm1 is not None, msgBlind
        LOGGER.info("User can see VM, where he have permissions")

        #vm2 = API.vms.get(VM2_NAME)
        vm2 = common.getObjectByName(API.vms, VM2_NAME)
        assert vm2 is None, msgVissible % VM2_NAME
        LOGGER.info("User can't see VM, where he have permissions")

    # Is consulted, dont know exactly hiearchy what should be seen or not
    @tcms(TCMS_PLAN_ID, 168714)
    def testAccessDenied(self):
        """ testAccessDenied """
        msg = "User can see %s where he has no permissions. Can see %s"

        storages = API.storagedomains.list()
        templates = API.templates.list()

        # FIXME, behaviour change in future
        try:
            networks = API.networks.list()
        except Exception as e:
            LOGGER.info("User dont have acces to /networks")

        # User should see SD, which is attach to sd, in which is his VM
        assert len(storages) == 1, msg %('storages', niceList(storages))
        # User should se Blank template
        assert len(templates) == 1, msg %('templates', niceList(templates))
        LOGGER.info("User see and don't see resources he can/can't.")

    @tcms(TCMS_PLAN_ID, 175445)
    def testHostInfo(self):
        """ testHostPowerManagementInfo """
        self.assertRaises(errors.RequestError, API.hosts.get, config.MAIN_HOST_NAME)
        LOGGER.info("User can't see any host info")
        self.assertRaises(errors.RequestError, API.hosts.list)
        LOGGER.info("User can't see any hosts info")
        vm = common.getObjectByName(API.vms, VM1_NAME) # Workaround FIXME
        vm.start()
        LOGGER.info("Starting vm to check host info in vm")
        common.waitForState(vm, states.vm.up)
        assert vm.get_host() == None
        LOGGER.info("User can't see any host info in /api/vms")
        assert vm.get_placement_policy() == None
        LOGGER.info("User can't see any placement_policy info in /api/vms")
        vm.stop()
        common.waitForState(vm, states.vm.down)
        LOGGER.info("Stopping vm")

class ViewviewChildrenInfoTests(unittest.TestCase):
    """ Tests if roles that are not able to view childrens, really dont view it. """
    __test__ = True

    # Could change in the future, probably no way how to get it from API.
    # So should be changed if behaviour will change.
    roles_can = [roles.role.PowerUserRole,
                roles.role.TemplateCreator,
                roles.role.VmCreator,
                roles.role.DiskCreator]
    roles_cant = [roles.role.UserRole,
                roles.role.UserVmManager,
                roles.role.DiskOperator,
                roles.role.TemplateOwner]

    @tcms(TCMS_PLAN_ID, 230017)
    def testCanViewChildren(self):
        """ CanViewChildren """
        for role in self.roles_can:
            LOGGER.info("Testing role: %s", role)
            common.givePermissionToCluster(config.MAIN_CLUSTER_NAME, role)
            common.loginAsUser(filter_=True)
            assert len(API.vms.list()) == 0, "User can see vms"
            common.loginAsAdmin()
            common.removeAllPermissionFromCluster(config.MAIN_CLUSTER_NAME)
            LOGGER.info("%s succeed", role)

    @tcms(TCMS_PLAN_ID, 230018)
    def testCantViewChildren(self):
        """ CantViewChildren """
        for role in self.roles_cant:
            LOGGER.info("Testing role: %s", role)
            common.givePermissionToCluster(config.MAIN_CLUSTER_NAME, role)
            common.loginAsUser(filter_=True)
            assert len(API.vms.list()) > 0, "User cant see vms"
            common.loginAsAdmin()
            common.removeAllPermissionFromCluster(config.MAIN_CLUSTER_NAME)
            LOGGER.info("%s succeed", role)

class VmCreatorInfoTests(unittest.TestCase):
    """ Test for VMcreator role """
    __test__ = True  # OK

    @classmethod
    def setUpClass(self):
        self.role = roles.role.VmCreator
        common.givePermissionToCluster(config.MAIN_CLUSTER_NAME, self.role)

    @classmethod
    def tearDownClass(self):
        common.removeAllPermissionFromCluster(config.MAIN_CLUSTER_NAME)

    def setUp(self):
        common.loginAsUser(filter_=True)

    def tearDown(self):
        common.loginAsAdmin()

    @istest
    @bz(881145)
    @tcms(TCMS_PLAN_ID, 174404)
    def vmCreatorClusterAdmin_filter_vms(self):
        """ vmCreatorClusterAdmin_filter_vms """

        common.loginAsAdmin()
        common.givePermissionToCluster(config.MAIN_CLUSTER_NAME, roles.role.UserVmManager)
        common.createVm(VM3_NAME, createDisk=False, cluster=ALT_CLUSTER_NAME)
        common.createVm(VM4_NAME, createDisk=False, cluster=ALT_CLUSTER_NAME)
        common.loginAsUser(filter_=True)

        LOGGER.info("Checking right permission on vms")
        vms = [vm.get_name() for vm in API.vms.list()]
        try:
            assert VM1_NAME in vms, "User can't see " + VM1_NAME
            assert VM2_NAME in vms, "User can't see " + VM2_NAME
            assert VM3_NAME not in vms, "User can see " + VM3_NAME
            assert VM4_NAME not in vms, "User can see " + VM4_NAME
        except Exception as er:
            raise er
        finally:
            common.loginAsAdmin()
            common.removeVm(VM3_NAME)
            common.removeVm(VM4_NAME)

            common.removeAllPermissionFromCluster(config.MAIN_CLUSTER_NAME)
            common.givePermissionToCluster(config.MAIN_CLUSTER_NAME, self.role)

    @istest
    @tcms(TCMS_PLAN_ID, 171080)
    def vmCreator_filter_vms(self):
        """ vmCreator_filter_vms """

        msg = "User can see vms where he has no permissions. Can see %s"

        vms = API.vms.list()
        assert len(vms) == 0, msg % (niceList(vms))
        LOGGER.info("User can't see vms where he has not perms.")

        common.createVm(VM3_NAME, createDisk=False)
        vms = API.vms.list()
        assert len(vms) == 1, msg % (niceList(vms))
        LOGGER.info("User can see only his vms")

        common.removeVm(VM3_NAME)


class TemplateCreatorInfoTests(unittest.TestCase):
    """ Test for VMcreator role """
    __test__ = True

    @classmethod
    def setUpClass(self):
        self.role = roles.role.TemplateCreator

    @classmethod
    def tearDownClass(self):
        common.removeAllPermissionFromVm(VM1_NAME)

    def setUp(self):
        common.loginAsUser(filter_=True)

    def tearDown(self):
        common.loginAsAdmin()

    @istest
    @tcms(TCMS_PLAN_ID, 174403)
    def templateCreator_filter_templatesAndVms(self):
        """ templateCreator_filter_templatesAndVms """
        msgCant =  "User can't see %s '%s' which should see"
        msgCan = "User can see %s '%s' which shouldn't see"

        common.loginAsAdmin()
        common.givePermissionToDc(config.MAIN_DC_NAME, roles.role.TemplateCreator)
        common.givePermissionToVm(VM1_NAME, roles.role.UserRole)

        common.createTemplate(VM2_NAME, TEMPLATE_NAME)
        common.createTemplate(VM1_NAME, ADMIN_TEMPLATE)

        common.loginAsUser(filter_=True)
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
        # tmps == 2(blank + newly created)
        assert TEMPLATE2_NAME in tmps and len(tmps) == 2, msgCan % ('Templates', niceList(tmps))
        LOGGER.info("Case ok")

        common.loginAsAdmin()
        common.removeAllPermissionFromVm(VM1_NAME)
        common.removeAllPermissionFromDc(config.MAIN_DC_NAME)
        common.removeTemplate(TEMPLATE_NAME)
        common.removeTemplate(TEMPLATE2_NAME)
        common.removeTemplate(ADMIN_TEMPLATE)

    # Create some templates in Datacenter1.
    # Create user and give him both roles TemplateCreator and DataCenterAdmin for Datacenter1
    # Create some templates in Datacenter2.
    # - Check /api/templates
    # Should see all templates in Datacenter1, but none in Datacenter2.
    @istest
    @unittest.skipIf(config.ALT1_HOST_AVAILABLE == False, "Requires two hosts")
    @tcms(TCMS_PLAN_ID, 174405)
    def templateCreatorDataCenterAdmin_filter_templates(self):
        """ templateCreatorDataCenterAdmin_filter_templates """
        common.loginAsAdmin()
        common.createTemplate(VM1_NAME, TEMPLATE_NAME)
        common.givePermissionToDc(config.MAIN_DC_NAME, roles.role.TemplateCreator)
        common.givePermissionToDc(config.MAIN_DC_NAME, roles.role.DataCenterAdmin)

        common.createVm(VM_NAME_B, createDisk=False, cluster=CLUSTER_NAME_B)
        common.createTemplate(VM_NAME_B, TEMPLATE2_NAME)
        common.loginAsUser(filter_=True)

        try:
            assert common.getObjectByName(API.templates, TEMPLATE_NAME) is None, "User can see %s" % TEMPLATE_NAME
            assert common.getObjectByName(API.templates, TEMPLATE2_NAME) is None, "User can't see %s" % TEMPLATE2_NAME
        except Exception as e:
            raise e
        finally:
            common.loginAsAdmin()
            common.removeVm(VM_NAME_B)
            common.removeTemplate(TEMPLATE_NAME)
            common.removeTemplate(TEMPLATE2_NAME)
            common.removeAllPermissionFromDc(config.MAIN_DC_NAME)

class CompolexCombinationTests(unittest.TestCase):
    __test__ = True

    # Check BZ 881109 - behaviour could be changed in future.
    @istest
    @tcms(TCMS_PLAN_ID, 174406)
    @unittest.skipIf(config.ALT1_HOST_AVAILABLE == False, "Requires two hosts")
    def complexCombination1_filter_templatesAndVms(self):
        """ complexCombination1_filter_templatesAndVms """
        tmp_vm_2 = 'VM_TEMP_2'
        tmp_vm_3 = 'VM_TEMP_3'
        tmp_template_2 = 'TEMPLATE_TEMP_2'
        tmp_template_3 = 'TEMPLATE_TEMP_3'

        common.loginAsAdmin()
        common.createTemplate(VM1_NAME, TEMPLATE_NAME)
        common.createTemplate(VM2_NAME, TEMPLATE2_NAME)

        common.createVm(tmp_vm_2, cluster=CLUSTER_NAME_B,
                storage=config.ALT1_STORAGE_NAME)
        common.createVm(tmp_vm_3, cluster=ALT_CLUSTER_NAME,
                storage=config.MAIN_STORAGE_NAME)
        common.createTemplate(tmp_vm_2, tmp_template_2)
        common.createTemplate(tmp_vm_3, tmp_template_3)

        common.givePermissionToVm(VM1_NAME, roles.role.UserRole)
        common.givePermissionToObject(common.getObjectByName(API.templates, TEMPLATE2_NAME),
                                    roles.role.TemplateAdmin)
        common.givePermissionToCluster(CLUSTER_NAME_B, roles.role.VmCreator)
        common.givePermissionToDc(DC_NAME_B, roles.role.TemplateCreator)
        common.givePermissionToCluster(ALT_CLUSTER_NAME, roles.role.ClusterAdmin)
        common.loginAsUser(filter_=True)

        try:
            assert common.getObjectByName(API.vms, VM1_NAME) is not None
            assert common.getObjectByName(API.vms, VM2_NAME) is None
            assert common.getObjectByName(API.vms, tmp_vm_2) is None
            assert common.getObjectByName(API.vms, tmp_vm_3) is None

            assert common.getObjectByName(API.templates, TEMPLATE2_NAME) is None
            assert common.getObjectByName(API.templates, tmp_template_3) is None
            assert common.getObjectByName(API.templates, TEMPLATE_NAME)  is None
            assert common.getObjectByName(API.templates, tmp_template_2) is None
        except Exception as e:
            raise e
        finally:
            common.loginAsAdmin()
            common.removeVm(tmp_vm_2)
            common.removeVm(tmp_vm_3)
            common.removeTemplate(TEMPLATE_NAME)
            common.removeTemplate(TEMPLATE2_NAME)
            common.removeTemplate(tmp_template_2)
            common.removeTemplate(tmp_template_3)
            common.removeAllPermissionFromVm(VM1_NAME)
            common.removeAllPermissionFromCluster(CLUSTER_NAME_B)
            common.removeAllPermissionFromCluster(ALT_CLUSTER_NAME)
            common.removeAllPermissionFromDc(DC_NAME_B)


class UserRoleInfoTests(VmUserInfoTests):
    __test__ = True  # OK

    @classmethod
    def setUpClass(self):
        self.role = roles.role.UserRole
        self.filter_ = True
        common.givePermissionToVm(VM1_NAME, self.role)
        common.givePermissionToObject(API.templates.get('Blank'), self.role)

def niceList(theList):
    return ", ".join([l.name for l in theList])

def niceEventList(theList):
    return '\n[' + ',\n'.join([l.get_description() for l in theList]) + ']'
