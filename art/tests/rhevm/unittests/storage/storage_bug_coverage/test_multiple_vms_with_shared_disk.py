"""
Test exposing BZ 834893 - running several VMs with the same shared disk on one
host should not fail

TCMS plan: https://tcms.engineering.redhat.com/plan/9583
"""

import logging
from nose.tools import istest
from unittest import TestCase

from art.rhevm_api.utils import test_utils

from art.rhevm_api.tests_lib.high_level import datacenters
from art.rhevm_api.tests_lib.low_level import vms
from art.rhevm_api.tests_lib.low_level import disks
from art.rhevm_api.tests_lib.low_level import storagedomains
from art.test_handler.tools import tcms

import config

LOGGER = logging.getLogger(__name__)
GB = 1024 * 1024 * 1024

ENUMS = config.ENUMS
STORAGE_DOMAIN_API = test_utils.get_api('storage_domain', 'storagedomains')


def setup_module():
    """ creates datacenter, adds hosts, clusters, storages according to
    the config file
    """
    datacenters.build_setup(
        config=config.PARAMETERS, storage=config.PARAMETERS,
        storage_type=config.DATA_CENTER_TYPE, basename=config.BASENAME)


def teardown_module():
    """ removes created datacenter, storages etc.
    """
    storagedomains.cleanDataCenter(True, config.DATA_CENTER_NAME)


class TestCase275816(TestCase):
    """
    test exposing https://bugzilla.redhat.com/show_bug.cgi?id=834893
    scenario:
    * creates 4 VMs with nics but without disks
    * creates a shared disks
    * attaches the disk to the vms one at a time
    * runs all the vms on one host

    https://tcms.engineering.redhat.com/case/275816/?from_plan=9583
    """
    __test__ = True
    tcms_plan_id = '9583'
    tcms_test_case = '275816'
    vm_names = []
    disk_name = None
    disk_size = 1 * GB

    @istest
    @tcms(tcms_plan_id, tcms_test_case)
    def several_vms_with_same_shared_disk_on_one_host_test(self):
        """ tests if running a few VMs with the same shared disk on the same
            host works correctly
        """
        for i in range(4):
            vm_name = "vm_%s_%s" % (self.tcms_test_case, i)
            nic = "nic_%s" % i
            vms.createVm(
                True, vm_name, vm_name, config.CLUSTER_NAME, nic=nic,
                placement_host=config.HOSTS[0])
            self.vm_names.append(vm_name)
        storage_domain_name = STORAGE_DOMAIN_API.get(absLink=False)[0].name
        self.disk_name = 'disk_%s' % self.tcms_test_case
        LOGGER.info("Creating disk")
        assert disks.addDisk(
            True, alias=self.disk_name, shareable=True, bootable=False,
            size=self.disk_size, storagedomain=storage_domain_name,
            format=ENUMS['format_raw'], interface=ENUMS['interface_ide'],
            sparse=False)
        assert disks.waitForDisksState(self.disk_name)
        LOGGER.info("Disk created")

        for vm in self.vm_names:
            assert disks.attachDisk(True, self.disk_name, vm, True)

        assert vms.startVms(",".join(self.vm_names))

    @classmethod
    def teardown_class(cls):
        for vm in cls.vm_names:
            vms.removeVm(True, vm, stopVM='true')
        if cls.disk_name is not None:
            disks.deleteDisk(True, cls.disk_name)
