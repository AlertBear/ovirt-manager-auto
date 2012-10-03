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

""" Global teardown that removes master host, storage, cluster and datacenter

Can be turned off using the SKIP_MAIN_TEARDOWN option in config. Run only once
per
whole test run, since it is very slow.
"""
import states

import logging
import logging.config
import ovirtsdk.api
from ovirtsdk.xml import params

LOGGER  = logging.getLogger(__name__)

def tearDownPackage():
    """ Package-level teardown ran only once at end of all tests.

    Detaches main storage, removes it, deactivates host, removes host,
    removes main cluster and main dc.

    Can be skipped by setting the config variable `SKIP_MAIN_TEARDOWN`.
    """
    import config
    import common
    API     = common.API
    if config.SKIP_MAIN_TEARDOWN:
        LOGGER.info("Skipping global teardown")
        return

    # TODO only check for objects associated with the host/cluster/dc that are
    # going to be removed, ignore others
    assert len(API.templates.list()) == 1, \
        "Templates were not correctly removed"
    assert len(API.storagedomains.list()) <= 1, \
        "Storages were not correctly removed"
    assert len(API.vms.list()) == 0, \
        "VMs were not correctly removed"

    try:
        ############################# STORAGE #################################
        if API.storagedomains.get(config.MAIN_STORAGE_NAME) is not None:
            common.removeMasterStorage(storageName=config.MAIN_STORAGE_NAME,
                                       datacenter=config.MAIN_DC_NAME,
                                       host=config.MAIN_HOST_NAME)

        ############################# HOST ####################################
        host = API.hosts.get(config.MAIN_HOST_NAME)
        if host is not None:
            LOGGER.info("Deactivating host")
            host.deactivate()
            common.waitForState(host, states.host.maintenance)

            LOGGER.info("Deleting host")
            host.delete()
            assert common.updateObject(host) is None, "Failed to remove host"

        ############################# CLUSTER #################################
        common.removeCluster(config.MAIN_CLUSTER_NAME)
    except Exception as err:
        LOGGER.warning("while cleaing => %s" % str(err))

def setUpPackage():
    """ Create basic resources required by all tests.

    Create the main datacenter and cluster, installs a host and starts it,
    creates and activetes main storage.
    """
    import config
    import common
    API     = common.API
    if config.SKIP_MAIN_SETUP:
        LOGGER.info("Skipping global setup")
        checkSetup()
        return

    try:
        common.createDataCenter(config.MAIN_DC_NAME)

        common.createCluster(config.MAIN_CLUSTER_NAME, config.MAIN_DC_NAME)
        cluster = API.clusters.get(config.MAIN_CLUSTER_NAME)

        ############################# HOST ####################################
        common.createHost(cluster.get_name(), hostName=config.MAIN_HOST_NAME,
                    hostAddress=config.HOST_ADDRESS,
                    hostPassword=config.HOST_ROOT_PASSWORD)

        ############################# STORAGE #################################
        if config.MAIN_STORAGE_TYPE.lower() == 'iscsi':
            common.createIscsiStorage(config.MAIN_STORAGE_NAME)
        else:
            common.createNfsStorage(config.MAIN_STORAGE_NAME)
        common.attachActivateStorage(config.MAIN_STORAGE_NAME, isMaster=True)

        checkSetup()

    # teardown even if the setup partially fails
    except Exception as err:
        LOGGER.error("while seting up => %s" % str(err))
        tearDownPackage()
        raise

def checkSetup():
    """ Helper function to check if the main setup was created correctly """

    import config
    import common
    API     = common.API
    assert API.datacenters.get(config.MAIN_DC_NAME) is not None, \
        "Datacenter " + config.MAIN_DC_NAME + " does not exist"
    assert API.clusters.get(config.MAIN_CLUSTER_NAME) is not None, \
        "Cluster " + config.MAIN_CLUSTER_NAME + " does not exist"
    assert API.hosts.get(config.MAIN_HOST_NAME) is not None, \
        "Host " + config.MAIN_HOST_NAME + " does not exist or is not up"

