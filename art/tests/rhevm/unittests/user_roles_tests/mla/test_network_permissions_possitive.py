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
# limitations under the License.
#

__test__ = True

from user_roles_tests import config, common, states
from user_roles_tests.roles import role
from nose.tools import istest

import unittest2 as unittest
import logging

from art.rhevm_api.tests_lib.low_level import mla, networks
from art.rhevm_api.tests_lib.low_level import users, vms, disks
from art.rhevm_api.tests_lib.low_level import templates
from art.test_handler.settings import opts
from art.core_api.apis_exceptions import EntityNotFound

try:
    from art.test_handler.tools import bz
except ImportError:
    from user_roles_tests.common import bz

try:
    from art.test_handler.tools import tcms
except ImportError:
    from user_roles_tests.common import tcms

LOGGER  = common.logging.getLogger(__name__)

VM_NAME = 'permissions_vm'
TEMPLATE_NAME = 'perms_template'
NIC_NAME = 'nic1'
NIC_NAME2 = 'nic2'
NIC_NAME3 = 'nic3'
NIC_NAME4 = 'nic4'
ROLE_NAME = '_NetworkCreator'

TCMS_PLAN_ID_POS = 7995

def loginAsUser(**kwargs):
    msg = "Logged in as %s@%s(filter=%s)"
    global opts
    opts['headers']['Filter'] = kwargs.pop('filter_', 'true')
    opts['user'] = kwargs.pop('userName', config.USER_NAME)
    opts['user_domain'] = config.USER_DOMAIN
    LOGGER.info(msg % (opts['user'], opts['user_domain'], opts['headers']['Filter']))

def loginAsAdmin():
    msg = "Logged in as %s@%s"
    global opts
    opts['headers']['Filter'] = 'false'
    opts['user'] = config.OVIRT_USERNAME
    opts['user_domain'] = config.OVIRT_DOMAIN
    LOGGER.info(msg % (opts['user'], opts['user_domain']))

def setUpModule():
    assert users.addUser(True, user_name=config.USER_NAME,
            domain=config.USER_DOMAIN)
    assert users.addUser(True, user_name=config.USER_NAME2,
            domain=config.USER_DOMAIN)
    assert users.addUser(True, user_name=config.USER_NAME3,
            domain=config.USER_DOMAIN)

def tearDownModule():
    loginAsAdmin()
    assert users.removeUser(True, config.USER_NAME)
    assert users.removeUser(True, config.USER_NAME2)
    assert users.removeUser(True, config.USER_NAME3)

def ignoreAllExceptions(method, **kwargs):
    '''
    Run method and ignore all exceptions.
    '''
    try:
        method(**kwargs)
    except Exception as e:
        pass

class NetworkingPossitive(unittest.TestCase):
    """ https://tcms.engineering.redhat.com/plan/7995 """
    __test__ = True

    def setUp(self):
        loginAsAdmin()

    def tearDown(self):
        # CleanUp
        loginAsAdmin()
        ignoreAllExceptions(vms.removeVm, positive=True, vm=VM_NAME)
        ignoreAllExceptions(templates.removeTemplate, positive=True,
            template=TEMPLATE_NAME)

        for network in [config.NETWORK_NAME1, config.NETWORK_NAME2,
                config.NETWORK_NAME3, config.NETWORK_NAME4]:
            ignoreAllExceptions(networks.removeNetwork, positive=True,
                    network=network, data_center=config.MAIN_DC_NAME)

        mla.removeUsersPermissionsFromDatacenter(True, config.MAIN_DC_NAME,
                [config.USER, config.USER2, config.USER3])
        mla.removeUsersPermissionsFromCluster(True, config.MAIN_CLUSTER_NAME,
                [config.USER, config.USER2, config.USER3])
        ignoreAllExceptions(mla.removeRole, positive=True, role=ROLE_NAME)

    @istest
    @tcms(TCMS_PLAN_ID_POS, 231821)
    def createNetworkInDC(self):
        """ CreateNetworkInDc """
        # Setup
        assert mla.addPermissionsForDataCenter(True, config.USER_NAME,
                config.MAIN_DC_NAME, role=role.SuperUser)
        assert mla.addPermissionsForDataCenter(True, config.USER_NAME2,
                config.MAIN_DC_NAME, role=role.DataCenterAdmin)
        assert mla.addPermissionsForDataCenter(True, config.USER_NAME3,
                config.MAIN_DC_NAME, role=role.NetworkAdmin)

        # Actions
        for u in [config.USER_NAME, config.USER_NAME2, config.USER_NAME3]:
            loginAsUser(userName=u, filter_=False)
            assert networks.addNetwork(True, name=config.NETWORK_NAME1,
                    data_center=config.MAIN_DC_NAME)
            loginAsAdmin()
            assert networks.removeNetwork(True, network=config.NETWORK_NAME1,
                    data_center=config.MAIN_DC_NAME)

    @istest
    @tcms(TCMS_PLAN_ID_POS, 231822)
    def editNetworkInDC(self):
        """ Edit network in DC """
        # Setup
        assert networks.addNetwork(True, name=config.NETWORK_NAME1,
                data_center=config.MAIN_DC_NAME)
        assert mla.addPermissionsForNetwork(True, config.USER_NAME,
                config.NETWORK_NAME1, data_center=config.MAIN_DC_NAME,
                role=role.DataCenterAdmin)
        assert mla.addPermissionsForNetwork(True, config.USER_NAME2,
                config.NETWORK_NAME1, data_center=config.MAIN_DC_NAME,
                role=role.NetworkAdmin)

        # Actions
        mtu = 800
        stp = True
        for uName in [config.USER_NAME, config.USER_NAME2]:
            loginAsUser(userName=uName, filter_=False)
            assert networks.updateNetwork(True, config.NETWORK_NAME1,
                    data_center=config.MAIN_DC_NAME, mtu=mtu,
                    stp=str(stp).lower())
            mtu += 100
            stp = not stp

    @istest
    @tcms(TCMS_PLAN_ID_POS, 231823)
    def attachingNetworkToCluster(self):
        """ Attaching network to cluster """
        # Setup
        assert networks.addNetwork(True, name=config.NETWORK_NAME1,
                data_center=config.MAIN_DC_NAME)
        assert mla.addPermissionsForNetwork(True, config.USER_NAME,
                config.NETWORK_NAME1, data_center=config.MAIN_DC_NAME,
                role=role.NetworkAdmin)
        assert mla.addClusterPermissionsToUser(True, config.USER_NAME2,
                cluster=config.MAIN_CLUSTER_NAME)

        # Actions
        loginAsUser(filter_=False)
        assert networks.addNetworkToCluster(True, config.NETWORK_NAME1,
                config.MAIN_CLUSTER_NAME)
        assert networks.removeNetworkFromCluster(True, config.NETWORK_NAME1,
                config.MAIN_CLUSTER_NAME)

        loginAsUser(userName=config.USER_NAME2, filter_=False)
        assert networks.addNetworkToCluster(False, config.NETWORK_NAME1,
                config.MAIN_CLUSTER_NAME)
        LOGGER.info("ClusterAdmin can't attach network to cluster.")

    def _testSwitchingDisplayAndRequired(self, required=None, display=None):
        ''' '''
        # Setup
        assert networks.addNetwork(True, name=config.NETWORK_NAME1,
                data_center=config.MAIN_DC_NAME)
        assert mla.addClusterPermissionsToUser(True, config.USER_NAME,
                cluster=config.MAIN_CLUSTER_NAME)
        assert mla.addPermissionsForNetwork(True, config.USER_NAME2,
                config.NETWORK_NAME1, data_center=config.MAIN_DC_NAME,
                role=role.NetworkAdmin)
        assert networks.addNetworkToCluster(True, config.NETWORK_NAME1,
                config.MAIN_CLUSTER_NAME)

        assert networks.updateClusterNetwork(True,
                config.MAIN_CLUSTER_NAME, config.NETWORK_NAME1,
                required=None if required is None else required,
                display=None if display is None else display)

        # Actions
        for uName in [config.USER_NAME, config.USER_NAME2]:
            loginAsUser(userName=uName, filter_=False)
            assert networks.updateClusterNetwork(True,
                    config.MAIN_CLUSTER_NAME, config.NETWORK_NAME1,
                    required=None if required is None else not required,
                    display=None if display is None else not display)
            assert networks.updateClusterNetwork(True,
                    config.MAIN_CLUSTER_NAME, config.NETWORK_NAME1,
                    required=None if required is None else required,
                    display=None if display is None else display)

    @istest
    @tcms(TCMS_PLAN_ID_POS, 231824)
    def requiredToNonRequiredAndViceVersa(self):
        """ Required to non-required and vice versa """
        self._testSwitchingDisplayAndRequired(required=True)

    @istest
    @tcms(TCMS_PLAN_ID_POS, 236073)
    def displayNetwork(self):
        """ Display network """
        self._testSwitchingDisplayAndRequired(display=True)

    @istest
    @tcms(TCMS_PLAN_ID_POS, 231826)
    def attachDetachNetworkToVM(self):
        """ Attach/Detach a network to VM  """
        # Setup
        assert vms.createVm(True, VM_NAME, '', cluster=config.MAIN_CLUSTER_NAME,
            storageDomainName=config.MAIN_STORAGE_NAME, size=common.GB)
        assert mla.addVMPermissionsToUser(True, config.USER_NAME, VM_NAME)

        # Actions
        loginAsUser()
        assert vms.addNic(True, VM_NAME, name=NIC_NAME,
                network=config.NETWORK_NAME, interface='virtio')
        assert vms.removeNic(True, VM_NAME, NIC_NAME)

    @istest
    @tcms(TCMS_PLAN_ID_POS, 231827)
    def visibleNetworksAndManipulations(self):
        """ Visible networks and manipulations """
        # Setup
        for num in ['1', '2', '3', '4']:  # Add networks 1,2,3,4 and assign them
            assert networks.addNetwork(True, name=config.NETWORK_NAME + num,
                    data_center=config.MAIN_DC_NAME)
            assert mla.addPermissionsForNetwork(True, config.USER_NAME,
                    config.NETWORK_NAME + num, data_center=config.MAIN_DC_NAME,
                    role=role.NetworkUser)
            assert networks.addNetworkToCluster(True, config.NETWORK_NAME + num,
                    config.MAIN_CLUSTER_NAME)

        assert vms.createVm(True, VM_NAME, '', cluster=config.MAIN_CLUSTER_NAME)
        assert mla.addVMPermissionsToUser(True, config.USER_NAME, VM_NAME)
        assert vms.addNic(True, VM_NAME, name=NIC_NAME,
                network=config.NETWORK_NAME1, interface='virtio')

        # Actions
        loginAsUser()
        assert vms.addNic(True, VM_NAME, name=NIC_NAME2,
                network=config.NETWORK_NAME1, interface='virtio')
        assert vms.addNic(True, VM_NAME, name=NIC_NAME3,
                network=config.NETWORK_NAME1, interface='virtio')
        assert vms.updateNic(True, VM_NAME, NIC_NAME2, name='abc1')
        assert vms.updateNic(True, VM_NAME, NIC_NAME3, name='abc2')
        nets = [n.get_name() for n in networks.NET_API.get(absLink=False)]
        LOGGER.info("User can see networks: '%s'" % nets)
        assert len(nets) == 6
        assert vms.removeNic(True, VM_NAME, NIC_NAME)

    @istest
    @tcms(TCMS_PLAN_ID_POS, 231830)
    @bz(982647)
    def networkVisibilityInAPI(self):
        """ Network visibility in RestAPI """
        # Create two network in dc and assign one to cluster
        # Create vm and template and add nics with network1
        assert networks.addNetwork(True, name=config.NETWORK_NAME1,
                data_center=config.MAIN_DC_NAME)
        assert networks.addNetwork(True, name=config.NETWORK_NAME2,
                data_center=config.MAIN_DC_NAME)
        assert networks.addNetworkToCluster(True, config.NETWORK_NAME1,
                config.MAIN_CLUSTER_NAME)

        assert vms.createVm(True, VM_NAME, '', cluster=config.MAIN_CLUSTER_NAME,
                storageDomainName=config.MAIN_STORAGE_NAME, size=common.GB)
        assert vms.addNic(True, VM_NAME, name=NIC_NAME,
                network=config.NETWORK_NAME1, interface='virtio')
        assert templates.createTemplate(True, vm=VM_NAME, name=TEMPLATE_NAME,
                cluster=config.MAIN_CLUSTER_NAME)
        # a)
        # Should see only network where he has permissions
        assert mla.addPermissionsForNetwork(True, config.USER_NAME,
                config.NETWORK_NAME1, data_center=config.MAIN_DC_NAME,
                role=role.NetworkUser)
        loginAsUser()
        assert networks.findNetwork(config.NETWORK_NAME1) is not None
        self.assertRaises(EntityNotFound, networks.findNetwork,
                config.NETWORK_NAME2)
        loginAsAdmin()
        assert mla.removeUserPermissionsFromNetwork(True, config.NETWORK_NAME1,
                config.MAIN_DC_NAME, config.USER)

        # b)
        # Should see all networks in dc
        assert mla.addPermissionsForDataCenter(True, config.USER_NAME,
                config.MAIN_DC_NAME, role.NetworkUser)
        loginAsUser()
        assert networks.findNetwork(config.NETWORK_NAME1) is not None
        assert networks.findNetwork(config.NETWORK_NAME2) is not None
        loginAsAdmin()
        assert mla.removeUserPermissionsFromDatacenter(True,
                config.MAIN_DC_NAME, config.USER)

        # c)
        # Should see only assigned networks
        assert mla.addClusterPermissionsToUser(True, config.USER_NAME,
                config.MAIN_CLUSTER_NAME, role.NetworkUser)
        loginAsUser()
        assert networks.findNetwork(config.NETWORK_NAME1) is not None
        self.assertRaises(EntityNotFound, networks.findNetwork,
                config.NETWORK_NAME2)
        loginAsAdmin()
        assert mla.removeUserPermissionsFromCluster(True,
                config.MAIN_CLUSTER_NAME, config.USER)

        # d)
        # Should see only networks which are attached to nics of vm
        assert mla.addVMPermissionsToUser(True, config.USER_NAME, VM_NAME,
                role=role.NetworkUser)
        loginAsUser()
        assert networks.findNetwork(config.NETWORK_NAME1) is not None
        self.assertRaises(EntityNotFound, networks.findNetwork,
                config.NETWORK_NAME2)
        loginAsAdmin()
        assert mla.removeUserPermissionsFromVm(True, VM_NAME, config.USER)

        # e)
        # Should see only networks which are attached to nics of template
        assert mla.addPermissionsForTemplate(True, config.USER_NAME,
                TEMPLATE_NAME, role=role.NetworkUser)
        loginAsUser()
        assert networks.findNetwork(config.NETWORK_NAME1) is not None
        self.assertRaises(EntityNotFound, networks.findNetwork,
                config.NETWORK_NAME2)
        loginAsAdmin()
        assert mla.removeUserPermissionsFromTemplate(True, TEMPLATE_NAME,
                config.USER)

        # f)
        # NetworkUser on system can't view all networks
        # it can't be fixed because 878812 - can change in future
        assert users.addRoleToUser(True, config.USER_NAME, role.NetworkUser)
        loginAsUser()
        self.assertRaises(EntityNotFound, networks.findNetwork,
                config.NETWORK_NAME1)
        self.assertRaises(EntityNotFound, networks.findNetwork,
                config.NETWORK_NAME2)
        loginAsAdmin()
        assert users.removeUser(True, config.USER_NAME)
        assert users.addUser(True, user_name=config.USER_NAME,
                domain=config.USER_DOMAIN)

    @istest
    @tcms(TCMS_PLAN_ID_POS, 231832)
    def portMirroring(self):
        """ Port mirroring """
        # Setup
        assert vms.createVm(True, VM_NAME, '', cluster=config.MAIN_CLUSTER_NAME)
        assert networks.addNetwork(True, name=config.NETWORK_NAME1,
                data_center=config.MAIN_DC_NAME)
        assert networks.addNetwork(True, name=config.NETWORK_NAME2,
                data_center=config.MAIN_DC_NAME)

        assert mla.addPermissionsForNetwork(True, config.USER_NAME,
                config.NETWORK_NAME1, data_center=config.MAIN_DC_NAME)
        assert mla.addPermissionsForNetwork(True, config.USER_NAME,
                config.NETWORK_NAME2, data_center=config.MAIN_DC_NAME)

        assert mla.addVMPermissionsToUser(True, config.USER_NAME, VM_NAME)
        assert mla.addVMPermissionsToUser(True, config.USER_NAME2, VM_NAME)

        assert networks.addNetworkToCluster(True, config.NETWORK_NAME1,
                config.MAIN_CLUSTER_NAME)
        assert networks.addNetworkToCluster(True, config.NETWORK_NAME2,
                config.MAIN_CLUSTER_NAME)
        assert vms.addNic(True, VM_NAME, name=NIC_NAME,
                network=config.NETWORK_NAME2, interface='virtio')

        # Actions
        loginAsUser(filter_=False)
        assert vms.addNic(True, VM_NAME, name=NIC_NAME2,
                network=config.NETWORK_NAME1, interface='virtio',
                port_mirroring=config.NETWORK_NAME1)
        assert vms.updateNic(True, VM_NAME, NIC_NAME2,
                network=config.NETWORK_NAME1,
                port_mirroring='')
        assert vms.updateNic(True, VM_NAME, NIC_NAME,
                network=config.NETWORK_NAME2,
                port_mirroring=config.NETWORK_NAME2)

        loginAsUser(userName=config.USER_NAME2)
        assert vms.updateNic(True, VM_NAME, NIC_NAME,
                network=config.NETWORK_NAME2,
                port_mirroring='')

    @istest
    @tcms(TCMS_PLAN_ID_POS, 236367)
    def addVNICToVM(self):
        """ Add a VNIC to VM  """
        # Setup
        assert vms.createVm(True, VM_NAME, '', cluster=config.MAIN_CLUSTER_NAME)
        assert networks.addNetwork(True, name=config.NETWORK_NAME1,
                data_center=config.MAIN_DC_NAME)
        assert mla.addPermissionsForNetwork(True, config.USER_NAME,
                config.NETWORK_NAME1, data_center=config.MAIN_DC_NAME,
                role=role.NetworkUser)

        assert mla.addVMPermissionsToUser(True, config.USER_NAME, VM_NAME)
        assert mla.addVMPermissionsToUser(True, config.USER_NAME2, VM_NAME)

        assert networks.addNetworkToCluster(True, config.NETWORK_NAME1,
                config.MAIN_CLUSTER_NAME)

        # Actions
        loginAsUser()
        assert vms.addNic(True, VM_NAME, name=NIC_NAME,
                network=None, interface='virtio')
        assert vms.addNic(True, VM_NAME, name=NIC_NAME2,
                network=config.NETWORK_NAME1, interface='virtio')
        loginAsUser(userName=config.USER_NAME2)
        assert vms.addNic(True, VM_NAME, name=NIC_NAME3,
                network=None, interface='virtio')

    @istest
    @tcms(TCMS_PLAN_ID_POS, 236406)
    def updateVNICOnVM(self):
        """ Update a VNIC on VM """
        # Setup
        assert vms.createVm(True, VM_NAME, '', cluster=config.MAIN_CLUSTER_NAME)
        assert networks.addNetwork(True, name=config.NETWORK_NAME1,
                data_center=config.MAIN_DC_NAME)
        assert mla.addPermissionsForNetwork(True, config.USER_NAME,
                config.NETWORK_NAME1, data_center=config.MAIN_DC_NAME,
                role=role.NetworkUser)

        assert mla.addVMPermissionsToUser(True, config.USER_NAME, VM_NAME)
        assert mla.addVMPermissionsToUser(True, config.USER_NAME2, VM_NAME)

        assert networks.addNetworkToCluster(True, config.NETWORK_NAME1,
                config.MAIN_CLUSTER_NAME)

        assert vms.addNic(True, VM_NAME, name=NIC_NAME,
                network=config.NETWORK_NAME1, interface='virtio')

        # Actions
        loginAsUser()
        assert vms.updateNic(True, VM_NAME, NIC_NAME, network=None)
        assert vms.updateNic(True, VM_NAME, NIC_NAME,
                network=config.NETWORK_NAME1)
        loginAsUser(userName=config.USER_NAME2)
        assert vms.updateNic(True, VM_NAME, NIC_NAME, network=None)

    @istest
    @bz(952647)
    @tcms(TCMS_PLAN_ID_POS, 236408)
    def addVNICToTemplate(self):
        """ Add a VNIC to template """
        # Setup
        assert vms.createVm(True, VM_NAME, '', cluster=config.MAIN_CLUSTER_NAME,
            storageDomainName=config.MAIN_STORAGE_NAME, size=common.GB)
        assert networks.addNetwork(True, name=config.NETWORK_NAME1,
                data_center=config.MAIN_DC_NAME)
        assert mla.addPermissionsForNetwork(True, config.USER_NAME,
                config.NETWORK_NAME1, data_center=config.MAIN_DC_NAME,
                role=role.NetworkUser)

        assert mla.addVMPermissionsToUser(True, config.USER_NAME, VM_NAME)
        assert mla.addPermissionsForDataCenter(True, config.USER_NAME,
                config.MAIN_DC_NAME, role.TemplateCreator)

        assert mla.addVMPermissionsToUser(True, config.USER_NAME2, VM_NAME)
        assert mla.addPermissionsForDataCenter(True, config.USER_NAME2,
                config.MAIN_DC_NAME, role.TemplateOwner)

        assert networks.addNetworkToCluster(True, config.NETWORK_NAME1,
                config.MAIN_CLUSTER_NAME)

        # Actions
        loginAsUser()
        assert templates.createTemplate(True, vm=VM_NAME, name=TEMPLATE_NAME,
                cluster=config.MAIN_CLUSTER_NAME)
        assert templates.addTemplateNic(True, TEMPLATE_NAME, name=NIC_NAME,
                network=None)
        assert templates.addTemplateNic(True, TEMPLATE_NAME, name=NIC_NAME2,
                network=config.NETWORK_NAME1)

        loginAsUser(userName=config.USER_NAME2)
        assert templates.addTemplateNic(True, TEMPLATE_NAME, name=NIC_NAME3,
                network=None)

    @istest
    @tcms(TCMS_PLAN_ID_POS, 236409)
    def updateVNICOnTemplate(self):
        """ Update a VNIC on the template """
        # Setup
        assert networks.addNetwork(True, name=config.NETWORK_NAME1,
                data_center=config.MAIN_DC_NAME)
        assert mla.addPermissionsForNetwork(True, config.USER_NAME,
                config.NETWORK_NAME1, data_center=config.MAIN_DC_NAME,
                role=role.NetworkUser)
        assert networks.addNetworkToCluster(True, config.NETWORK_NAME1,
                config.MAIN_CLUSTER_NAME)

        assert vms.createVm(True, VM_NAME, '', cluster=config.MAIN_CLUSTER_NAME,
                storageDomainName=config.MAIN_STORAGE_NAME, size=common.GB)
        assert mla.addVMPermissionsToUser(True, config.USER_NAME, VM_NAME)
        assert mla.addVMPermissionsToUser(True, config.USER_NAME2, VM_NAME)
        assert vms.addNic(True, VM_NAME, name=NIC_NAME,
                network=config.NETWORK_NAME1, interface='virtio')

        assert templates.createTemplate(True, vm=VM_NAME, name=TEMPLATE_NAME,
                cluster=config.MAIN_CLUSTER_NAME)
        assert mla.addPermissionsForTemplate(True, config.USER_NAME,
                TEMPLATE_NAME, role=role.TemplateOwner)
        assert mla.addPermissionsForTemplate(True, config.USER_NAME2,
                TEMPLATE_NAME, role=role.TemplateOwner)

        # Actions
        loginAsUser()
        assert templates.updateTemplateNic(True, TEMPLATE_NAME, NIC_NAME,
                network=None)
        assert templates.updateTemplateNic(True, TEMPLATE_NAME, NIC_NAME,
                network=config.NETWORK_NAME1)
        assert templates.updateTemplateNic(True, TEMPLATE_NAME, NIC_NAME,
                name='_')
        assert templates.updateTemplateNic(True, TEMPLATE_NAME, '_',
                name=NIC_NAME)
        loginAsUser(userName=config.USER_NAME2)
        assert templates.updateTemplateNic(True, TEMPLATE_NAME, NIC_NAME,
                network=None)
        assert templates.updateTemplateNic(True, TEMPLATE_NAME, NIC_NAME,
                name='_')

    @istest
    @tcms(TCMS_PLAN_ID_POS, 236577)
    def removeNetworkFromDC(self):
        """ RemoveNetwokFromDC """
        msg = "NetworkAdmin role wasn't removed after network %s was removed."
        # Setup
        assert mla.addPermissionsForDataCenter(True, config.USER_NAME,
                config.MAIN_DC_NAME, role.NetworkAdmin)

        # Actions
        loginAsUser(filter_=False)
        assert networks.addNetwork(True, name=config.NETWORK_NAME1,
                data_center=config.MAIN_DC_NAME)
        assert networks.removeNetwork(True, network=config.NETWORK_NAME1,
                data_center=config.MAIN_DC_NAME)

        loginAsAdmin()
        assert mla.removeUserPermissionsFromDatacenter(True, config.MAIN_DC_NAME,
                config.USER)

        # Check if permissions was removed
        perm_persist = False
        obj = mla.userUtil.find(config.USER_NAME)
        objPermits = mla.permisUtil.getElemFromLink(obj, get_href=False)
        roleNAid = users.rlUtil.find(role.NetworkAdmin).get_id()
        for perm in objPermits:
            perm_persist = perm_persist or perm.get_role().get_id() == roleNAid
        assert not perm_persist, msg % config.NETWORK_NAME1

    @istest
    @tcms(TCMS_PLAN_ID_POS, 236664)
    def customRole(self):
        """ Custom Role """
        # Setup
        assert mla.addRole(True, name=ROLE_NAME, administrative='true',
                permits='login create_storage_pool_network')
        assert mla.addPermissionsForDataCenter(True, config.USER_NAME,
                config.MAIN_DC_NAME, ROLE_NAME)

        # Actions
        loginAsUser(filter_=False)
        assert networks.addNetwork(True, name=config.NETWORK_NAME1,
                data_center=config.MAIN_DC_NAME)
        assert networks.updateNetwork(True, config.NETWORK_NAME1,
                data_center=config.MAIN_DC_NAME, mtu=1405)
        assert networks.removeNetwork(True, network=config.NETWORK_NAME1,
                data_center=config.MAIN_DC_NAME)
