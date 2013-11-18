"""
Scalability VM test
"""

import logging
from nose.tools import istest
from unittest import TestCase

from art.rhevm_api.tests_lib.low_level import vms

import config
import common
import resource_monitor

LOGGER = logging.getLogger(__name__)


def setup_module():
    """
        Creates datacenter, adds hosts, clusters, storages according to
        the config file
    """
    pass


def teardown_module():
    """
        Removes created datacenter, storages etc.
    """
    pass


class TestCaseCreateVms(TestCase):
    """
        Create number of VMs defined in configuration
    """
    __test__ = True

    def setUp(self):
        self.vm_names = list()

    @istest
    def test_create_vms(self):
        """
            Create VMs and fake hosts
        """
        monitor = resource_monitor.ResourcesTemplate()
        monitor.create_report('system idle')
        vm_cnt = int(config.VM_CNT)
        bulk_cnt = int(config.BULK_VM_CNT)
        self.vm_names = ['%s_%s' % (config.VM_BASE_NAME, ind)
                         for ind in range(vm_cnt)]
        status = True
        template = 'Blank'
        start = 0
        while vm_cnt:
            cnt = bulk_cnt if vm_cnt > bulk_cnt else vm_cnt
            LOGGER.info("Create VMs: %s", self.vm_names[start:start + cnt])
            status = common.create_vms(
                self.vm_names[start:start + cnt], template) and status
            monitor.create_report('%s running VMs' % (start + cnt))
            start += bulk_cnt
            vm_cnt -= cnt

        LOGGER.info("Stop dwh service")
        common.toggle_dwh_service('stop')
        monitor.create_report('%s running VMs, dwh stopped' % config.VM_CNT)
        LOGGER.info("Start dwh service")
        common.toggle_dwh_service('start')
        monitor.create_report('%s running VMs, dwh started' % config.VM_CNT)

        vms_start_stop = ",".join(self.vm_names[0:bulk_cnt])
        LOGGER.info("Stop %s VMs", bulk_cnt)
        status = vms.stopVms(vms_start_stop) and status
        LOGGER.info("Start %s VMs", bulk_cnt)
        status = vms.startVms(vms_start_stop) and status
        monitor.create_report('%s running VMs, after start-stop %s VMs' % \
            (config.VM_CNT, bulk_cnt))

        assert(status)

    def tearDown(self):
        """
            Remove created fake hosts and VMs
        """
        pass
#        vm_names = ",".join(self.vm_names)
#        LOGGER.info("Removing created VMs")
#        vms.removeVms(True, vm_names, stop='true')
