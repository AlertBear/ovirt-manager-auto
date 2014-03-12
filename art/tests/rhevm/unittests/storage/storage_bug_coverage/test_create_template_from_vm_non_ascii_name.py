#!/usr/bin/python
# -*- coding: utf8 -*-
"""
Test exposing BZ 1002249, checks that creating a template
from a vm with non-ascii character in its name is working
"""
import logging
from nose.tools import istest
from art.unittest_lib import BaseTestCase as TestCase

from art.rhevm_api.utils import test_utils

from art.rhevm_api.tests_lib.high_level import datacenters
from art.rhevm_api.tests_lib.low_level import vms as ll_vms
from art.rhevm_api.tests_lib.low_level import templates
from art.rhevm_api.tests_lib.low_level import storagedomains
from art.rhevm_api.tests_lib.low_level import disks
from art.test_handler.tools import tcms, bz
import art.test_handler.exceptions as errors

import config

LOGGER = logging.getLogger(__name__)

ENUMS = config.ENUMS
STORAGE_DOMAIN_API = test_utils.get_api('storage_domain', 'storagedomains')

def setup_module():
    """ creates datacenter, adds hosts, clusters, storages according to
    the config file
    """
    datacenters.build_setup(
        config=config.PARAMETERS, storage=config.PARAMETERS,
        storage_type=config.DATA_CENTER_TYPE, basename=config.BASENAME)

    # Add a VM
    if not ll_vms.addVm(True, name=config.VM_BASE_NAME,
                        storagedomain=config.DOMAIN_NAME_1,
                        cluster=config.CLUSTER_NAME):
        raise errors.VMException("Cannot create vm %s" % config.VM_BASE_NAME)

    # Add a disk to the VM
    if not ll_vms.addDisk(True, config.VM_BASE_NAME, config.DISK_SIZE,
                          storagedomain=config.DOMAIN_NAME_1):
        raise errors.DiskException("Cannot create disk for vm %s" %
                                   config.VM_BASE_NAME)


def teardown_module():
    """ removes created datacenter, storages etc.
    """
    storagedomains.cleanDataCenter(True, config.DATA_CENTER_NAME,
                                   vdc=config.VDC,
                                   vdc_password=config.VDC_PASSWORD)


class TestCase305452(TestCase):
    """
    test exposing https://bugzilla.redhat.com/show_bug.cgi?id=1002249
    scenario:
    * create a VM with a non-ascii char in the disk's name
    * Create a template from the vm

    https://tcms.engineering.redhat.com/case/305452/?from_plan=6468
    """
    __test__ = True
    tcms_plan_id = '6468'
    tcms_test_case = '305452'

    @bz(1002249)
    @tcms(tcms_plan_id, tcms_test_case)
    def test_create_template_from_vm(self):
        """ creates template from vm
        """
        LOGGER.info("Adding a non-ascii character to the disk name")
        disk_name = u"DiskNonAsciié"
        disk_params = {"alias": "%s_Disk1" % config.VM_BASE_NAME,
                       "name": disk_name}
        self.assertTrue(disks.updateDisk(True, **disk_params))

        template_name = '%s_%s_non_ascii_template_' % (
            config.VM_BASE_NAME, config.DATA_CENTER_TYPE)
        template_kwargs = {"vm": vm_name,
                           "name": template_name}
        LOGGER.info("Creating template")
        self.assertTrue(templates.createTemplate(True, **template_kwargs))


    @classmethod
    def teardown_class(cls):
        """
        Wait for un-finished tasks
        """
        test_utils.wait_for_tasks(config.VDC, config.VDC_PASSWORD,
                                  config.DATA_CENTER_NAME)
