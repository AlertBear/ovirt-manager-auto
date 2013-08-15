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

import logging

from user_roles_tests import config
from user_roles_tests.roles import role
from nose.tools import istest
from unittest import TestCase

from art.rhevm_api.tests_lib.low_level import mla, networks, users, vms
from art.rhevm_api.tests_lib.low_level import templates
from art.test_handler.tools import tcms

LOGGER = logging.getLogger(__name__)
VM_NAME = 'networking_vm'
TEMPLATE_NAME = 'networking_template'
NIC_NAME = 'nic1'
NIC_NAME2 = 'nic2'
NIC_NAME3 = 'nic3'
TCMS_PLAN_ID_NEG = 10640


def loginAsUser(userName=config.USER_NAME, filter_=True):
    users.loginAsUser(
        userName, config.USER_DOMAIN, config.USER_PASSWORD, filter_)


def loginAsAdmin():
    users.loginAsUser(config.OVIRT_USERNAME, config.OVIRT_DOMAIN,
                      config.OVIRT_PASSWORD, filter=False)


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
    """ Run method and ignore all exceptions. """
    try:
        method(**kwargs)
    except:
        pass


class NetworkingNegative(TestCase):
    """ https://tcms.engineering.redhat.com/plan/8052 """
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
            ignoreAllExceptions(networks.removeNetwork,
                                positive=True,
                                network=network,
                                data_center=config.MAIN_DC_NAME)

        mla.removeUsersPermissionsFromDatacenter(
            True, config.MAIN_DC_NAME,
            [config.USER, config.USER2, config.USER3])
        mla.removeUsersPermissionsFromCluster(
            True, config.MAIN_CLUSTER_NAME,
            [config.USER, config.USER2, config.USER3])

    @istest
    @tcms(TCMS_PLAN_ID_NEG, 231821)
    def createDeleteNetworkinDC(self):
        """ Create/Delete network in DC """
        # Setup
        msg = "User %s with %s can't add/remove network."
        assert networks.addNetwork(True, name=config.NETWORK_NAME1,
                                   data_center=config.MAIN_DC_NAME)
        assert mla.addClusterPermissionsToUser(
            True, config.USER_NAME, cluster=config.MAIN_CLUSTER_NAME)

        # Actions
        loginAsUser(filter_=False)
        assert networks.addNetwork(False, name=config.NETWORK_NAME2,
                                   data_center=config.MAIN_DC_NAME)
        assert networks.removeNetwork(False, network=config.NETWORK_NAME1,
                                      data_center=config.MAIN_DC_NAME)
        LOGGER.info(msg % (config.USER, role.ClusterAdmin))

    @istest
    @tcms(TCMS_PLAN_ID_NEG, 231916)
    def editNetworkInDC(self):
        """  Edit network in DC """
        msg = "User %s with %s can't update network."
        # Setup
        assert networks.addNetwork(True, name=config.NETWORK_NAME1,
                                   data_center=config.MAIN_DC_NAME)
        assert mla.addClusterPermissionsToUser(
            True, config.USER_NAME, cluster=config.MAIN_CLUSTER_NAME)

        # Actions
        loginAsUser(filter_=False)
        assert networks.updateNetwork(
            False, network=config.NETWORK_NAME1,
            data_center=config.MAIN_DC_NAME, mtu=1502)
        assert networks.updateNetwork(
            False, network=config.NETWORK_NAME1,
            data_center=config.MAIN_DC_NAME, vlan_id=3)
        assert networks.updateNetwork(
            False, network=config.NETWORK_NAME1,
            data_center=config.MAIN_DC_NAME, usages='')
        assert networks.updateNetwork(
            False, network=config.NETWORK_NAME1,
            data_center=config.MAIN_DC_NAME, usages='VM')
        LOGGER.info(msg % (config.USER, role.ClusterAdmin))

    # NEED UPDATE
    #@istest
    @tcms(TCMS_PLAN_ID_NEG, 231917)
    def attachingDetachingNetworkToFromCluster(self):
        """ Attaching/Detaching network to/from Cluster """
        # Setup
        assert networks.addNetwork(True, name=config.NETWORK_NAME1,
                                   data_center=config.MAIN_DC_NAME)
        assert networks.addNetwork(True, name=config.NETWORK_NAME2,
                                   data_center=config.MAIN_DC_NAME)

        for net in [config.NETWORK_NAME1, config.NETWORK_NAME2]:
            assert mla.addPermissionsForDataCenter(
                True, config.USER_NAME,
                config.MAIN_DC_NAME, role=role.VnicProfileUser)
            assert mla.addPermissionsForDataCenter(
                True, config.USER_NAME,
                config.MAIN_DC_NAME, role=role.ClusterAdmin)
            assert mla.addPermissionsForDataCenter(
                True, config.USER_NAME2,
                config.MAIN_DC_NAME, role=role.VnicProfileUser)
            assert mla.addPermissionsForDataCenter(
                True, config.USER_NAME2,
                config.MAIN_DC_NAME, role=role.HostAdmin)

        assert networks.addNetworkToCluster(True, config.NETWORK_NAME1,
                                            config.MAIN_CLUSTER_NAME)

        # Actions
        for user in [config.USER_NAME, config.USER_NAME2]:
            loginAsUser(userName=user, filter_=False)
            assert networks.removeNetworkFromCluster(
                False, config.NETWORK_NAME1, config.MAIN_CLUSTER_NAME)
            assert networks.addNetworkToCluster(
                False, config.NETWORK_NAME2, config.MAIN_CLUSTER_NAME)

    # NEED UPDATE
    #@istest
    @tcms(TCMS_PLAN_ID_NEG, 231918)
    def networkRequiredToNonRequiredAndViceVersa(self):
        """ Network required to non-required and vice versa """
        # Setup
        assert mla.addPermissionsForDataCenter(
            True, config.USER_NAME,
            config.MAIN_DC_NAME, role=role.VnicProfileUser)
        assert mla.addPermissionsForDataCenter(
            True, config.USER_NAME, config.MAIN_DC_NAME, role=role.HostAdmin)
        assert networks.addNetwork(
            True, name=config.NETWORK_NAME1, data_center=config.MAIN_DC_NAME)
        assert networks.addNetwork(
            True, name=config.NETWORK_NAME2, data_center=config.MAIN_DC_NAME)

        assert networks.addNetworkToCluster(
            True, config.NETWORK_NAME1, config.MAIN_CLUSTER_NAME)
        assert networks.addNetworkToCluster(
            True, config.NETWORK_NAME2, config.MAIN_CLUSTER_NAME)

        assert networks.updateClusterNetwork(
            True, config.MAIN_CLUSTER_NAME,
            config.NETWORK_NAME1, required=True)
        assert networks.updateClusterNetwork(
            True, config.MAIN_CLUSTER_NAME,
            config.NETWORK_NAME2, required=False)

        # Actions
        loginAsUser(filter_=False)
        assert networks.updateClusterNetwork(
            False, config.MAIN_CLUSTER_NAME,
            config.NETWORK_NAME1, required=False)
        assert networks.updateClusterNetwork(
            False, config.MAIN_CLUSTER_NAME,
            config.NETWORK_NAME1, required=True)

    @istest
    @tcms(TCMS_PLAN_ID_NEG, 231919)
    def attachingVNICToVM(self):
        """ Attaching VNIC to VM """
        # Setup
        assert vms.createVm(True, VM_NAME, '',
                            cluster=config.MAIN_CLUSTER_NAME)
        assert mla.addPermissionsForDataCenter(
            True, config.USER_NAME,
            config.MAIN_DC_NAME, role=role.HostAdmin)
        assert mla.addVMPermissionsToUser(
            True, config.USER_NAME, VM_NAME, role=role.UserRole)
        assert vms.addNic(True, VM_NAME, name=NIC_NAME,
                          network=config.NETWORK_NAME, interface='virtio')

        # Actions
        loginAsUser(filter_=False)
        assert vms.addNic(False, VM_NAME, name=NIC_NAME2,
                          network=config.NETWORK_NAME, interface='virtio')
        assert vms.removeNic(False, VM_NAME, NIC_NAME)
        assert vms.updateNic(False, VM_NAME, NIC_NAME, name='newName')


    @istest
    @tcms(TCMS_PLAN_ID_NEG, 234215)
    def attachVNICToTemplate(self):
        """ Attach VNIC to Template """
        # Setup
        assert mla.addPermissionsForDataCenter(
            True, config.USER_NAME, config.MAIN_DC_NAME, role=role.HostAdmin)
        assert vms.createVm(True, VM_NAME, '',
                            cluster=config.MAIN_CLUSTER_NAME)
        assert templates.createTemplate(
            True, vm=VM_NAME, name=TEMPLATE_NAME,
            cluster=config.MAIN_CLUSTER_NAME)
        assert templates.addTemplateNic(True, TEMPLATE_NAME, name=NIC_NAME,
                                        network=config.NETWORK_NAME)

        # Actions
        loginAsUser(filter_=False)
        assert templates.addTemplateNic(False, TEMPLATE_NAME, name=NIC_NAME2,
                                        network=config.NETWORK_NAME)
        assert templates.removeTemplateNic(False, TEMPLATE_NAME, NIC_NAME)
        assert templates.updateTemplateNic(False, TEMPLATE_NAME, NIC_NAME,
                                           name='newName')

    @istest
    @tcms(TCMS_PLAN_ID_NEG, 236686)
    def attachNetworkToVM(self):
        """ Attach a network to VM """
        # Setup
        assert vms.createVm(True, VM_NAME, '',
                            cluster=config.MAIN_CLUSTER_NAME)
        assert networks.addNetwork(True, name=config.NETWORK_NAME1,
                                   data_center=config.MAIN_DC_NAME)
        assert networks.addNetwork(True, name=config.NETWORK_NAME2,
                                   data_center=config.MAIN_DC_NAME)
        assert mla.addVMPermissionsToUser(True, config.USER_NAME, VM_NAME)
        assert networks.addNetworkToCluster(True, config.NETWORK_NAME1,
                                            config.MAIN_CLUSTER_NAME)
        assert networks.addNetworkToCluster(True, config.NETWORK_NAME2,
                                            config.MAIN_CLUSTER_NAME)
        assert vms.addNic(True, VM_NAME, name=NIC_NAME,
                          network=config.NETWORK_NAME2, interface='virtio')

        # Actions
        loginAsUser()
        assert vms.addNic(False, VM_NAME, name=NIC_NAME3,
                          network=config.NETWORK_NAME1, interface='virtio')
        assert vms.updateNic(False, VM_NAME, NIC_NAME,
                             network=config.NETWORK_NAME1)


    # NEED UPDATE
    #@istest
    @tcms(TCMS_PLAN_ID_NEG, 236736)
    def visibleNetworksAndManipulation(self):
        """ Visible networks and manipulation """
        # Setup
        assert vms.createVm(True, VM_NAME, '',
                            cluster=config.MAIN_CLUSTER_NAME)
        assert mla.addVMPermissionsToUser(True, config.USER_NAME, VM_NAME)
        assert networks.addNetwork(True, name=config.NETWORK_NAME1,
                                   data_center=config.MAIN_DC_NAME)
        assert networks.addNetwork(True, name=config.NETWORK_NAME2,
                                   data_center=config.MAIN_DC_NAME)
        assert networks.addNetwork(True, name=config.NETWORK_NAME3,
                                   data_center=config.MAIN_DC_NAME)
        assert networks.addNetwork(True, name=config.NETWORK_NAME4,
                                   data_center=config.MAIN_DC_NAME)

        assert networks.addNetworkToCluster(True, config.NETWORK_NAME1,
                                            config.MAIN_CLUSTER_NAME)
        assert networks.addNetworkToCluster(True, config.NETWORK_NAME2,
                                            config.MAIN_CLUSTER_NAME)

        assert vms.addNic(True, VM_NAME, name=NIC_NAME,
                          network=config.NETWORK_NAME1, interface='virtio')
        assert vms.addNic(True, VM_NAME, name=NIC_NAME2,
                          network=config.NETWORK_NAME2, interface='virtio')

        # Actions
        loginAsUser()
        assert vms.addNic(False, VM_NAME, name=NIC_NAME3,
                          network=config.NETWORK_NAME1, interface='virtio')
        assert vms.updateNic(False, VM_NAME, NIC_NAME2,
                             network=config.NETWORK_NAME1)
        assert vms.removeNic(True, VM_NAME, NIC_NAME)
        assert vms.addNic(False, VM_NAME, name=NIC_NAME,
                          network=config.NETWORK_NAME1, interface='virtio')
        nets = [n.get_name() for n in networks.NET_API.get(absLink=False)]
        LOGGER.info("User can see networks: '%s'" % nets)
        # User can see network2 and default rhevm network, because has
        # Everyone VnicProfileUser permissons, None network is not count
        # (is not shown in /api/networks) + Default DC
        assert len(nets) == 3
        assert vms.updateNic(True, VM_NAME, NIC_NAME2, network=None)
        assert vms.updateNic(False, VM_NAME, NIC_NAME2,
                             network=config.NETWORK_NAME2)
