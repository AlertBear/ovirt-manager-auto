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


def teardown_module():
    """
        Removes created datacenter, storages etc.
    """


class TestCaseCreateFakeHosts(TestCase):
    """
        Create number of VMs defined in configuration
    """
    __test__ = True

    def setUp(self):
        self.vm_cnt = int(config.VM_CNT)
        self.vm_names = ['%s_fake_%s' % (config.VM_BASE_NAME, ind)
                         for ind in range(self.vm_cnt)]

    @istest
    def test_create_fake_hosts(self):
        """
            Create VMs and fake hosts
        """
        monitor = resource_monitor.ResourcesTemplate()
        monitor.create_report('system idle')

        status = True
        bulk_cnt = int(config.BULK_VM_CNT)
        start = 0
        while self.vm_cnt:
            cnt = bulk_cnt if self.vm_cnt > bulk_cnt else self.vm_cnt
            LOGGER.info("Create %s VMs as a source for fake hosts", cnt)
            status = common.create_vms(self.vm_names[start:start + cnt]) \
                and status
            monitor.create_report('%s running VMs' % cnt)
            LOGGER.info("Create %s fake hosts", cnt)
            status = common.create_fake_hosts(
                self.vm_names[start:start + cnt]) and status
            monitor.create_report('%s running fake hosts' % cnt)
            start += bulk_cnt
            self.vm_cnt -= cnt

        assert(status)


    def tearDown(self):
        """
            Remove created fake hosts and VMs
        """

#        fake_host_names = ['host_%s' % n for n in self.vm_names]
#        common.remove_fake_hosts(fake_host_names)
#
#        vm_names = ",".join(self.vm_names)
#        LOGGER.info("Removing created VMs")
#        vms.removeVms(True, vm_names, stop='true')

