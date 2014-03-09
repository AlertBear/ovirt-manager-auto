"""
Test exposing BZ 960430

TCMS plan: https://tcms.engineering.redhat.com/plan/9583
"""

import logging
from nose.tools import istest
from art.unittest_lib import BaseTestCase as TestCase

from art.rhevm_api.tests_lib.high_level import datacenters
from art.rhevm_api.tests_lib.low_level import storagedomains
from art.rhevm_api.tests_lib.low_level import disks
from art.test_handler.tools import tcms

import config

LOGGER = logging.getLogger(__name__)
GB = 1024 * 1024 * 1024

ENUMS = config.ENUMS


def setup_module():
    """ creates datacenter, adds hosts, clusters, storages according to
    the config file
    """
    datacenters.build_setup(
        config=config.PARAMETERS, storage=config.PARAMETERS,
        storage_type=config.STORAGE_TYPE, basename=config.BASENAME)


def teardown_module():
    """ removes created datacenter, storages etc.
    """
    storagedomains.cleanDataCenter(True, config.DATA_CENTER_NAME)


class TestCase284324(TestCase):
    """ Test exposing https://bugzilla.redhat.com/show_bug.cgi?id=960430
    Tries to create a disk via REST API without specifying 'sparse' tag.

    https://tcms.engineering.redhat.com/case/284324/?from_plan=9583
    """
    __test__ = True
    tcms_plan_id = '9583'
    tcms_test_case = '284324'

    @istest
    @tcms(tcms_plan_id, tcms_test_case)
    def create_raw_disk_without_sparse_tag_test(self):
        """
        Tries to create a raw disk via REST API without specifying 'sparse'
        flag. Such call should fail.
        """
        master_domain = storagedomains.findMasterStorageDomain(
            True, config.DATA_CENTER_NAME)[1]['masterDomain']
        disk_name = "disk_%s" % self.tcms_test_case

        assert disks.addDisk(
            False, alias=disk_name, shareable=False, bootable=False,
            size=1 * GB, storagedomain=master_domain, sparse=None,
            format=ENUMS['format_raw'], interface=ENUMS['interface_ide'])
