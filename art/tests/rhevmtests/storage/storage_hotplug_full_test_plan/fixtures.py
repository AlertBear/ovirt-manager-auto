import pytest
import logging
import config
import helpers
import os

from art.rhevm_api.tests_lib.low_level import (
    datacenters as ll_dc,
    disks as ll_disks,
    hosts as ll_hosts,
    vms as ll_vms,
    jobs as ll_jobs,
)
from rhevmtests.storage import helpers as storage_helpers
from rhevmtests import helpers as rhevm_helpers
from art.unittest_lib.common import testflow

logger = logging.getLogger(__name__)


@pytest.fixture()
def initializer_hotplug_hook(request, storage):
    """
    Initialize test params and ensure VM is 'UP'
    """
    self = request.node.cls

    def finalizer():
        """
        Clear hooks and removes hook results
        """
        helpers.run_cmd(
            self.executor, ['rm', '-f', config.FILE_WITH_RESULTS]
        )
        helpers.clear_hooks(self.executor)
        assert ll_vms.stop_vms_safely([self.vm_name]), (
            "Failed to stop VM %s" % self.vm_name
        )
    request.addfinalizer(finalizer)
    self.use_disks = config.DISKS_TO_PLUG[self.storage]
    self.vm_name = config.VM_NAMES.get(self.storage)

    if ll_vms.get_vm_state(self.vm_name) != config.VM_UP:
        testflow.setup("Start VM: %s", self.vm_name)
        # TODO: Because of BZ1273891 - vm can be down after the hotplug
        assert ll_vms.startVm(True, self.vm_name), (
            "Failed to start VM %s" % self.vm_name
        )
        assert ll_vms.waitForVMState(self.vm_name), (
            "VM %s doesn't reach to state UP" % self.vm_name
        )

    self.host_name = ll_vms.get_vm_host(vm_name=self.vm_name)
    self.host_address = ll_hosts.get_host_ip(self.host_name)

    self.user = config.HOSTS_USER
    self.password = config.HOSTS_PW
    logger.info("Creating 'executor' object")
    self.executor = rhevm_helpers.get_host_resource(
        ip=self.host_address, password=self.password, username=self.user
    )
    self.host_resource = rhevm_helpers.get_host_resource(
        ip=self.host_address, password=self.password, username=self.user
    )


@pytest.fixture()
def create_results_files(request, storage):
    """
    Create hotplug/unplug hooks on host machine
    """
    self = request.node.cls

    testflow.setup("Clear old files and create new results files")

    testflow.setup("Clearing old hooks")
    helpers.clear_hooks(self.executor)

    testflow.setup("Removing old results")
    helpers.run_cmd(self.executor, ['rm', '-f', config.FILE_WITH_RESULTS])
    testflow.setup("Touching result file")
    helpers.run_cmd(self.executor, ['touch', config.FILE_WITH_RESULTS])
    testflow.setup("Changing permissions of results")
    helpers.run_cmd(
        self.executor, ['chown', '36:36', config.FILE_WITH_RESULTS]
    )


@pytest.fixture()
def set_disks_in_the_correct_state(request, storage):
    """
    Activate or deactivate disk according to self.active_disk
    """
    self = request.node.cls

    testflow.setup("Putting disks in correct state")
    activate_or_deactivate_disks = getattr(
        self, 'put_disk_in_correct_state', True
    )
    if activate_or_deactivate_disks:
        for disk_name in self.use_disks:
            active = ll_vms.is_active_disk(self.vm_name, disk_name, 'alias')
            logger.info("Disk active: %s", active)
            if active and not self.active_disk:
                assert ll_vms.deactivateVmDisk(True, self.vm_name, disk_name)
            elif not active and self.active_disk:
                assert ll_vms.activateVmDisk(True, self.vm_name, disk_name)


@pytest.fixture()
def install_hooks(request, storage):
    """
    Install hotplug/unplug hooks
    """
    self = request.node.cls
    non_executable_hook = getattr(self, 'non_executable_hook', False)

    testflow.setup("Installing hooks")
    for hook_dir, hooks in self.hooks.iteritems():
        for hook in hooks:
            remote_hook = os.path.join(
                config.MAIN_HOOK_DIR, hook_dir, os.path.basename(hook)
            )
            assert config.SLAVE_HOST.fs.transfer(
                path_src=hook,
                target_host=self.host_resource,
                path_dst=remote_hook
            )
            testflow.setup("Changing permissions")
            if not non_executable_hook:
                helpers.run_cmd(self.executor, ["chmod", "775", remote_hook])
                helpers.run_cmd(self.executor, ["chown", "36:36", remote_hook])


@pytest.fixture()
def remove_vm_disk(request, storage):

    self = request.node.cls

    def finalizer():
        """
        remove disk from a VM
        """
        testflow.setup(
            "Remove disk: %s of VM: %s", self.disk_name, self.vm_name
        )
        assert ll_vms.deactivateVmDisk(
            positive=True, vm=self.vm_name, diskAlias=self.disk_name
        ), "Failed to deactivate disk: %s of VM: %s" % (
            self.disk_name, self.vm_name
        )
        assert ll_vms.removeDisk(
            positive=True, vm=self.vm_name, disk=self.disk_name
        ), "Failed to remove disk: %s from VM: %s" % (
            self.disk_name, self.vm_name
        )
    request.addfinalizer(finalizer)


@pytest.fixture()
def wait_for_dc_and_hosts(request, storage):

    self = request.node.cls

    def finalizer():
        """
        Give VDSM time to restart and clean the environment
        """
        assert ll_dc.waitForDataCenterState(name=config.DATA_CENTER_NAME), (
            "Data-center failed to reach state %s" % config.DATA_CENTER_UP
        )
        assert ll_hosts.wait_for_hosts_states(
            positive=True, names=[self.host_name]
        ), "Host failed to reach state %s" % config.HOST_UP
    request.addfinalizer(finalizer)


@pytest.fixture(scope='class')
def add_disks_to_vm(request, storage):
    """
    Create a VM with 2 disks - 1 active and 1 inactive
    """

    self = request.node.cls

    testflow.setup(
        "Adding 1 active disk and 1 inactive disk to VM %s", self.vm_name
    )

    for interface in self.interfaces:
        disk_params = config.disk_args.copy()
        disk_params['wipe_after_delete'] = self.storage in config.BLOCK_TYPES
        disk_params['storagedomain'] = self.storage_domain
        disk_params['interface'] = interface
        disk_params['vm'] = self.vm_name

        for active in True, False:
            disk_params['alias'] = storage_helpers.create_unique_object_name(
                self.__class__.__name__, config.OBJECT_TYPE_DISK
            )
            logger.info(
                "Adding disk to vm %s with %s active disk",
                self.vm_name, "not" if not active else ""
            )
            disk_params['active'] = active
            assert ll_vms.addDisk(
                positive=True, **disk_params
            ), "Unable to add disk to VM %s" % self.vm_name


@pytest.fixture(scope='class')
def add_floating_disks(request, storage):
    """
    Create floating disks - 1 shareable and 1 non-shareable from each
    interface
    """

    self = request.node.cls

    testflow.setup(
        "Adding 1 shareable disk and 1 non-shareable disk to VM %s",
        self.vm_name
    )
    self.disk_aliases = []

    for disk_interface in self.interfaces:
        for shareable in (True, False):
            disk_params = config.disk_args.copy()
            disk_params['interface'] = disk_interface
            disk_params['shareable'] = shareable
            if shareable:
                disk_params['format'] = config.DISK_FORMAT_RAW
                disk_params['sparse'] = False
            disk_params['storagedomain'] = self.storage_domain
            disk_params['alias'] = (
                storage_helpers.create_unique_object_name(
                    self.__class__.__name__, config.OBJECT_TYPE_DISK
                )
            )
            assert ll_disks.addDisk(True, **disk_params), (
                "Can't create disk with params: %s" % disk_params
            )
            logger.info(
                "Waiting for disk %s to be OK", disk_params['alias']
            )
            assert ll_disks.wait_for_disks_status(disk_params['alias']), (
                "Disk '%s' has not reached state 'OK'" % disk_params['alias']
            )
            self.disk_aliases.append(disk_params['alias'])
        # initialize for delete_disks fixture
        self.disks_to_remove = self.disk_aliases


@pytest.fixture(scope='class')
def attach_floating_disks_to_vm(request, storage):
    """
    Attach floating disks from add_floating_disks fixture to a VM
    """

    self = request.node.cls
    testflow.setup(
        "Attach 2 disks: %s to VM: %s", self.disk_aliases, self.vm_name
    )
    for disk in self.disk_aliases:
        assert ll_disks.attachDisk(
            positive=True, alias=disk, vm_name=self.vm_name, active=True
        ), "Unable to attach disk %s to VM %s" % (disk, self.vm_name)
        if ll_disks.get_disk_obj(disk_alias=disk).get_shareable():
            assert ll_disks.attachDisk(
                positive=True, alias=disk, vm_name=self.vm_name_2, active=True
            ), "Unable to attach disk %s to VM %s" % (disk, self.vm_name)


@pytest.fixture(scope='class')
def create_second_vm(request, storage):
    """
    Create second VM and initialize parameters
    """
    self = request.node.cls

    def finalizer():
        """
        Remove the second VM
        """
        testflow.teardown("Remove VM: %s", self.vm_name_2)
        assert ll_vms.safely_remove_vms([self.vm_name_2]), (
            "Failed to power off and remove VM %s" % self.vm_name_2
        )
        ll_jobs.wait_for_jobs([config.JOB_REMOVE_VM])
    request.addfinalizer(finalizer)

    self.vm_name_2 = storage_helpers.create_unique_object_name(
        self.__name__, config.OBJECT_TYPE_VM
    )
    testflow.setup("Create VM: %s", self.vm_name_2)
    vm_args = config.create_vm_args.copy()
    vm_args['storageDomainName'] = self.storage_domain
    vm_args['cluster'] = config.CLUSTER_NAME
    vm_args['vmName'] = self.vm_name_2
    vm_args['deep_copy'] = False
    testflow.setup("Creating VM %s", self.vm_name_2)
    assert storage_helpers.create_vm_or_clone(**vm_args), (
        "Failed to create VM %s" % self.vm_name_2
    )
