"""
Test exposing BZ 962549

TCMS plan: https://tcms.engineering.redhat.com/plan/9583
"""

import logging
from nose.tools import istest
from art.unittest_lib import BaseTestCase as TestCase

from art.rhevm_api.utils import test_utils

from art.rhevm_api.tests_lib.high_level import datacenters
from art.rhevm_api.tests_lib.low_level import vms
from art.rhevm_api.tests_lib.low_level import hosts
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
        storage_type=config.STORAGE_TYPE, basename=config.BASENAME)


def teardown_module():
    """ removes created datacenter, storages etc.
    """
    storagedomains.cleanDataCenter(True, config.DATA_CENTER_NAME)


class TestCase280628(TestCase):
    """ Test exposing https://bugzilla.redhat.com/show_bug.cgi?id=962549

    Test scenario:
    * create a VM with RHEL, run it on SPM
    * create a snapshot
    * run the VM on an HSM
    * stop the VM
    * remove the snapshot
    * run the VM again on the same HSM
    """
    __test__ = True
    tcms_plan_id = '9583'
    tcms_test_case = '280628'
    vm_name = "vm_%s" % tcms_test_case
    snap_name = "snap_%s" % tcms_test_case

    @istest
    @tcms(tcms_plan_id, tcms_test_case)
    def merge_snapshots_on_hsm_test(self):
        """
        checks that a VM with a snapshot, which where created when the VM was
        run on SPM and removed when the VM was moved to an HSM, can be booted
        """
        LOGGER.info("Create VM")
        storage_domain_name = STORAGE_DOMAIN_API.get(absLink=False)[0].name
        spm_host = hosts.getSPMHost(config.HOSTS)
        assert vms.createVm(
            True, self.vm_name, self.vm_name, config.CLUSTER_NAME,
            installation=True, nic=config.HOST_NICS[0],
            storageDomainName=storage_domain_name, size=config.DISK_SIZE,
            diskType=config.DISK_TYPE_SYSTEM, memory=GB,
            cpu_socket=config.CPU_SOCKET, cpu_cores=config.CPU_CORES,
            nicType=config.NIC_TYPE_VIRTIO, display_type=config.DISPLAY_TYPE,
            os_type=config.OS_TYPE, user=config.VM_LINUX_USER,
            password=config.VM_LINUX_PASSWORD, type=config.VM_TYPE_DESKTOP,
            slim=True, cobblerAddress=config.COBBLER_ADDRESS,
            cobblerUser=config.COBBLER_USER, placement_host=spm_host,
            cobblerPasswd=config.COBBLER_PASSWORD, volumeType=False,
            volumeFormat=ENUMS['format_raw'],
            image=config.COBBLER_PROFILE, network=config.MGMT_BRIDGE,
            useAgent=config.USE_AGENT)
        LOGGER.info("Stopping VM")
        assert vms.stopVm(True, self.vm_name)
        LOGGER.info("Adding snapshot")
        assert vms.addSnapshot(True, self.vm_name, self.snap_name)
        hsm_host = hosts.getAnyNonSPMHost(",".join(config.HOSTS))[1]['hsmHost']
        assert hsm_host
        assert vms.updateVm(True, self.vm_name, placement_host=hsm_host)
        LOGGER.info("Starting VM on HSM")
        assert vms.startVm(True, self.vm_name, wait_for_ip=True)
        LOGGER.info("Stopping VM")
        assert vms.stopVm(True, self.vm_name)
        LOGGER.info("Removing snapshot")
        assert vms.removeSnapshot(
            True, self.vm_name, self.snap_name, timeout=30 * 60)
        LOGGER.info("Starting again")
        assert vms.startVm(True, self.vm_name, wait_for_ip=True)

    @classmethod
    def teardown_class(cls):
        vms.removeVm(True, cls.vm_name, stopVM='true')
