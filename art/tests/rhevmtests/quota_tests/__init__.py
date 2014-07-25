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
per whole test run, since it is very slow.
"""

import os
import logging
from art.rhevm_api.tests_lib.high_level import datacenters
from art.rhevm_api.tests_lib.low_level.storagedomains import cleanDataCenter

LOGGER = logging.getLogger(__name__)


def setup_package():
    """ Create basic resources required by all tests.

    Create the main datacenter and cluster, installs a host and starts it,
    creates and activates main storage.
    """
    if os.environ.get("JENKINS_URL"):
        import config
        LOGGER.info("Building setup...")
        datacenters.build_setup(config.PARAMETERS, config.PARAMETERS,
                                config.STORAGE_TYPE, config.TEST_NAME)


def teardown_package():
    """ Package-level teardown ran only once at end of all tests.

    Detaches main storage, removes it, deactivates host, removes host,
    removes main cluster and main dc.

    Can be skipped by setting the config variable `SKIP_MAIN_TEARDOWN`.
    """
    if os.environ.get("JENKINS_URL"):
        import config
        LOGGER.info("Teardown...")
        cleanDataCenter(True, config.DC_NAME[0], vdc=config.VDC_HOST,
                        vdc_password=config.VDC_PASSWORD)
