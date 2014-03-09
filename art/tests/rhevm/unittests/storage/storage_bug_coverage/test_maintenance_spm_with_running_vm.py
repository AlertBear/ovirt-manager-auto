"""
Test exposing BZ 986961

"""
import logging
from art.unittest_lib import BaseTestCase as TestCase

from art.rhevm_api.tests_lib.high_level import datacenters
from art.rhevm_api.tests_lib.low_level import datacenters as dc_ll
from art.rhevm_api.tests_lib.low_level import vms
from art.rhevm_api.tests_lib.low_level import hosts
from art.rhevm_api.tests_lib.low_level import storagedomains
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
    storagedomains.cleanDataCenter(True, config.DATA_CENTER_NAME,
                                   vdc=config.VDC,
                                   vdc_password=config.VDC_PASSWORD)


class TestCase315489(TestCase):
    """
    test exposing https://bugzilla.redhat.com/show_bug.cgi?id=986961
    scenario:
        * on 2 host cluster with connected pool and running VM on SPM
        * maintenance SPM

    https://tcms.engineering.redhat.com/case/315489/?from_plan=2337
    """
    __test__ = True
    tcms_plan_id = '2337'
    tcms_test_case = '315489'
    vm_name_base = "vm_%s" % tcms_test_case

    def _createVm(self, vm_name, sd, host):
        return vms.createVm(
            True, vm_name, vm_name, config.CLUSTER_NAME,
            storageDomainName=sd, size=config.DISK_SIZE,
            installation=True, diskType=config.DISK_TYPE_SYSTEM, memory=GB,
            cpu_socket=config.CPU_SOCKET, cpu_cores=config.CPU_CORES,
            nicType=config.NIC_TYPE_VIRTIO, highly_available=True,
            display_type=config.DISPLAY_TYPE,
            os_type=config.OS_TYPE, user=config.VM_LINUX_USER,
            password=config.VM_LINUX_PASSWORD, type=config.VM_TYPE_SERVER,
            slim=True, nic=config.HOST_NICS[0], volumeType=True,
            volumeFormat=ENUMS['format_cow'], useAgent=config.USE_AGENT,
            image=config.COBBLER_PROFILE, network=config.MGMT_BRIDGE,
            placement_host=host)

    def setUp(self):
        """
        create a VM on SPM
        """
        master_domain = storagedomains.findMasterStorageDomain(
            True, config.DATA_CENTER_NAME)[1]['masterDomain']
        host = hosts.getSPMHost(config.HOSTS)

        LOGGER.info("Create VM")
        assert self._createVm(self.vm_name_base, master_domain, host)


    @tcms(tcms_plan_id, tcms_test_case)
    def test_maintenance_spm_with_running_vm(self):
        """
            * maintenance SPM
        """
        self.spm_host = hosts.getSPMHost(config.HOSTS)

        LOGGER.info("Deactivating SPM host %s", self.spm_host)
        assert hosts.deactivateHost(True, self.spm_host)

        LOGGER.info("Waiting DC state to be up with the new spm")
        dc_ll.wait_for_datacenter_state_api(config.DATA_CENTER_NAME)

        new_spm = hosts.getSPMHost(config.HOSTS)
        LOGGER.info("New SPM is: %s", new_spm)
