import config
import pytest
import logging
import shlex

from art.rhevm_api.tests_lib.low_level import (
    datacenters as ll_dc,
    hosts as ll_hosts,
    storagedomains as ll_sd,
    disks as ll_disks,
)
from art.unittest_lib import testflow
from rhevmtests import helpers as rhevm_helpers
from rhevmtests.storage import helpers as storage_helpers
from subprocess import Popen, PIPE

logger = logging.getLogger(__name__)


@pytest.fixture(scope='class')
def initialize_variables(request, storage):
    """
    Initialize variables needed for the test
    """
    self = request.node.cls

    spm = ll_hosts.get_spm_host(config.HOSTS)
    self.spm_host = rhevm_helpers.get_host_resource_by_name(spm)
    data_center_obj = ll_dc.get_data_center(config.DATA_CENTER_NAME)
    self.sp_id = storage_helpers.get_spuuid(data_center_obj)
    self.storage_domain = ll_sd.getStorageDomainNamesForType(
        config.DATA_CENTER_NAME, self.storage
    )[0]
    self.disks_names = list()


@pytest.fixture(scope='class')
def test_detach_disks(request, storage):
    """
    Detach disks from VM before test
    """

    self = request.node.cls

    disk_ids = self.DISKS_MOUNTS_EXECUTOR[self.vm_name]['disks']
    for disk in disk_ids:
        disk_name = ll_disks.get_disk_obj(disk, attribute='id').get_name()
        self.disks_names.append(disk_name)
        testflow.setup("detach disk %s", disk_name)

        assert ll_disks.detachDisk(
            True, disk_name, self.vm_name
        ), "Failed to detach disk %s to vm %s" % (self.disk_name, self.vm_name)
    self.disks_to_remove = self.disks_names


@pytest.fixture(scope='class')
def test_delete_downloaded_files(request, storage):
    """
    Delete downloaded files from test runner machine
    """

    self = request.node.cls

    self.files_to_remove = list()

    def finalizer():
        testflow.teardown(
            "deleting downloaded files %s", self.files_to_remove[0]
        )
        (out, err) = Popen(
            shlex.split("rm " + " ".join(self.files_to_remove[0])),
            stdout=PIPE, stderr=PIPE
        ).communicate()
        assert not err, (
            "error %s occured when trying to execute the command %s" % (
                err, "rm " + " ".join(self.files_to_remove[0])
            )
        )
    request.addfinalizer(finalizer)
