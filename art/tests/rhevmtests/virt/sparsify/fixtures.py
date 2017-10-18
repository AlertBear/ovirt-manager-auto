import pytest
from art.unittest_lib import testflow
from art.rhevm_api.utils import test_utils
from art.rhevm_api.tests_lib.low_level import (
    vms as ll_vms,
    storagedomains as ll_sd,
    hosts as ll_hosts,
    disks as ll_disks
)
from art.rhevm_api.tests_lib.high_level import (
    storagedomains as hl_sd,
    disks as hl_disks
)

import rhevmtests.fixtures_helper as fixt_helper
import rhevmtests.helpers as helpers
import config


@pytest.fixture()
def block_storage_domain_setup(request):
    """
    Create new block storage domain (ISCSI or FC) with new lun
    """
    storage_type = request.node.cls.storage
    new_lun_identifier = request.node.cls.new_lun_identifier
    storage_domain_name = request.node.cls.storage_domain_name

    def fin():
        """
        Removes new storage domain
        """
        testflow.teardown(
            "Deactivate and detach storage domain: %s from the system",
            request.cls.storage_domain_name
        )
        current_spm_host = ll_hosts.get_spm_host(
            ll_hosts.get_cluster_hosts(config.CLUSTER_NAME[0])
        )
        assert hl_sd.detach_and_deactivate_domain(
            datacenter=config.DC_NAME[0],
            domain=request.cls.storage_domain_name,
            engine=config.ENGINE
        )
        testflow.teardown(
            "Remove storage domain: %s from the system",
            request.cls.storage_domain_name
        )
        assert ll_sd.removeStorageDomain(
            True,
            storagedomain=storage_domain_name,
            host=current_spm_host,
            destroy=True,
            force=True
        )
    request.addfinalizer(fin)
    spm_host = ll_hosts.get_spm_host(
        ll_hosts.get_cluster_hosts(config.CLUSTER_NAME[0])
    )
    if storage_type == config.STORAGE_TYPE_ISCSI:
        assert hl_sd.add_iscsi_data_domain(
            host=spm_host,
            storage=storage_domain_name,
            data_center=config.DC_NAME[0],
            lun=new_lun_identifier,
            lun_address=config.UNUSED_LUN_ADDRESSES[0],
            lun_target=config.UNUSED_LUN_TARGETS[0],
            login_all=True
        )
    elif storage_type == config.STORAGE_TYPE_FCP:
        assert hl_sd.add_fcp_data_domain(
            host=spm_host,
            storage=storage_domain_name,
            data_center=config.DC_NAME[0],
            lun=new_lun_identifier,
        )


@pytest.fixture()
def file_storage_domain_setup(request):
    """
    Sets class variables based on the specific file storage configurations
    """
    storage_type = request.cls.storage or request.getfixturevalue('storage')
    nfs_version = fixt_helper.get_fixture_val(request, "nfs_version")

    existing_storages = ll_sd.getStorageDomainNamesForType(
        config.DC_NAME[0], storage_type
    )

    if storage_type == config.STORAGE_TYPE_NFS:
        if nfs_version is not config.NFS_VERSION_AUTO:
            existing_storages = [
                sd for sd in existing_storages if ll_sd.get_nfs_version(sd) ==
                nfs_version
                ]
        if not existing_storages:
            pytest.skip(
                "Cannot run sparsify tests for SD of type: %s as this system "
                "doesn't have any such SD"
            )
    request.cls.storage_domain_name = existing_storages[0]
    spm_host = ll_hosts.get_spm_host(
        ll_hosts.get_cluster_hosts(config.CLUSTER_NAME[0])
    )
    request.cls.storage_manager = helpers.get_host_resource_by_name(
        spm_host
    )


@pytest.fixture()
def add_vms_on_specific_sd(request):
    """
    Adds vms from GE template, on the specific class SD.
    """
    storage_domain = request.cls.storage_domain_name
    number_of_thin_vms = get_number_of_vms(request)
    storage_type = request.cls.storage or request.getfixturevalue('storage')

    def fin1():
        testflow.teardown("Unlock disks")
        hl_disks.unlock_disks(engine=config.ENGINE)
        test_utils.wait_for_tasks(config.ENGINE, config.DC_NAME[0])
        testflow.teardown("Check there are no disks in locked status")
        assert hl_disks.check_no_locked_disks(engine=config.ENGINE)

    def fin2():
        """
        Removes vms
        """
        vms = config.THIN_PROVISIONED_VMS + config.PREALLOCATED_VMS
        testflow.teardown("Remove vms %s", vms)
        assert ll_vms.safely_remove_vms(vms)

    request.addfinalizer(fin2)
    request.addfinalizer(fin1)
    testflow.setup("Set vms names for test")
    del config.THIN_PROVISIONED_VMS[:]
    if number_of_thin_vms:
        config.THIN_PROVISIONED_VMS = [
            'sparsify_{0}_vm_{1}'.format(
                storage_type, i + 1
            ) for i in range(number_of_thin_vms)
        ]
    for vm in config.THIN_PROVISIONED_VMS:
        testflow.setup(
            "Create vm: %s from template %s with params: %s",
            vm, config.TEMPLATE_NAME[0], config.THIN_VM_PARAMS
        )
        assert ll_vms.cloneVmFromTemplate(
            positive=True,
            name=vm,
            template=config.TEMPLATE_NAME[0],
            cluster=config.CLUSTER_NAME[0],
            storagedomain=storage_domain,
            wait=False,
            **config.THIN_VM_PARAMS
        )
        disk_id = ll_vms.getObjDisks(name=vm, get_href=False)[0].id
        assert ll_disks.wait_for_disks_status(disk_id, key='id')
        assert ll_disks.updateDisk(
            positive=True, vmName=vm, id=disk_id, bootable=True,
        )
        if not ll_vms.get_vm_nics_obj(vm):
            assert ll_vms.addNic(positive=True, vm=vm, name='nic1')
    testflow.setup("Wait for new vms and disks creation to be done")
    assert ll_vms.waitForVmsStates(
        True, config.THIN_PROVISIONED_VMS,
        states=config.VM_DOWN_STATE
    )
    for vm in config.THIN_PROVISIONED_VMS:
        assert ll_vms.waitForVmsDisks(vm)


@pytest.fixture()
def copy_template_to_new_storage_domain(request):
    """
    Copy the GE template to the new storage domain
    """
    new_domain = request.cls.storage_domain_name
    template_disk = ll_disks.getObjDisks(
        config.TEMPLATE_NAME[0], get_href=False, is_template=True
    )[0]
    assert ll_disks.copy_disk(
        disk_id=template_disk.get_id(), target_domain=new_domain,
        timeout=config.COPY_DISK_TIMEOUT
    )


def get_number_of_vms(request):
    """
    Parse number of VMs from request and return tuple

    Args:
        request (FixtureRequest): request with session info

    Returns:
        init: number_of_thin_vms
    """
    args = request.node.get_marker("initialization_param")
    initialization_params = args.kwargs if args else {}
    if initialization_params:
        return (
            initialization_params["number_of_thin_vms"]
        )
    else:
        number_of_thin_vms = getattr(request.cls, "number_of_thin_vms", 0)
        return number_of_thin_vms


@pytest.fixture()
def add_disks_to_vm(request):
    """
    Adds 2 disks to one of the test's vm for multiple disks on vm case
    """
    storage_domain = config.NEW_SD
    vm = config.THIN_PROVISIONED_VMS[1]

    def fin():
        """
        Remove the 2 new disks from the vm at tht end of the test
        """
        new_disks = [
            ll_vms.getVmDisk(vm, disk) for disk in config.NEW_DISKS_ALIAS
        ]
        for disk in new_disks:
            assert ll_vms.removeDisk(True, vm, disk_id=disk.get_id())

    request.addfinalizer(fin)
    for disk in config.NEW_DISKS_ALIAS:
        assert ll_vms.addDisk(
            True, vm, 2 * config.GB, storagedomain=storage_domain, alias=disk
        )


@pytest.fixture()
def add_perallocate_disk(request):
    """
    Add VM with preallocated disk
    """
    vm_name = config.THIN_PROVISIONED_VMS[0]
    storage_domain = request.cls.storage_domain_name
    disk_alias = vm_name + "_perallocate_disk"

    testflow.step("Add per-allocate disk to VM")
    assert ll_vms.addDisk(
        positive=True,
        vm=vm_name,
        provisioned_size=2 * config.GB,
        storagedomain=storage_domain,
        alias=disk_alias,
        sparse=False,
        format=config.DISK_FORMAT_RAW
    )
    disk_id = ll_vms.getObjDisks(name=vm_name, get_href=False)[1].get_id()
    assert ll_disks.wait_for_disks_status(
        disk_id, key='id'
    ), "Failed to add per-allocate disk"


@pytest.fixture()
def set_storage_domain_name(request, storage):
    self = request.node.cls
    self.storage_domain_name = config.NEW_SD_NAME % storage
