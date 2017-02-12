"""
Storage Snapshot Basic Operations -
https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
Storage_4_0/4_1_Storage_Snapshot_Operations
"""
import base_snapshot_operation as BasePlan
from art.unittest_lib import attr

from rhevmtests.storage.fixtures import (
    create_vm, initialize_storage_domains, undo_snapshot, add_disk,
    create_template, start_vm, attach_disk, poweroff_vm, remove_vms,
    remove_vm, create_fs_on_disk
)  # flake8: noqa
from fixtures import (
    initialize_prepare_environment, add_disks_different_sd,
    add_two_vms_from_template,
)  # flake8: noqa


class SnapshotBaseClass(BasePlan.BasicEnvironmentSetUp):
    """
    Set live snapshot parameter to False
    """
    live_snapshot = False


class TestCase18868(BasePlan.TestCase18863, SnapshotBaseClass):
    """
    Full flow snapshot

    Create snapshot
    Add file to the VM
    Stop VM
    Preview and commit snapshot

    Expected Results:
    Snapshot should be successfully created
    Verify that a new data is written on new volumes
    Verify that the file no longer exists both after preview and after commit
    """
    __test__ = True
    polarion_test_case = '18868'


class TestCase18887(BasePlan.TestCase11679, SnapshotBaseClass):
    """
    Add a disk to the VMs
    Create snapshot
    Add 3 files to the VM
    Stop VM and restore snapshot

    Expected Results:

    Verify that the correct number of images were created
    Verify that a new data is written on new volumes
    """
    __test__ = True
    polarion_test_case = '18887'


class TestCase18884(BasePlan.TestCase11676, SnapshotBaseClass):
    """
    Try to create a snapshot with max chars length
    Try to create a snapshot with special characters

    Expected Results:

    Should be possible to create a snapshot with special characters and backend
    should not limit chars length
    """
    __test__ = True
    polarion_test_case = '18884'


class TestCase18873(BasePlan.TestCase11665):
    """
    Create 2 additional disks on a VM, each on a different storage domain
    Add snapshot

    Expected Results:
    You should be able to create a snapshot
    """
    __test__ = True
    polarion_test_case = '18873'
    live_snapshot = False


class TestCase18882(BasePlan.TestCase11674):
    """
    Add a second disk to a VM
    Add snapshot
    Make sure that the new snapshot appears only once

    Expected Results:

    Only one snapshot should be available in UI, no matter how many disks do
    you have.
    """
    __test__ = True
    polarion_test_case = '18882'
    live_snapshot = False


class TestCase18892(BasePlan.TestCase11684):
    """
    Create a template
    Create a thin provisioned VM from that template
    Create a cloned VM from that template
    Start the thin and cloned VMs
    Add snapshot for both thin and cloned VMs

    Expected Results:

    Snapshots should be created for both cases
    """
    __test__ = True
    polarion_test_case = '18892'
    live_snapshot = False
