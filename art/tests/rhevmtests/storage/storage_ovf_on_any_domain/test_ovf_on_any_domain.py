"""
3.5 Storage OVF on any Domain
https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
Storage/3_5_Storage_OVF_On_Any_Domain
"""
import pytest
import logging
import config
import helpers
from art.core_api.apis_utils import TimeoutingSampler
from art.rhevm_api.tests_lib.low_level import (
    disks as ll_disks,
    storagedomains as ll_sd,
    templates as ll_templates,
    vmpools as ll_vmpools,
    vms as ll_vms,
)
from art.rhevm_api.utils import test_utils
from art.test_handler.settings import ART_CONFIG
from art.test_handler.tools import bz, polarion
from art.unittest_lib import (
    tier2,
    tier3,
)
from art.unittest_lib import StorageTest as BaseTestCase
from art.unittest_lib.common import testflow
from rhevmtests.storage import helpers as storage_helpers
from fixtures import (
    initialize_variables, initialize_storage_domains_for_test,
    initialize_new_disk_params, initialize_direct_lun_params,
    init_params_for_diskless_test, initialize_template_params,
    set_ovf_store_count, initalize_vm_to_remove,
    remove_ovf_store_from_glance_domain, initialize_vm_pool_name,
    remove_ovf_store_disks,
)
from rhevmtests.storage.fixtures import (
    create_vm, remove_vms, add_disk, delete_disk, create_second_vm,
    remove_template, remove_vms_pool,
)

from rhevmtests.storage.fixtures import remove_vm  # noqa

logger = logging.getLogger(__name__)
ENUMS = config.ENUMS

ISCSI = config.STORAGE_TYPE_ISCSI
NFS = config.STORAGE_TYPE_NFS
GLUSTERFS = config.STORAGE_TYPE_GLUSTER


@pytest.mark.usefixtures(
    initialize_storage_domains_for_test.__name__,
    create_vm.__name__,
    initialize_variables.__name__,
)
@bz({'1507824': {}})
class BasicEnvironment(BaseTestCase):
    """
    This class implements the common functions including the setUp and
    tearDown for this feature
    """
    __test__ = False

    def get_ovf_contents_or_num_ovf_files(
        self, disk, vm, template, vm_or_template_id, sd_id,
        ovf_should_exist=True, get_content=True
    ):
        """
        Extract and return the OVF contents for the VM or Template, or the
        number of OVF files within OVF store provided
        """
        ovf_store_args = {
            'host': self.spm_host,
            'is_block': self.is_block_storage,
            'disk_or_template_or_vm_name': '',
            'vm_or_template_id': vm_or_template_id,
            'sd_id': sd_id,
            'ovf_id': '',
            'sp_id': '',
            'ovf_filename': ''
        }
        if self.is_block_storage:
            ovf_store_args['ovf_id'] = self.ovf_store['img_id']
        else:
            ovf_store_args['ovf_id'] = self.ovf_store['id']
            ovf_store_args['ovf_filename'] = self.ovf_store['img_id']
            ovf_store_args['sp_id'] = self.sp_id

        if template:
            ovf_store_args['disk_or_template_or_vm_name'] = template
        elif disk:
            ovf_store_args['disk_or_template_or_vm_name'] = disk
        elif vm:
            ovf_store_args['disk_or_template_or_vm_name'] = vm

        for ovf_remote_full_path_num_ovf_files in TimeoutingSampler(
                timeout=config.FIND_OVF_INFO_TIMEOUT,
                sleep=config.FIND_OVF_INFO_SLEEP,
                func=helpers.get_ovf_file_path_and_num_ovf_files,
                **ovf_store_args
        ):
            if ovf_remote_full_path_num_ovf_files is not None or (
                    not ovf_should_exist
            ):
                break

        if ovf_remote_full_path_num_ovf_files is None and ovf_should_exist:
            assert False, (
                "The OVF file for the VM or Template still doesn't exist, "
                "aborting run"
            )

        ovf_remote_full_path = (
            ovf_remote_full_path_num_ovf_files['ovf_file_path']
        )
        number_of_ovf_files = (
            ovf_remote_full_path_num_ovf_files['number_of_ovf_files']
        )

        if not ovf_should_exist:
            assert not self.spm_host.fs.exists(ovf_remote_full_path)
            return None

        if not self.spm_host.fs.exists(ovf_remote_full_path):
            logger.info("The OVF file for the VM still doesn't exist, return")
            return None

        ovf_file_content = self.spm_host.fs.read_file(ovf_remote_full_path)
        self.spm_host.fs.remove(ovf_remote_full_path)

        if get_content:
            return ovf_file_content
        else:
            return number_of_ovf_files

    def validate_vm_in_ovf_contents(
        self, disk_name, vm_name, storage_domain, vm_id=None, positive=True,
        should_ovf_exist=True
    ):
        """
        Validate the OVF contents for the requested VM, ensuring each attached
        disk is checked for
        """
        sd_id = ll_sd.get_storage_domain_obj(storage_domain).get_id()
        if not vm_id:
            vm_id = ll_vms.get_vm_obj(vm_name).get_id()

        for ovf_file_content in TimeoutingSampler(
            timeout=config.FIND_OVF_INFO_TIMEOUT,
            sleep=config.FIND_OVF_INFO_SLEEP,
            func=self.get_ovf_contents_or_num_ovf_files,
            disk=disk_name, vm=vm_name, template=None,
            vm_or_template_id=vm_id, sd_id=sd_id,
            ovf_should_exist=should_ovf_exist, get_content=True
        ):
            logger.info(
                "Removing the extracted OVF store for disk '%s'", disk_name
            )
            helpers.remove_ovf_store_extracted(
                self.spm_host, disk_name
            )

            if not should_ovf_exist:
                logger.info(
                    "VM OVF was not expected to exist, validated as "
                    "part of the "
                    "self.get_ovf_contents_or_num_ovf_files call"
                )
                break

            if ovf_file_content is None:
                logger.info("No OVF content retrieved")
                continue

            if positive:
                if disk_name in ovf_file_content:
                    break
                else:
                    logger.info(
                        "Positive path, disk '%s' isn't found in VM "
                        "'%s' OVF file", disk_name, vm_name
                    )
            else:
                if disk_name not in ovf_file_content:
                    break
                else:
                    logger.info(
                        "Negative path, disk '%s' isn't found in VM "
                        "'%s' OVF file", disk_name, vm_name
                    )

            if should_ovf_exist:
                if positive:
                    assert disk_name, (
                        "Disk alias '%s' was not found in the OVF file, "
                        "contents '%s'" % (
                            disk_name, ovf_file_content
                        )
                    )
                else:
                    assert disk_name, (
                        "Disk alias '%s' was found in the OVF file, "
                        "contents '%s'" % (
                            disk_name, ovf_file_content
                        )
                    )

    def validate_template_in_ovf_contents(
        self, disk_name, template_name, storage_domain, positive=True,
        should_ovf_exist=True
    ):
        """
        Validate the OVF contents for the requested template
        """
        sd_id = ll_sd.get_storage_domain_obj(storage_domain).get_id()
        template_id = ll_templates.get_template_obj(
            self.template_name
        ).get_id()
        for ovf_file_content in TimeoutingSampler(
            timeout=config.FIND_OVF_INFO_TIMEOUT,
            sleep=config.FIND_TEMPLATE_OVF_INFO_SLEEP,
            func=self.get_ovf_contents_or_num_ovf_files,
            disk=disk_name, vm=None, template=template_name,
            vm_or_template_id=template_id, sd_id=sd_id,
            ovf_should_exist=should_ovf_exist, get_content=True
        ):
            if ovf_file_content is None:
                logger.info("No OVF content retrieved, try again")
                continue
            else:
                logger.info(
                    "Removing the extracted OVF store for template '%s'",
                    template_name
                )
                helpers.remove_ovf_store_extracted(
                    self.spm_host, template_name
                )
                break

        if should_ovf_exist:
            if positive:
                assert config.OBJECT_NAME_IN_OVF % template_name in (
                    ovf_file_content
                ), (
                    "Template name '%s' was not found in the OVF file "
                    "contents '%s'" % (template_name, ovf_file_content)
                )
                assert disk_name in ovf_file_content, (
                    "Disk alias '%s' was not found in the OVF file "
                    "contents '%s'" % (
                        disk_name, ovf_file_content
                    )
                )
            else:
                assert config.OBJECT_NAME_IN_OVF % template_name not in (
                    ovf_file_content
                ), (
                    "Template name '%s' was found in the OVF file "
                    "contents '%s'" % (template_name, ovf_file_content)
                )

    def validate_ovf_contents(
        self, disk_name=None, vm_name=None, vm_id=None, template_name=None,
        storage_domain=None, positive=True, should_ovf_exist=True
    ):
        """
        Validate the OVF contents for the requested VM, ensuring each
        attached disk is checked for
        """
        self.ovf_store = helpers.get_first_ovf_store_id_and_obj(storage_domain)
        storage_domain_type = ll_sd.get_storage_domain_storage_type(
            storage_domain
        )
        self.is_block_storage = (
            True if storage_domain_type in config.BLOCK_TYPES else False
        )

        if self.is_block_storage:
            logger.info(
                "Block based storage, will use LVM methods to extract OVF "
                "store"
            )
            self.spm_host.lvm.pvscan()
        else:
            logger.info(
                "File based storage, will use file system methods to extract"
                "OVF store"
            )

        if vm_name:
            self.validate_vm_in_ovf_contents(
                disk_name, vm_name, storage_domain, vm_id, positive,
                should_ovf_exist
            )
        elif template_name:
            self.validate_template_in_ovf_contents(
                disk_name, template_name, storage_domain, positive,
                should_ovf_exist
            )
        else:
            assert False, (
                "vm_name or template_name must be passed in to "
                "validate_ovf_contents"
            )

    def retrieve_number_of_ovf_files_from_ovf_store(
        self, vm_name=None, template_name=None
    ):
        """
        Return the number of OVF files found in the OVF store of the VM or
        Template.  Note that in the case of a VM, it is assumed that there
        is only one disk attached
        """
        number_of_ovf_files = -1
        if self.is_block_storage:
            logger.info(
                "Block based storage, will use LVM methods to extract OVF "
                "store"
            )
            self.spm_host.lvm.pvscan()
        else:
            logger.info(
                "File based storage, will use file system methods to extract "
                "OVF store"
            )

        sd_id = ll_sd.get_storage_domain_obj(self.storage_domain).get_id()

        if vm_name:
            vm_id = ll_vms.get_vm_obj(vm_name).get_id
            number_of_ovf_files = (
                self.get_ovf_contents_or_num_ovf_files(
                    disk=self.disk_name, vm=vm_name, template=None,
                    sd_id=sd_id, vm_or_template_id=vm_id, get_content=False
                )
            )
            logger.info(
                "Removing the extracted OVF store for disk '%s'",
                self.disk_name
            )
            helpers.remove_ovf_store_extracted(self.spm_host, self.disk_name)
        elif template_name:
            template_id = ll_templates.get_template_obj(
                self.template_name
            ).get_id()
            number_of_ovf_files = self.get_ovf_contents_or_num_ovf_files(
                disk=self.disk_name, vm=None, template=template_name,
                vm_or_template_id=template_id, sd_id=sd_id, get_content=False
            )
            logger.info(
                "Removing the extracted OVF store for template '%s'",
                template_name
            )
            helpers.remove_ovf_store_extracted(self.spm_host, template_name)
        return number_of_ovf_files


@pytest.mark.usefixtures(
    init_params_for_diskless_test.__name__,
)
class EnvironmentWithDisklessVm(BasicEnvironment):
    """
    This class implements the common functions for tests that require a
    standalone VM created
    """
    __test__ = False
    diskless_vm = True
    installation = False


class TestCase6247(BasicEnvironment):
    """
    Disk on master domain attached to VM

    1. Create a VM with a disk on master storage domain, ensure the OVF is
    created on this storage domain

    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/
    workitem?id=RHEVM3-6247
    """
    __test__ = True
    polarion_test_case = '6247'
    disk_on_master = True

    @polarion("RHEVM3-6247")
    @tier2
    def test_disk_on_master_domain(self):
        """ Polarion case 6247 """
        testflow.step(
            "Validate the OVF store contents for VM '%s'",
            self.vm_name
        )
        ll_sd.update_ovf_store(self.storage_domain)
        self.validate_ovf_contents(
            disk_name=self.disk_name, vm_name=self.vm_name,
            storage_domain=self.storage_domain
        )


class TestCase6248(BasicEnvironment):
    """
    Disk on non-master domain attached to VM

    1. Create a VM with a disk on a non-master storage domain, ensure the
    OVF is created on this storage domain

    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/
    workitem?id=RHEVM3-6248
    """
    __test__ = True
    polarion_test_case = '6248'
    disk_on_non_master = True

    @polarion("RHEVM3-6248")
    @tier2
    def test_disk_on_non_master_domain(self):
        """ Polarion case 6248 """
        testflow.step(
            "Validate the OVF store contents for VM '%s'",
            self.vm_name
        )
        ll_sd.update_ovf_store(self.storage_domain)
        self.validate_ovf_contents(
            disk_name=self.disk_name, vm_name=self.vm_name,
            storage_domain=self.storage_domain
        )


@pytest.mark.usefixtures(
    create_second_vm.__name__,
    remove_vms.__name__,
)
class TestCase6250(BasicEnvironment):
    """
    Several Disks from several VMs on one storage domain

    1. Create 2 VMs, each with a disk, ensure that OVFs are created on this
    storage domain

    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/
    workitem?id=RHEVM3-6250
    """
    __test__ = True
    polarion_test_case = '6250'

    @polarion("RHEVM3-6250")
    @tier3
    def test_multiple_disks_on_single_domain(self):
        """ Polarion case 6250 """
        self.disk_name_2 = ll_vms.get_vm_bootable_disk(self.vm_name_2)
        disk_names = [self.disk_name, self.disk_name_2]
        self.vm_names = [self.vm_name, self.vm_name_2]

        for vm, disk in zip(self.vm_names, disk_names):
            testflow.step(
                "Validate the OVF store contents for VM '%s'", vm
            )
            ll_sd.update_ovf_store(self.storage_domain)
            self.validate_ovf_contents(
                disk_name=disk, vm_name=vm, storage_domain=self.storage_domain
            )


@pytest.mark.usefixtures(
    initialize_new_disk_params.__name__,
)
class TestCase6251(BasicEnvironment):
    """
    VM with disks on 2 storage domains

    1. Create 1 VM with 2 disks (each on a different storage domain), ensure
    that OVFs are created on each of the storage domains

    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/
    workitem?id=RHEVM3-6251
    """
    __test__ = True
    polarion_test_case = '6251'

    @polarion("RHEVM3-6251")
    @tier3
    def test_one_vm_with_disks_on_multiple_domains(self):
        """ Polarion case 6251 """
        storage_helpers.add_new_disk(
            self.storage_domain_1, self.disk_args, self.storage
        )
        ll_disks.wait_for_disks_status([self.new_disk_name])
        ll_disks.attachDisk(True, self.new_disk_name, self.vm_name)

        disk_names = [self.disk_name, self.new_disk_name]
        sd_list = [self.storage_domain, self.storage_domain_1]

        testflow.step(
            "Validate the OVF store contents for VM '%s'",
            self.vm_name
        )
        for disk, sd in zip(disk_names, sd_list):
            ll_sd.update_ovf_store(sd)
            self.validate_ovf_contents(
                disk_name=disk, vm_name=self.vm_name, storage_domain=sd
            )


@pytest.mark.usefixtures(
    initialize_new_disk_params.__name__,
    remove_ovf_store_from_glance_domain.__name__,
)
class TestCase6252(BasicEnvironment):
    """
    Actions on OVF store

    1. Create a VM
    2. Create a disk on the master domain and attach it to the VM
    3. Create a disk on the non-master domain and attach it to the VM
    4. Ensure that OVF files are created containing info for both disks
    5. Try moving the OVF store for each disk into a different storage
    domain - this should fail
    6. Try to export the OVF store for each disk into a glance domain -
    this should succeed
    7. Try to remove the OVF store for each disk - this should fail

    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/
    workitem?id=RHEVM3-6252
    """
    __test__ = True
    polarion_test_case = '6252'
    disk_on_master = True

    @polarion("RHEVM3-6252")
    @tier3
    def test_actions_on_ovf_store(self):
        """ Polarion case 6252 """
        found, storage_domain = ll_sd.findNonMasterStorageDomains(
            True, datacenter=config.DATA_CENTER_NAME
        )
        non_master_sd = storage_domain.get('nonMasterDomains')[0]

        storage_helpers.add_new_disk(
            non_master_sd, self.disk_args, self.storage
        )
        ll_disks.wait_for_disks_status([self.new_disk_name])
        ll_disks.attachDisk(True, self.new_disk_name, self.vm_name)

        disk_names = [self.disk_name, self.new_disk_name]
        self.sd_list = [self.storage_domain, non_master_sd]

        testflow.step(
            "Validate the OVF store contents for VM '%s'",
            self.vm_name
        )
        for disk, sd in zip(disk_names, self.sd_list):
            ll_sd.update_ovf_store(sd)
            ovf_disk_id = helpers.get_first_ovf_store_id_and_obj(sd)['id']
            self.validate_ovf_contents(
                vm_name=self.vm_name, disk_name=disk, storage_domain=sd
            )
            helpers.move_ovf_store(self.vm_name, disk, ovf_disk_id)
            helpers.export_ovf_store_to_glance(ovf_disk_id)
            helpers.delete_ovf_store_disk(ovf_disk_id)


@pytest.mark.usefixtures(
    add_disk.__name__,
    delete_disk.__name__,
)
class TestCase6253File(BasicEnvironment):
    """
    VM with an attached shareable disk

    1. Create 1 VM with no disks
    2. Attach a shared disk to this VM
    OVF should be created, but the disk alias for the shared disk should not
    be part of the OVF file contents

    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/
    workitem?id=RHEVM3-6253
    """
    __test__ = (NFS in ART_CONFIG['RUN']['storages'])
    storages = set([NFS])
    polarion_test_case = '6253'
    diskless_vm = True
    installation = False
    add_disk_params = config.ADD_DISK_PARAMS

    @polarion("RHEVM3-6253")
    @tier3
    def test_one_vm_with_shared_disk(self):
        """ Polarion case 6253 """
        ll_disks.attachDisk(True, self.disk_name, self.vm_name, bootable=True)

        testflow.step(
            "Validate the OVF store contents for VM '%s'",
            self.vm_name
        )
        ll_sd.update_ovf_store(self.storage_domain)
        self.validate_ovf_contents(
            disk_name=self.disk_name, vm_name=self.vm_name,
            storage_domain=self.storage_domain, positive=False
        )


@pytest.mark.usefixtures(
    add_disk.__name__,
    initialize_direct_lun_params.__name__,
    delete_disk.__name__,
)
class TestCase6253Block(BasicEnvironment):
    """
    VM with attached disks: shared disk and direct LUN

    1. Create 1 VM with no disks
    2. Attach a shared disk to this VM
    3. Attach a direct LUN to this VM
    OVF should be created, but the disk aliases for the shared disk and the
    direct LUN should not be part of the OVF file contents

    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/
    workitem?id=RHEVM3-6253
    """
    # Direct LUN is only possible on Block devices
    __test__ = ISCSI in ART_CONFIG['RUN']['storages']
    storages = set([ISCSI])
    polarion_test_case = '6253'
    diskless_vm = True
    installation = False
    add_disk_params = config.ADD_DISK_PARAMS
    # Bugzilla history
    # Bug 1273376: OVF file is removed for any given VM when only a direct
    # LUN disk is attached to it

    @polarion("RHEVM3-6253")
    @tier3
    def test_one_vm_with_shared_disk_and_direct_LUN(self):
        """ Polarion case 6253 """
        ll_disks.attachDisk(True, self.disk_name, self.vm_name, bootable=True)

        testflow.step("Adding direct LUN %s", self.direct_lun_name)
        assert ll_disks.addDisk(
            True, **self.direct_lun_args
        ), "Failed to create direct LUN"
        ll_disks.attachDisk(True, self.direct_lun_name, self.vm_name)

        testflow.step(
            "Validate the OVF store contents for VM '%s'",
            self.vm_name
        )
        ll_sd.update_ovf_store(self.storage_domain)
        for disk in [self.disk_name, self.direct_lun_name]:
            self.validate_ovf_contents(
                disk_name=disk, vm_name=self.vm_name,
                storage_domain=self.storage_domain, positive=False
            )


class TestCase6254(BasicEnvironment):
    """
    Delete a disk from a VM

    1. Create a VM with a disk, ensure the OVF is created on this storage
    domain
    2. Delete the disk from the VM, ensure that the OVF remains for this VM
    but the disk alias no longer exists as part of the OVF file contents

    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/
    workitem?id=RHEVM3-6254
    """
    __test__ = True
    polarion_test_case = '6254'

    @polarion("RHEVM3-6254")
    @tier2
    def test_delete_disk_from_vm(self):
        """ Polarion case 6254 """
        ll_sd.update_ovf_store(self.storage_domain)
        self.validate_ovf_contents(
            disk_name=self.disk_name, vm_name=self.vm_name,
            storage_domain=self.storage_domain,
        )

        testflow.step(
            "Remove disk %s from VM %s", self.disk_name, self.vm_name
        )
        assert ll_disks.deleteDisk(True, self.disk_name), (
            "Failed to remove disk %s" % self.disk_name
        )

        testflow.step(
            "Validate the OVF store contents for VM '%s'", self.vm_name
        )
        ll_sd.update_ovf_store(self.storage_domain)
        self.validate_ovf_contents(
            disk_name=self.disk_name, vm_name=self.vm_name,
            storage_domain=self.storage_domain, positive=False
        )


class TestCase6255(BasicEnvironment):
    """
    Remove a VM

    1. Create a VM with a disk, ensure the OVF is created on this storage
    domain
    2. Remove the VM, ensure the OVF is removed for this VM

    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/
    workitem?id=RHEVM3-6255
    """
    __test__ = True
    polarion_test_case = '6255'

    @polarion("RHEVM3-6255")
    @tier2
    def test_remove_vm(self):
        """ Polarion case 6255 """
        vm_id = ll_vms.get_vm_obj(self.vm_name).get_id()

        ll_sd.update_ovf_store(self.storage_domain)
        self.validate_ovf_contents(
            vm_name=self.vm_name, vm_id=vm_id, disk_name=self.disk_name,
            storage_domain=self.storage_domain
        )

        testflow.step("Remove VM %s", self.vm_name)
        assert ll_vms.safely_remove_vms([self.vm_name]), (
            "Failed to remove VM %s" % self.vm_name
        )

        testflow.step(
            "Validate the OVF store contents for VM '%s'",
            self.vm_name
        )
        ll_sd.update_ovf_store(self.storage_domain)
        test_utils.wait_for_tasks(config.ENGINE, config.DATA_CENTER_NAME)
        self.validate_ovf_contents(
            vm_name=self.vm_name, vm_id=vm_id, disk_name=self.disk_name,
            storage_domain=self.storage_domain, positive=False,
            should_ovf_exist=False
        )


class TestCase6256(EnvironmentWithDisklessVm):
    """
    Diskless VM

    1. Create a VM with no disks, ensure that the OVF is created on all
    storage domains (pick any domain within the current storage type,
    no need to check across all storage domains)

    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/
    workitem?id=RHEVM3-6256
    """
    __test__ = True
    polarion_test_case = '6256'

    @polarion("RHEVM3-6256")
    @tier2
    def test_diskless_vm(self):
        """ Polarion case 6256 """
        vm_id = ll_vms.get_vm_obj(self.vm_name).get_id()
        sd_id = ll_sd.get_storage_domain_obj(self.storage_domain).get_id()
        self.is_block_storage = (
            True if self.storage in config.BLOCK_TYPES else False
        )
        ll_sd.update_ovf_store(self.storage_domain)
        self.ovf_store = helpers.get_first_ovf_store_id_and_obj(
            self.storage_domain
        )

        testflow.step(
            "Extract and return the contents of the OVF store containing "
            "the disk"
        )
        for ovf_file_content in TimeoutingSampler(
            timeout=config.FIND_OVF_INFO_TIMEOUT,
            sleep=config.FIND_OVF_INFO_SLEEP,
            func=self.get_ovf_contents_or_num_ovf_files, disk=None,
            vm=self.vm_name, vm_or_template_id=vm_id, sd_id=sd_id,
            template=None, ovf_should_exist=True, get_content=True
        ):
            if ovf_file_content is not None:
                break

        logger.info("Ensure that the VM's OVF file contains the VM name")
        assert config.OBJECT_NAME_IN_OVF % self.vm_name in ovf_file_content


@pytest.mark.usefixtures(
    initalize_vm_to_remove.__name__,
)
class TestCase6257(EnvironmentWithDisklessVm):
    """
    Check tar file after VM name change

    1. Create a VM with no disks
    2. Modify the VM's name and ensure that the OVF is updated reflecting
    this change

    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/
    workitem?id=RHEVM3-6257
    """
    __test__ = True
    polarion_test_case = '6257'
    new_vm_name = "storage_ovf_renamed_vm"

    @polarion("RHEVM3-6257")
    @tier3
    def test_tar_file_on_vdsm_for_vm_name_change(self):
        """ Polarion case 6257 """
        ll_sd.update_ovf_store(self.storage_domain)
        testflow.step(
            "Extract and return the contents of the OVF store containing the "
            "VM"
        )
        for ovf_file_content in TimeoutingSampler(
            timeout=config.FIND_OVF_INFO_TIMEOUT,
            sleep=config.FIND_OVF_INFO_SLEEP,
            func=self.get_ovf_contents_or_num_ovf_files, disk=None,
            vm=self.vm_name, vm_or_template_id=self.vm_id,
            sd_id=self.sd_id, template=None, ovf_should_exist=True,
            get_content=True
        ):
            if ovf_file_content is not None and (
                config.OBJECT_NAME_IN_OVF % self.vm_name in ovf_file_content
            ):
                break

        logger.info("Ensure that the VM's OVF file contains the VM name")
        assert config.OBJECT_NAME_IN_OVF % self.vm_name in ovf_file_content, (
            "VM name '%s' doesn't exist in the OVF file" % self.vm_name
        )

        testflow.step("Update VM %s name", self.vm_name)
        assert ll_vms.updateVm(True, self.vm_name, name=self.new_vm_name), (
            "Failed to update VM %s" % self.vm_name
        )

        ll_sd.update_ovf_store(self.storage_domain)
        logger.info(
            "Extract and return the contents of the OVF store containing the "
            "VM"
        )
        for ovf_file_content in TimeoutingSampler(
            timeout=config.FIND_OVF_INFO_TIMEOUT,
            sleep=config.FIND_OVF_INFO_SLEEP,
            func=self.get_ovf_contents_or_num_ovf_files, disk=None,
            vm=self.new_vm_name, vm_or_template_id=self.vm_id,
            sd_id=self.sd_id, template=None, ovf_should_exist=True,
            get_content=True
        ):
            if ovf_file_content is not None and (
                config.OBJECT_NAME_IN_OVF % self.vm_name not in
                ovf_file_content
            ):
                break

        logger.info("Ensure that the VM's OVF file contains the VM name")
        assert (
            config.OBJECT_NAME_IN_OVF % self.vm_name not in ovf_file_content
        ), (
                "Original VM name '%s' still exists in the updated OVF file" %
                self.vm_name
            )
        assert (
            config.OBJECT_NAME_IN_OVF % self.new_vm_name in ovf_file_content
        ), (
            "Updated VM name '%s' does not exist in the updated OVF file" %
            self.new_vm_name
        )


class TestCase6259(BasicEnvironment):
    """
    Restore a VM from configuration

    1. Create a VM with a single disk, ensure that the OVF is created on the
    disk's storage domain
    2. Remove VM, ensuring that its OVF file is removed
    3. Create a new VM with a single disk
    4. Attach the OVF_store where the previous VM originally resided
    5. Attempt to run RestoreVmFromConfiguration which should restore the
    original VM

    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/
    workitem?id=RHEVM3-6259
    """
    # TODO: Mounting the OVF store as a disk isn't supported until version 4.0
    __test__ = False
    polarion_test_case = '6259'

    @polarion("RHEVM3-6259")
    @tier2
    def test_restore_vm_from_ovf_store(self):
        """ Polarion case 6259 """
        # TODO: Add code once support for mounting OVF store exists


@pytest.mark.usefixtures(
    initialize_template_params.__name__,
    remove_template.__name__,
)
class TestCase6260(BasicEnvironment):
    """
    OVF of a template

    1. Create a VM with a disk, ensure the OVF is created on this storage
    domain
    2. Create a template from this VM, ensure that a new OVF is created
    reflecting the Template created

    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/
    workitem?id=RHEVM3-6260
    """
    __test__ = True
    polarion_test_case = '6260'

    @polarion("RHEVM3-6260")
    @tier2
    def test_ovf_for_a_template(self):
        """ Polarion case 6260 """
        ll_sd.update_ovf_store(self.storage_domain)
        self.validate_ovf_contents(
            disk_name=self.disk_name, vm_name=self.vm_name,
            storage_domain=self.storage_domain
        )

        testflow.step("Create template from VM %s", self.vm_name)
        assert ll_templates.createTemplate(
            True, name=self.template_name, vm=self.vm_name,
            storagedomain=self.storage_domain
        ), "Failed to create Template '%s'" % self.template_name
        ll_templates.wait_for_template_disks_state(self.template_name)

        testflow.step(
            "Validate the OVF store contents for template '%s'",
            self.template_name
        )
        ll_sd.update_ovf_store(self.storage_domain)
        self.validate_ovf_contents(
            disk_name=self.disk_name, template_name=self.template_name,
            storage_domain=self.storage_domain
        )


@pytest.mark.usefixtures(
    set_ovf_store_count.__name__,
    initialize_new_disk_params.__name__,
    remove_ovf_store_disks.__name__,
)
class TestCase6261(BasicEnvironment):
    """
    Change the number of OVF_STORE disks

    1. Update the number of the OVF_STORE disks
    2. Create a VM with a disk, ensure the OVF is created on each of the
    OVF stores that are assigned to the storage domain, matching the updated
    number specified

    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/
    workitem?id=RHEVM3-6261
    """
    __test__ = True
    polarion_test_case = '6261'

    @polarion("RHEVM3-6261")
    @tier2
    def test_change_ovf_store_count(self):
        """ Polarion case 6261 """
        sd_list = [self.storage_domain, self.storage_domain_1]
        for sd in sd_list:
            ll_sd.deactivateStorageDomain(
                True, config.DATA_CENTER_NAME, sd
            )
            ll_sd.activateStorageDomain(
                True, config.DATA_CENTER_NAME, sd
            )
        logger.info(
            "Ensure that OVF store count is %s after the engine "
            "configuration change", config.UPDATED_NUM_OVF_STORES_PER_SD
        )
        for num_ovf_store_disks_sd_0 in TimeoutingSampler(
            timeout=config.FIND_OVF_DISKS_TIMEOUT,
            sleep=config.FIND_OVF_DISKS_SLEEP,
            func=ll_sd.get_number_of_ovf_store_disks,
            storage_domain=self.storage_domain
        ):
            if (num_ovf_store_disks_sd_0) == (
                config.UPDATED_NUM_OVF_STORES_PER_SD
            ):
                break
        assert (num_ovf_store_disks_sd_0) == (
            config.UPDATED_NUM_OVF_STORES_PER_SD
        ), (
            "The number of OVF stores in domain '%s' isn't %s after the "
            "engine configuration change" %
            self.storage_domain, config.UPDATED_NUM_OVF_STORES_PER_SD
        )

        for num_ovf_store_disks_sd_1 in TimeoutingSampler(
            timeout=config.FIND_OVF_DISKS_TIMEOUT,
            sleep=config.FIND_OVF_DISKS_SLEEP,
            func=ll_sd.get_number_of_ovf_store_disks,
            storage_domain=self.storage_domain_1
        ):
            if (num_ovf_store_disks_sd_1) == (
                config.UPDATED_NUM_OVF_STORES_PER_SD
            ):
                break
        assert (num_ovf_store_disks_sd_1) == (
            config.UPDATED_NUM_OVF_STORES_PER_SD
        ), (
            "The number of OVF stores in domain '%s' isn't %s after the "
            "engine configuration change" %
            (self.storage_domain_1, config.UPDATED_NUM_OVF_STORES_PER_SD)
        )

        assert storage_helpers.add_new_disk(
            self.storage_domain_1, self.disk_args, self.storage
        ), "Failed to add new disk %s" % self.new_disk_name
        ll_disks.wait_for_disks_status([self.new_disk_name])

        disk_names = [self.disk_name, self.new_disk_name]

        ll_disks.attachDisk(True, self.new_disk_name, self.vm_name)

        testflow.step(
            "Validate the OVF store contents for VM '%s'",
            self.vm_name
        )
        for disk, sd in zip(disk_names, sd_list):
            ll_sd.update_ovf_store(sd)
            self.validate_ovf_contents(
                disk_name=disk, vm_name=self.vm_name, storage_domain=sd
            )


@pytest.mark.usefixtures(
    initialize_template_params.__name__,
    initialize_vm_pool_name.__name__,
    remove_template.__name__,
    remove_vms_pool.__name__,
)
class TestCase6262(BasicEnvironment):
    """
    Large number of OVFs

    1. Create a VM with a disk, ensure the OVF is created on this storage
    domain
    2. Create a template from this VM, ensure that a new OVF is created
    reflecting the Template created
    3. Create a pool of 5 from this template, ensure that the OVF counts
    reflect this newly created pool

    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/
    workitem?id=RHEVM3-6262
    """
    __test__ = True
    polarion_test_case = '6262'

    @polarion("RHEVM3-6262")
    @tier3
    def test_ovf_for_a_template(self):
        """ Polarion case 6262 """
        ll_sd.update_ovf_store(self.storage_domain)
        self.validate_ovf_contents(
            vm_name=self.vm_name, disk_name=self.disk_name,
            storage_domain=self.storage_domain
        )

        testflow.step(
            "Create template from VM %s and watch OVF processing", self.vm_name
        )
        assert ll_templates.createTemplate(
            True, name=self.template_name, vm=self.vm_name,
            storagedomain=self.storage_domain
        ), "Failed to createTemplate '%s'" % self.template_name
        ll_templates.wait_for_template_disks_state(self.template_name)

        logger.info(
            "Validate the OVF store contents for template '%s'",
            self.template_name
        )
        ll_sd.update_ovf_store(self.storage_domain)
        self.validate_ovf_contents(
            disk_name=self.disk_name, template_name=self.template_name,
            storage_domain=self.storage_domain
        )
        num_ovf_files_with_template = (
            self.retrieve_number_of_ovf_files_from_ovf_store(
                template_name=self.template_name
            )
        )

        logger.info("Create a VM pool with 5 VMs from the created template")
        assert ll_vmpools.addVmPool(
            True, name=self.pool_name, size=config.POOL_SIZE,
            cluster=config.CLUSTER_NAME, template=self.template_name,
            description=config.POOL_DESCRIPTION
        ), "Failed to add VM pool '%s' using template '%s'" % (
            config.POOL_NAME, self.template_name
        )
        logger.info(
            "Wait until all VMs in the pool have been created successfully"
        )
        test_utils.wait_for_tasks(config.ENGINE, config.DATA_CENTER_NAME)
        logger.info(
            "Allow a bit over a minute for all the VMs created from the pool "
            "to be written into the OVF store"
        )
        ll_sd.update_ovf_store(self.storage_domain)
        for num_ovf_files_with_vm_pool in TimeoutingSampler(
            timeout=config.FIND_OVF_DISKS_TIMEOUT,
            sleep=config.FIND_OVF_DISKS_SLEEP,
            func=self.retrieve_number_of_ovf_files_from_ovf_store,
            template_name=self.template_name
        ):
            if num_ovf_files_with_vm_pool == (
                num_ovf_files_with_template + config.POOL_SIZE
            ):
                break
        assert num_ovf_files_with_vm_pool == (
            num_ovf_files_with_template + config.POOL_SIZE
        ), (
            "The number of OVF stores in domain '%s' hasn't increased by the "
            "%s VMs added in the VM pool after the Data center upgrade" %
            (self.storage_domain, config.POOL_SIZE)
        )
