#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (c) 2013 Red Hat, Inc.
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

import logging
from art.rhevm_api.tests_lib.low_level import vms
from art.rhevm_api.tests_lib.low_level import datacenters
from art.rhevm_api.tests_lib.low_level import clusters
from art.rhevm_api.tests_lib.low_level import hosts
from art.rhevm_api.tests_lib.low_level import storagedomains
from art.rhevm_api.tests_lib.low_level import templates
from art.rhevm_api.tests_lib.high_level import storagedomains as h_storagedomains

LOGGER  = logging.getLogger(__name__)

def tearDownPackage():
    """ Package-level teardown ran only once at end of all tests.

    Detaches main storage, removes it, deactivates host, removes host,
    removes main cluster and main dc.

    Can be skipped by setting the config variable `SKIP_MAIN_TEARDOWN`.
    """
    import config
    if config.SKIP_MAIN_TEARDOWN:
        LOGGER.info("Skipping global teardown")
        return

    assert templates.searchForTemplate(True, 'name', '*', 'name', expected_count=1)
    assert storagedomains.searchForStorageDomain(True, 'name', '*', 'name', expected_count=1)
    assert vms.searchForVm(True, 'name', '*', 'name', expected_count=0)

    assert storagedomains.deactivateStorageDomain(True, config.MAIN_DC_NAME,
            config.MAIN_STORAGE_NAME)
    assert hosts.deactivateHost(True, config.MAIN_HOST_NAME)
    assert hosts.removeHost(True, config.MAIN_HOST_NAME)
    assert clusters.removeCluster(True, config.MAIN_CLUSTER_NAME)
    #assert datacenters.removeDataCenter(True, config.MAIN_DC_NAME, force=True) # TODO implement force

def setUpPackage():
    """ Create basic resources required by all tests.

    Create the main datacenter and cluster, installs a host and starts it,
    creates and activetes main storage.
    """
    import config
    if config.SKIP_MAIN_SETUP:
        LOGGER.info("Skipping global setup")
        return

    assert datacenters.addDataCenter(True, name=config.MAIN_DC_NAME,
            storage_type=config.MAIN_STORAGE_TYPE, version=config.OVIRT_VERSION)
    assert clusters.addCluster(True, name=config.MAIN_CLUSTER_NAME, cpu=config.HOST_CPU_TYPE,
            data_center=config.MAIN_DC_NAME, version=config.OVIRT_VERSION)
    assert hosts.addHost(True, config.MAIN_HOST_NAME, root_password=config.HOST_ROOT_PASSWORD,
            address=config.HOST_ADDRESS, cluster=config.MAIN_CLUSTER_NAME)
    assert h_storagedomains.addNFSDomain(config.MAIN_HOST_NAME, config.MAIN_STORAGE_NAME,
            config.MAIN_DC_NAME, config.NFS_STORAGE_ADDRESS, config.NFS_STORAGE_PATH)
