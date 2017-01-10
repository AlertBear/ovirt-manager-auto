"""
Storage live snapshot sanity tests - full test
https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
Storage/3_1_Storage_Live_Snapshot
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
    Set live snapshot parameter to True
    """
    live_snapshot = True


@attr(tier=2)
class TestCase11660(BasePlan.TestCase18863, SnapshotBaseClass):
    """
    Full flow - Live Snapshot

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
    polarion_test_case = '11660'


@attr(tier=2)
class TestCase11679(BasePlan.TestCase11679, SnapshotBaseClass):
    """
    Add a disk to the VMs
    Create live snapshot
    Add 3 files to the VM
    Stop VM and restore snapshot

    Expected Results:

    Verify that the correct number of images were created
    Verify that a new data is written on new volumes
    """
    __test__ = True
    polarion_test_case = '11679'


@attr(tier=3)
class TestCase11676(BasePlan.TestCase11676, SnapshotBaseClass):
    """
    Try to create a snapshot with max chars length
    Try to create a snapshot with special characters

    Expected Results:

    Should be possible to create a snapshot with special characters and backend
    should not limit chars length
    """
    __test__ = True
    polarion_test_case = '11676'


@attr(tier=3)
class TestCase11665(BasePlan.TestCase11665):
    """
    Create 2 additional disks on a VM, each on a different storage domain
    Add snapshot

    Expected Results:
    You should be able to create a snapshot
    """
    __test__ = True
    live_snapshot = True
    polarion_test_case = '11665'


@attr(tier=3)
class TestCase11680(BasePlan.TestCase11680):
    """
    Migrate a VM without waiting
    Add snapshot to the same VM while migrating it

    Expected Results:

    It should be impossible to create a snapshot while VMs migration
    """
    __test__ = True
    live_snapshot = True
    polarion_test_case = '11680'


@attr(tier=2)
class TestCase11674(BasePlan.TestCase11674):
    """
    Add a second disk to a VM
    Add snapshot
    Make sure that the new snapshot appears only once

    Expected Results:

    Only one snapshot should be available in UI, no matter how many disks do
    you have.
    """
    __test__ = True
    live_snapshot = True
    polarion_test_case = '11674'


@attr(tier=3)
class TestCase11684(BasePlan.TestCase11684):
    """
    Create a template
    Create a thin provisioned VM from that template
    Create a cloned VM from that template
    Start the thin and cloned VMs
    Add live snapshot for both thin and cloned VMs

    Expected Results:

    Live snapshots should be created for both cases
    """
    __test__ = True
    live_snapshot = True
    polarion_test_case = '11684'
