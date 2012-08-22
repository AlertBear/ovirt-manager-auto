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

__test__ = False

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
VM_NAME = 'user_permissions__vm'
CLUSTER_NAME = 'user_permissions__cluster'

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
    common.createVm(VM_NAME)

def tearDownModule():
    common.removeVm(VM_NAME)
    common.removeUser()


class DiskPermissionsTests(unittest.TestCase):
    __test__ = True

    @istest
    @logger
    def testTest(self):
        """ testTest """
        pass
