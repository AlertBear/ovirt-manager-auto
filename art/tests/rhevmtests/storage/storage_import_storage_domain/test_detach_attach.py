"""
3.5 - Import Storage Domain
https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
Storage/3_5_Storage_ImportDomain_DetachAttach
3.5 - Import Storage Domain Between Different Setups
https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
Storage/3_5_Storage_ImportDomain_Between_DifferentSetups
"""
import logging
import config
from rhevmtests import helpers as rhevm_helpers
from rhevmtests.storage import helpers as storage_helpers
from art.rhevm_api.tests_lib.high_level import (
    storagedomains as hl_sd,
)
from art.rhevm_api.tests_lib.low_level import (
    datacenters as ll_dc,
    hosts as ll_hosts,
    jobs as ll_jobs,
    storagedomains as ll_sd,
    vms as ll_vms,
)
from art.rhevm_api.utils import test_utils
from art.test_handler.settings import ART_CONFIG
from art.test_handler.tools import bz, polarion
from art.unittest_lib import (
    tier2,
    tier3,
    tier4,
)
from art.unittest_lib import StorageTest as BaseTestCase
from rhevmtests.storage.fixtures import (
    create_dc, clean_dc, create_template, remove_vm, add_disk, attach_disk,
    create_vm, create_snapshot, remove_vms, clean_mount_point, storage_cleanup,
    clone_vm_from_template, copy_golden_template_disk,
)
from fixtures import (
    secure_deactivate_and_detach_storage_domain, remove_storage_domain_fin,
    secure_deactivate_storage_domain, deactivate_detach_and_remove_domain_fin,
    add_master_storage_domain_to_new_dc, create_gluster_or_posix_export_domain,
    initialize_params, add_non_master_storage_domain_to_new_dc,
    add_non_master_storage_domain, remove_template_setup, create_vm_func_lvl,
    remove_storage_domain_setup, attach_and_activate_storage_domain,
    attach_disk_to_cloned_vm, delete_snapshot_setup, initialize_disk_params,
    block_connection_to_sd, unblock_connection_to_sd, wait_for_dc_state,
)
from art.unittest_lib.common import testflow
import pytest

logger = logging.getLogger(__name__)

ENUMS = config.ENUMS
ISCSI = config.STORAGE_TYPE_ISCSI
FCP = config.STORAGE_TYPE_FCP
NFS = config.STORAGE_TYPE_NFS
GLUSTER = config.STORAGE_TYPE_GLUSTER
POSIX = config.STORAGE_TYPE_POSIX
CEPH = config.STORAGE_TYPE_CEPH


@pytest.mark.usefixtures(
    initialize_params.__name__,
    storage_cleanup.__name__,
)
class BasicEnvironment(BaseTestCase):
    """
    This class implements setup and teardowns of common things
    """
    # TODO: Run only on rest:
    # https://projects.engineering.redhat.com/browse/RHEVM-1654
    # https://bugzilla.redhat.com/show_bug.cgi?id=1223448
    __test__ = False


@pytest.mark.usefixtures(
    add_non_master_storage_domain.__name__,
    deactivate_detach_and_remove_domain_fin.__name__,
    create_vm.__name__,
)
class DomainImportWithTemplate(BasicEnvironment):
    """
    Create vm from imported domain's Template
    """
    vm_name = 'vm_from_temp'
    vm_created = False
    remove_param = {'format': 'false'}
    partial_import = None

    def new_vm_from_imported_domain_template(self):
        """
        - import data domain
        - verify template's existence
        - create VM from template
        """
        testflow.step("Import storage domain %s", self.non_master)
        storage_helpers.import_storage_domain(self.host, self.storage)
        testflow.step(
            "Attach storage domain %s to date-center %s",
            self.non_master, config.DATA_CENTER_NAME
        )
        hl_sd.attach_and_activate_domain(
            config.DATA_CENTER_NAME, self.non_master
        )
        ll_jobs.wait_for_jobs([config.JOB_ACTIVATE_DOMAIN])
        unregistered_templates = ll_sd.get_unregistered_templates(
            self.non_master
        )
        template_names = [
            template.get_name() for template in unregistered_templates
        ]
        logger.info("Unregistered templates: %s", template_names)
        template_to_register = [
            template for template in unregistered_templates if (
                template.get_name() == self.template_name
            )
        ]
        testflow.step(
            "Registering template: %s", template_to_register[0].get_name()
        )
        self.template_exists = ll_sd.register_object(
            template_to_register[0], cluster=config.CLUSTER_NAME,
            partial_import=self.partial_import
        )
        assert self.template_exists, "Template registration failed"
        testflow.step(
            "Clone VM %s from template: %s",
            self.vm_name, template_to_register[0].get_name()
        )
        assert ll_vms.safely_remove_vms([self.vm_name])
        assert ll_vms.cloneVmFromTemplate(
            positive=True, name=self.vm_name,
            template=self.template_name, cluster=config.CLUSTER_NAME
        ), "Unable to create vm %s from template %s" % (
            self.vm_name, self.template_name
        )


@pytest.mark.usefixtures(
    add_non_master_storage_domain.__name__,
    deactivate_detach_and_remove_domain_fin.__name__,
    create_vm.__name__,
    create_snapshot.__name__,
    secure_deactivate_and_detach_storage_domain.__name__,
    remove_vms.__name__
)
class TestCase5300(BasicEnvironment):
    """
    Import domain, preview snapshots and create vm from a snapshot
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/
    workitem?id=RHEVM3-5300
    """
    __test__ = True
    polarion_test_case = '5300'
    snapshot_description = 'snap_5300'
    cloned_vm = 'cloned_vm_5300'
    previewed = False
    vm_names = list()

    @polarion("RHEVM3-5300")
    @tier2
    def test_detach_attach_new_domain(self):
        """
        - create vm + disk
        - install OS, create snapshot
        - detach the domain
        - attach data domain and register the vm
        - verify snapshot exists
        - preview snapshot
        - create vm from snapshot
        """
        testflow.step("Attaching storage domain %s", self.non_master)
        hl_sd.attach_and_activate_domain(
            config.DATA_CENTER_NAME, self.non_master
        )
        ll_jobs.wait_for_jobs([config.JOB_ACTIVATE_DOMAIN])

        unregistered_vms = ll_sd.get_unregistered_vms(self.non_master)
        vm_names = [vm.get_name() for vm in unregistered_vms]
        vms_to_register = [
            vm for vm in unregistered_vms if vm.get_name() == self.vm_name
        ]

        testflow.step("Unregistered vms: %s", vm_names)
        assert ll_sd.register_object(
            vms_to_register[0], cluster=config.CLUSTER_NAME
        )
        ll_jobs.wait_for_jobs([config.JOB_REGISTER_DISK])

        assert self.snapshot_description in [
            snap.get_description() for snap in ll_vms.get_vm_snapshots(
                self.vm_name
            )
        ]
        testflow.step("Preview snapshot %s", self.snapshot_description)
        self.previewed = ll_vms.preview_snapshot(
            True, self.vm_name, self.snapshot_description, ensure_vm_down=True
        )
        ll_vms.wait_for_vm_snapshots(
            self.vm_name, config.SNAPSHOT_IN_PREVIEW, self.snapshot_description
        )
        assert self.previewed
        testflow.step("Undo snapshot Preview for %s", self.vm_name)
        ll_vms.undo_snapshot_preview(True, self.vm_name)
        ll_jobs.wait_for_jobs([config.JOB_RESTORE_SNAPSHOT])
        ll_vms.wait_for_vm_snapshots(self.vm_name, config.SNAPSHOT_OK)
        self.previewed = False

        testflow.step(
            "Creating vm %s from snapshot %s", self.cloned_vm,
            self.snapshot_description
        )
        assert ll_vms.cloneVmFromSnapshot(
            True, name=self.cloned_vm, cluster=config.CLUSTER_NAME,
            vm=self.vm_name, snapshot=self.snapshot_description,
            storagedomain=self.non_master,
        )
        vm_names.append(self.cloned_vm)


@pytest.mark.usefixtures(
    add_non_master_storage_domain.__name__,
    wait_for_dc_state.__name__,
)
class TestCase5302(BasicEnvironment):
    """
    IP block during import domain
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/
    workitem?id=RHEVM3-5302
    """
    __test__ = True
    polarion_test_case = '5302'
    imported = False
    block_dest = dict()

    @polarion("RHEVM3-5302")
    @tier4
    def test_block_connection_during_import(self):
        """
        - verify that there are no IP blocks from vdsm->engine
          or engine->vdsm
        - import data domain to another DC
        - during the operation add IP block from host to engine's IP
        """
        logger.info('Checking if domain %s is attached to dc %s',
                    self.non_master, config.DATA_CENTER_NAME)

        host_obj = rhevm_helpers.get_host_resource(
            self.host_ip, config.HOSTS_PW
        )
        non_master_domains = ll_sd.findNonMasterStorageDomains(
            True, config.DATA_CENTER_NAME
        )[1]['nonMasterDomains']
        self.block_dest['address'] = [config.VDC]

        if self.non_master not in [sd for sd in non_master_domains]:
            logger.info(
                'Attaching domain %s to dc %s' % (
                    self.non_master, config.DATA_CENTER_NAME
                )
            )
            ll_sd.attachStorageDomain(
                True, config.DATA_CENTER_NAME, self.non_master, wait=False
            )
            assert host_obj.firewall.chain('OUTPUT').add_rule(
                self.block_dest, 'DROP'
            )

        non_master_domains = ll_sd.findNonMasterStorageDomains(
            True, config.DATA_CENTER_NAME
        )
        if self.non_master in [sd for sd in non_master_domains]:
            self.imported = True
            # TODO: Expected results are not clear

        host_obj.firewall.chain('OUTPUT').delete_rule(self.block_dest, 'DROP')


@pytest.mark.usefixtures(
    add_non_master_storage_domain.__name__,
    deactivate_detach_and_remove_domain_fin.__name__,
    create_vm.__name__,
    secure_deactivate_and_detach_storage_domain.__name__,
)
class TestCase5193(BasicEnvironment):
    """
    test mounted meta-data files when attaching a file domain
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/
    workitem?id=RHEVM3-5193
    """
    __test__ = NFS in ART_CONFIG['RUN']['storages']
    polarion_test_case = '5193'
    storages = set([NFS, GLUSTER])

    @polarion("RHEVM3-5193")
    @tier3
    def test_attach_file_domain(self):
        """
        - detach an nfs domain
        - attach an nfs domain on different dc
        - register the vms
        """
        testflow.step("Attaching storage domain %s", self.non_master)
        hl_sd.attach_and_activate_domain(
            config.DATA_CENTER_NAME, self.non_master
        )
        ll_jobs.wait_for_jobs([config.JOB_ACTIVATE_DOMAIN])

        unregistered_vms = ll_sd.get_unregistered_vms(self.non_master)
        vm_names = [vm.get_name() for vm in unregistered_vms]
        vms_to_register = [
            vm for vm in unregistered_vms if vm.get_name() == self.vm_name
        ]
        testflow.step("Unregistered vms: %s", vm_names)
        assert ll_sd.register_object(
            vms_to_register[0], cluster=config.CLUSTER_NAME
        )
        ll_jobs.wait_for_jobs([config.JOB_REGISTER_DISK])


@pytest.mark.usefixtures(
    add_non_master_storage_domain.__name__,
    deactivate_detach_and_remove_domain_fin.__name__,
    create_vm.__name__,
    secure_deactivate_and_detach_storage_domain.__name__,
)
class TestCase5194(BasicEnvironment):
    """
    test lv's existence when importing a block domain
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/
    workitem?id=RHEVM3-5194
    """
    __test__ = (ISCSI in ART_CONFIG['RUN']['storages'] or
                FCP in ART_CONFIG['RUN']['storages'])
    storages = set([ISCSI, FCP])
    polarion_test_case = '5194'

    @polarion("RHEVM3-5194")
    @tier3
    def test_lv_exists_after_import_block_domain(self):
        """
        - detach block domain
        - attach the block domain to different dc (execute lvs,vgs)
        - register vms and disks
        """
        testflow.step("Attaching storage domain %s", self.non_master)
        hl_sd.attach_and_activate_domain(
            config.DATA_CENTER_NAME, self.non_master
        )
        ll_jobs.wait_for_jobs([config.JOB_ACTIVATE_DOMAIN])

        unregistered_vms = ll_sd.get_unregistered_vms(self.non_master)
        vm_names = [vm.get_name() for vm in unregistered_vms]
        vms_to_register = [
            vm for vm in unregistered_vms if vm.get_name() == self.vm_name
        ]
        testflow.step("Unregistered vms: %s", vm_names)
        assert ll_sd.register_object(
            vms_to_register[0], cluster=config.CLUSTER_NAME
        ), "Failed to register vm %s" % vms_to_register[0]
        ll_jobs.wait_for_jobs([config.JOB_REGISTER_DISK])
        testflow.step("Start VM %s", self.vm_name)
        assert ll_vms.startVms(
            [self.vm_name], wait_for_status=config.VM_UP
        ), "VM %s failed to restart" % self.vm_name


@pytest.mark.usefixtures(
    add_non_master_storage_domain.__name__,
    deactivate_detach_and_remove_domain_fin.__name__,
    secure_deactivate_and_detach_storage_domain.__name__
)
class TestCase5205(BasicEnvironment):
    """
    detach/attach domain during vdsm/engine restart
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/
    workitem?id=RHEVM3-5205
    """
    __test__ = True
    polarion_test_case = '5205'

    def _restart_component(self, restart_function, *args):
        logger.info(
            'Checking if domain %s is attached to dc %s' % (
                self.non_master, config.DATA_CENTER_NAME
            )
        )

        non_master_domains = ll_sd.findNonMasterStorageDomains(
            True, config.DATA_CENTER_NAME
        )

        if self.non_master not in [
            sd['nonMasterDomains'] for sd in non_master_domains
        ]:
            logger.info(
                'Attaching domain %s to dc %s' % (
                    self.non_master, config.DATA_CENTER_NAME
                )
            )
            ll_sd.attachStorageDomain(
                True, config.DATA_CENTER_NAME, self.non_master, wait=False,
                compare=False
            )

            assert restart_function(*args)
            ll_dc.waitForDataCenterState(config.DATA_CENTER_NAME)

        non_master_domains = ll_sd.findNonMasterStorageDomains(
            True, config.DATA_CENTER_NAME
        )
        self.imported = self.non_master in [
            sd['nonMasterDomains'] for sd in non_master_domains
        ]

    @polarion("RHEVM3-5205")
    @tier4
    def test_restart_vdsm_during_import_domain(self):
        """
        - import data domain on different dc
        - during the operation restart vdsm
        """
        self._restart_component(
            test_utils.restartVdsmd, config.HOSTS[0], config.HOSTS_PW
        )

    @polarion("RHEVM3-5205")
    @tier4
    def test_restart_engine_during_import_domain(self):
        """
        - import data domain on different dc
        - Restart the engine during the Import domain operation
        """
        self._restart_component(
            test_utils.restart_engine, config.ENGINE, 10, 300
        )


@pytest.mark.usefixtures(
    add_non_master_storage_domain.__name__,
    deactivate_detach_and_remove_domain_fin.__name__,
    secure_deactivate_and_detach_storage_domain.__name__
)
class TestCase5304(BasicEnvironment):
    """
    Import domain during host reboot
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/
    workitem?id=RHEVM3-5304
    """
    __test__ = True
    polarion_test_case = '5304'

    @polarion("RHEVM3-5304")
    @tier4
    def test_reboot_host_during_import_domain(self):
        """
        - Import data domain to different dc
        - Reboot host during the Import domain operation
        """
        logger.info('Checking if domain %s is attached to dc %s'
                    % (self.non_master, config.DATA_CENTER_NAME))

        non_master_domains = ll_sd.findNonMasterStorageDomains(
            True, config.DATA_CENTER_NAME
        )

        if self.non_master not in [
            sd['nonMasterDomains'] for sd in non_master_domains
        ]:
            logger.info(
                'Attaching domain %s to dc %s' % (
                    self.non_master, config.DATA_CENTER_NAME
                )
            )
            ll_sd.attachStorageDomain(
                True, config.DATA_CENTER_NAME, self.non_master, wait=False
            )

        assert ll_hosts.reboot_host(host=config.VDS_HOSTS[0])
        ll_dc.waitForDataCenterState(config.DATA_CENTER_NAME)

        non_master_domains = ll_sd.findNonMasterStorageDomains(
            True, config.DATA_CENTER_NAME
        )
        self.imported = self.non_master in [
            sd['nonMasterDomains'] for sd in non_master_domains
        ]
        assert not self.imported, "Storage domain %s was imported" % (
            self.non_master
        )


@pytest.mark.usefixtures(
    add_non_master_storage_domain.__name__,
    remove_storage_domain_fin.__name__,
    clean_dc.__name__,
    create_vm.__name__,
    create_dc.__name__,

)
class BaseCaseInitializeDataCenter(BasicEnvironment):
    """
    Base class for initializing a data center with an imported domain
    """
    remove_param = None

    def execute_flow(self):
        """
        Import the data domain
        """
        testflow.step("Import storage-domain %s", self.non_master)
        status = False
        if self.storage == ISCSI:
            status = hl_sd.import_iscsi_storage_domain(
                self.host,
                lun_address=config.ISCSI_DOMAINS_KWARGS[0]['lun_address'],
                lun_target=config.ISCSI_DOMAINS_KWARGS[0]['lun_target']
            )

        elif self.storage == FCP:
            status = hl_sd.import_fcp_storage_domain(self.host)

        elif self.storage == NFS:
            status = ll_sd.importStorageDomain(
                True, config.TYPE_DATA, NFS,
                config.NFS_DOMAINS_KWARGS[0]['address'],
                config.NFS_DOMAINS_KWARGS[0]['path'], self.host
            )
        elif self.storage == GLUSTER:
            status = ll_sd.importStorageDomain(
                True, config.TYPE_DATA, GLUSTER,
                config.GLUSTER_DOMAINS_KWARGS[0]['address'],
                config.GLUSTER_DOMAINS_KWARGS[0]['path'], self.host,
                vfs_type=config.ENUMS['vfs_type_glusterfs']
            )
        assert status, "Failed to import storage domain"


@pytest.mark.usefixtures(
    secure_deactivate_and_detach_storage_domain.__name__,
    remove_storage_domain_setup.__name__,
)
class TestCase5201(BaseCaseInitializeDataCenter):
    """
    Initialize DC from an unattached imported domain
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/
    workitem?id=RHEVM3-5201
    """
    __test__ = True
    polarion_test_case = '5201'

    remove_param = {'format': 'false'}

    @polarion("RHEVM3-5201")
    @tier2
    def test_initialize_dc_with_imported_domain(self):
        """
        - Configure 2 DCs: DC1 with 2 storage domains
          and DC2 without a storage domain
        - Create a VM with a disk on the non-master domain in DC1
        - Detach the domain which holds the disk from DC1
        - Remove it from the setup
        - Import it back again
        - Attach the domain to DC2 as the first domain (initialize DC)
        - Import the VM to DC2
        """
        self.execute_flow()
        testflow.step("Attaching storage domain %s", self.non_master)
        hl_sd.attach_and_activate_domain(self.new_dc_name, self.non_master)
        ll_jobs.wait_for_jobs([config.JOB_ACTIVATE_DOMAIN])

        unregistered_vms = ll_sd.get_unregistered_vms(self.non_master)
        vm_names = [vm.get_name() for vm in unregistered_vms]
        vms_to_register = [
            vm for vm in unregistered_vms if vm.get_name() == self.vm_name
        ]
        logger.info("Unregistered vms: %s", vm_names)
        testflow.step("Register VM: %s", vm_names[0])

        assert ll_sd.register_object(
            vms_to_register[0], cluster=self.cluster_name
        ), "Unable to register vm %s in cluster %s" % (
            (vms_to_register[0], self.cluster_name)
        )
        ll_jobs.wait_for_jobs([config.JOB_REGISTER_DISK])
        testflow.step("Start VM %s", self.vm_name)
        assert ll_vms.startVm(
            True, self.vm_name, wait_for_status=config.VM_UP
        ), "VM %s failed to restart" % self.vm_name


@pytest.mark.usefixtures(
    secure_deactivate_storage_domain.__name__,
    remove_storage_domain_setup.__name__,
    clean_mount_point.__name__
)
class TestCase12207(BaseCaseInitializeDataCenter):
    """
    Initialize DC from a destroyed domain
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/
    workitem?id=RHEVM3-12207
    """
    __test__ = True
    polarion_test_case = '12207'
    remove_param = {'destroy': True, 'format': 'false'}
    destroy = True

    @polarion("RHEVM3-12207")
    @tier2
    def test_initialize_dc_with_destroyed_domain(self):
        """
        - Configure 2 DCs: DC1 with 2 storage domains
          and DC2 without a storage domain
        - Create a VM with a disk on the non-master domain in DC1
        - Deactivate and Destroy the domain which holds the disk from DC1
        - Import it back again
        - Attach the domain to DC2 as the first domain (initialize DC)
        """
        self.execute_flow()
        testflow.step("Attaching storage domain %s", self.non_master)
        hl_sd.attach_and_activate_domain(self.new_dc_name, self.non_master)
        ll_jobs.wait_for_jobs([config.JOB_ACTIVATE_DOMAIN])
        # set remove_param for fin_remove_storage_domain
        self.remove_param = {'format': 'true'}


@pytest.mark.usefixtures(
    secure_deactivate_and_detach_storage_domain.__name__,
    create_gluster_or_posix_export_domain.__name__,
)
class TestCase10951(BasicEnvironment):
    """
    Import an export domain to the system

    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/
    workitem?id=RHEVM3-10951
    """
    __test__ = (POSIX in ART_CONFIG['RUN']['storages'] or
                GLUSTER in ART_CONFIG['RUN']['storages'])
    storages = set([GLUSTER, POSIX])
    polarion_test_case = '10951'
    nfs_version = None
    vfs_type = None
    storage_type = None
    sd_type = ENUMS['storage_dom_type_export']
    domain_to_detach = config.EXPORT_DOMAIN_NAME

    @polarion("RHEVM3-10951")
    @tier2
    def test_import_existing_export_domain(self):
        """
        - Import existing export storage domain
        - Attach it to the data center
        """
        testflow.step("Import export domain %s", self.export_domain)
        assert ll_sd.importStorageDomain(
            True, self.sd_type, self.storage_type, self.export_address,
            self.export_path, self.host, nfs_version=self.nfs_version,
            vfs_type=self.vfs_type
        ), "Unable to import export domain %s" % self.export_domain
        testflow.step("Attaching storage domain %s", self.export_domain)
        assert hl_sd.attach_and_activate_domain(
            config.DATA_CENTER_NAME, self.export_domain
        ), "Unable to attach export domain %s" % self.export_domain
        ll_jobs.wait_for_jobs([config.JOB_ACTIVATE_DOMAIN])


@pytest.mark.usefixtures(
    create_dc.__name__,
    add_master_storage_domain_to_new_dc.__name__,
    remove_storage_domain_fin.__name__,
    add_non_master_storage_domain_to_new_dc.__name__,
    deactivate_detach_and_remove_domain_fin.__name__,
    create_vm.__name__,
    secure_deactivate_and_detach_storage_domain.__name__,
    clean_dc.__name__,
)
class BaseTestCase5192(BasicEnvironment):
    """
    Attach storage domain from older version into 4.1 data center
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/
    workitem?id=RHEVM3-5192
    """
    polarion_test_case = '5192'
    dc_version = None
    vm_args = {'clone_from_template': False}

    @polarion("RHEVM3-5192")
    @tier3
    def test_attach_from_older_version(self):
        """
        Configure two data centers, one dc_verion and other > 3.6
        Detach dc_version storage domain and attach it to > 3.6 data center and
        register the vms
        """
        testflow.step("Attaching storage domain %s", self.non_master)
        if hl_sd.attach_and_activate_domain(
            config.DATA_CENTER_NAME, self.non_master
        ):
            config.DOMAIN_MOVED = True
        ll_jobs.wait_for_jobs([config.JOB_ACTIVATE_DOMAIN])
        unregistered_vms = ll_sd.get_unregistered_vms(self.non_master)
        vm_names = [vm.get_name() for vm in unregistered_vms]
        logger.info("Unregistered vms: %s", vm_names[0])
        testflow.step("Register VM: %s", self.non_master)
        assert ll_sd.register_object(
            unregistered_vms[0], cluster=config.CLUSTER_NAME
        ), "Unable to register vm %s in cluster %s" % (
            (vm_names[0], config.CLUSTER_NAME)
        )
        ll_jobs.wait_for_jobs([config.JOB_REGISTER_DISK])


@bz({'1467061': {}})
class TestCase5192_3_6(BaseTestCase5192):
    """
    Attach storage domain from 3.6 version into 4.1 data center
    """
    __test__ = True
    polarion_test_case = '5192'
    dc_version = "3.6"


class TestCase5192_4_0(BaseTestCase5192):
    """
    Attach storage domain from 4.0 version into 4.1 data center
    """
    __test__ = True
    polarion_test_case = '5192'
    dc_version = "4.0"


@pytest.mark.usefixtures(
    initialize_disk_params.__name__,
    add_disk.__name__,
    attach_disk.__name__,
    create_template.__name__,
    secure_deactivate_and_detach_storage_domain.__name__,
    remove_storage_domain_setup.__name__,
    remove_template_setup.__name__,
)
class TestCase5200(DomainImportWithTemplate):
    """
    Create vm from a template with two disks, one on a block domain
    and the other on a file domain, from an imported data domain
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/
    workitem?id=RHEVM3-5200
    """
    __test__ = (ISCSI in ART_CONFIG['RUN']['storages'] or
                FCP in ART_CONFIG['RUN']['storages'])
    polarion_test_case = '5200'
    storages = set([ISCSI, NFS])
    partial_import = True

    @polarion("RHEVM3-5200")
    @bz({'1422508': {}})
    @tier3
    def test_import_template_cross_domain(self):
        """
        - One data center with one block storage domain and one file domain
          with a template that contains a VM with disks on both domains
        - Detach the block domain and remove the template
        - Re-attach the block domain and register the template
        - Verify template's existence
        """
        self.new_vm_from_imported_domain_template()


@pytest.mark.usefixtures(
    create_template.__name__,
    secure_deactivate_and_detach_storage_domain.__name__,
    remove_storage_domain_setup.__name__,
    remove_vm.__name__
)
class TestCase5297(DomainImportWithTemplate):
    """
    Create vm from a template from an imported data domain
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/
    workitem?id=RHEVM3-5297
    """
    __test__ = True
    polarion_test_case = '5297'

    @polarion("RHEVM3-5297")
    @bz({'1422508': {}})
    @tier2
    def test_new_vm_from_imported_domain_template(self):
        """
        - import data domain
        - verify template's existence
        - create VM from template
        """
        self.new_vm_from_imported_domain_template()


@pytest.mark.usefixtures(
    create_template.__name__,
    clone_vm_from_template.__name__,
    add_disk.__name__,
    attach_disk_to_cloned_vm.__name__,
    secure_deactivate_and_detach_storage_domain.__name__,
    attach_and_activate_storage_domain.__name__,
    remove_vms.__name__,
)
class TestCase16771(DomainImportWithTemplate):
    """
    Create a VM out of a diskless template
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage_4_0/4_0_Storage_Templates
    """
    __test__ = True
    polarion_test_case = '16771'

    installation = False
    diskless_vm = True

    @polarion("RHEVM-16771")
    @tier2
    def test_register_vm_from_diskless_template(self):
        """
        - Create a VM without disks
        - Create Template from the diskless VM
        - Create VM from the template
        - Attach disk to the VM that created from the template
        - Deactivate and detach the storage domain of the VM with the disk
        - Attach the domain back to the environment
        - Import the VM from the storage domain

        Expected result:
            VM should import back the the environment
        """
        self.vm_names.append(self.vm_from_template)
        hl_sd.register_vm_from_data_domain(
            self.non_master, self.vm_from_template, config.CLUSTER_NAME
        )


@pytest.mark.usefixtures(
    add_non_master_storage_domain.__name__,
    deactivate_detach_and_remove_domain_fin.__name__,
    copy_golden_template_disk.__name__,
    create_vm_func_lvl.__name__,
    create_snapshot.__name__,
    delete_snapshot_setup.__name__,
    block_connection_to_sd.__name__,
    remove_storage_domain_setup.__name__,
    unblock_connection_to_sd.__name__,
)
class TestCase11861(BasicEnvironment):
    """
    Destroy storage domain after VM snapshot delete
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_5_Storage_ImportDomain_DetachAttach?selection=RHEVM3-11861
    """
    __test__ = True
    polarion_test_case = '11861'
    remove_param = {'destroy': True, 'format': 'false'}

    @tier3
    @bz({'1455273': {}})
    @polarion("RHEVM3-11861")
    def test_destroy_domain_after_snapshot_delete(self):
        """
        - Create VM with disk
        - Create Snapshot for the VM
        - Delete the VM snapshot
        - Force remove the disk storage domain without deactivate it (prevent
          from OVF update to occur)
        - Try to import the storage domain back

        Expected result:
            - Import the storage domain should succeed
        """
        testflow.step("Import storage domain %s", self.non_master)
        spm_host = ll_hosts.get_spm_host(config.HOSTS)
        storage_helpers.import_storage_domain(spm_host, self.storage)
        ll_jobs.wait_for_jobs([config.JOB_ADD_DOMAIN])

        testflow.step(
            "Attach storage domain %s to data-center %s",
            self.non_master, config.DATA_CENTER_NAME
        )
        assert hl_sd.attach_and_activate_domain(
            config.DATA_CENTER_NAME, self.non_master
        ), "Failed to attach storage domain %s to data center %s" % (
            self.non_master, config.DATA_CENTER_NAME
        )
        ll_jobs.wait_for_jobs([config.JOB_ACTIVATE_DOMAIN])
