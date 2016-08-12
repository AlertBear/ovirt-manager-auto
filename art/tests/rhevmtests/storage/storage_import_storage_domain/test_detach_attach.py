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
from art.core_api.apis_utils import TimeoutingSampler
from art.rhevm_api.resources import storage
from art.rhevm_api.tests_lib.high_level import (
    datacenters as hl_dc,
    storagedomains as hl_sd,
)
from art.rhevm_api.tests_lib.low_level import (
    clusters as ll_clusters,
    datacenters as ll_dc,
    disks as ll_disks,
    hosts as ll_hosts,
    jobs as ll_jobs,
    storagedomains as ll_sd,
    templates as ll_templates,
    vms as ll_vms,
)
from art.rhevm_api.utils import storage_api as utils
from art.rhevm_api.utils import test_utils
from art.test_handler import exceptions
from art.test_handler.settings import opts
from art.test_handler.tools import polarion, bz
from art.unittest_lib import attr, StorageTest as BaseTestCase
import rhevmtests.storage.helpers as storage_helpers
import rhevmtests.helpers as rhevm_helpers
import pytest

logger = logging.getLogger(__name__)

ENUMS = config.ENUMS
ISCSI = config.STORAGE_TYPE_ISCSI
FCP = config.STORAGE_TYPE_FCP
NFS = config.STORAGE_TYPE_NFS
GLUSTER = config.STORAGE_TYPE_GLUSTER
POSIX = config.STORAGE_TYPE_POSIX
CEPH = config.STORAGE_TYPE_CEPH
TIMEOUT_DEACTIVATE_DOMAIN = 90


def teardown_module():
    """
    Clean datacenter
    """
    # TODO: Seems the imported vms will get assign a mac address and will get
    # released after the engine is restarted. Restart the engine as a W/A
    # until this issue is investigated and fixed:
    # https://projects.engineering.redhat.com/browse/RHEVM-2610
    test_utils.restart_engine(config.ENGINE, 10, 300)

    # TODO: As a workaround for bug
    # https://bugzilla.redhat.com/show_bug.cgi?id=1300075
    test_utils.wait_for_tasks(
        config.VDC, config.VDC_PASSWORD, config.DATA_CENTER_NAME
    )
    hl_dc.ensure_data_center_and_sd_are_active(config.DATA_CENTER_NAME)


class BasicEnvironment(BaseTestCase):
    """
    This class implements setup and teardowns of common things
    """
    # TODO: Run only on rest:
    # https://projects.engineering.redhat.com/browse/RHEVM-1654
    # https://bugzilla.redhat.com/show_bug.cgi?id=1223448
    __test__ = False
    apis = BaseTestCase.apis - set(['cli', 'java', 'sdk'])
    polarion_test_case = None

    def setUp(self):
        """
        Create disks for case
        """
        self.test_failed = False
        self.vm_name = None
        status, master_domain = ll_sd.findMasterStorageDomain(
            True, config.DATA_CENTER_NAME
        )
        if not status:
            raise exceptions.StorageDomainException(
                "Unable to find master storage domain"
            )

        self.host = ll_hosts.getSPMHost(config.HOSTS)
        self.non_master = storage_helpers.create_unique_object_name(
            self.__class__.__name__, config.OBJECT_TYPE_SD
        )
        self.add_storage(
            self.non_master, config.DATA_CENTER_NAME, 0
        )

    def create_vm(self, params={'deep_copy': True}):
        self.vm_name = storage_helpers.create_unique_object_name(
            self.__class__.__name__, config.OBJECT_TYPE_VM
        )
        vm_args = config.create_vm_args.copy()
        vm_args['storageDomainName'] = self.non_master
        vm_args['vmName'] = self.vm_name
        vm_args['vmDescription'] = self.vm_name
        vm_args.update(params)
        if not storage_helpers.create_vm_or_clone(**vm_args):
            raise exceptions.VMException(
                'Unable to create vm %s for test' % self.vm_name
            )

    def _secure_deactivate_detach_storage_domain(self, dc_name, sd_name):
        logger.info("Detaching storage domain %s", sd_name)
        return (
            self._secure_deactivate_domain(dc_name, sd_name)
            and
            self._secure_detach_domain(dc_name, sd_name)
        )

    def _secure_deactivate_domain(self, dc_name, sd_name):
        """
        Deactivate storage domain. There's a chance the OVF update
        task starts while the deactivation command is executed, try for
        TIMEOUT_DEACTIVATE_DOMAIN executing wait_for_tasks
        """
        test_utils.wait_for_tasks(
            config.VDC, config.VDC_PASSWORD, dc_name
        )
        for status in TimeoutingSampler(
            TIMEOUT_DEACTIVATE_DOMAIN, 10, ll_sd.deactivateStorageDomain,
            True, dc_name,
            sd_name
        ):
            if not ll_sd.is_storage_domain_active(dc_name, sd_name):
                return True
            logger.info(
                "Storage domain %s wasn't deactivated, wait for tasks and "
                "try again", sd_name
            )
            test_utils.wait_for_tasks(
                config.VDC, config.VDC_PASSWORD, dc_name
            )
        return False

    def _secure_detach_domain(self, dc_name, sd_name):
        """
        Detach storage domain. There's a chance of other tasks running
        while detaching the domain
        """
        test_utils.wait_for_tasks(
            config.VDC, config.VDC_PASSWORD, dc_name
        )
        for status in TimeoutingSampler(
            TIMEOUT_DEACTIVATE_DOMAIN, 10, ll_sd.detachStorageDomain,
            True, dc_name, sd_name
        ):
            domain_obj = ll_sd.get_storage_domain_obj(sd_name)
            try:
                if domain_obj.get_status() == config.SD_UNATTACHED:
                    return True
            except AttributeError:
                logger.info(
                    "Waiting for all tasks to end before trying to deactivate "
                    "the storage domain again "
                )
                test_utils.wait_for_tasks(
                    config.VDC, config.VDC_PASSWORD, dc_name
                )
        return False

    def _create_environment(
        self, dc_name, cluster_name,
        comp_version=config.COMPATIBILITY_VERSION
    ):
        if not ll_dc.addDataCenter(
                True, name=dc_name, local=False,
                version=comp_version
        ):
            raise exceptions.DataCenterException(
                "Failed to create dc %s" % dc_name
            )

        logger.info("Data Center %s was created successfully", dc_name)

        if not ll_clusters.addCluster(
                True, name=cluster_name, cpu=config.CPU_NAME,
                data_center=dc_name, version=config.COMPATIBILITY_VERSION
        ):
            raise exceptions.ClusterException(
                "addCluster %s with cpu %s and version %s to datacenter %s "
                "failed" % (
                    cluster_name, config.CPU_NAME,
                    config.COMPATIBILITY_VERSION, dc_name
                )
            )
        logger.info("Cluster %s was created successfully", cluster_name)

        self.host = ll_hosts.getHSMHost(config.HOSTS)
        if not ll_hosts.deactivateHost(True, self.host):
            raise exceptions.HostException(
                "Failed to deactivate host %s" % self.host
            )
        ll_hosts.waitForHostsStates(True, [self.host], config.HOST_MAINTENANCE)

        if not ll_hosts.updateHost(
                True, self.host, cluster=cluster_name
        ):
            raise exceptions.HostException(
                "Failed to update host %s" % self.host
            )

        if not ll_hosts.activateHost(True, self.host):
            raise exceptions.HostException(
                "Failed to activate host %s" % self.host
            )

    def add_storage(self, name, data_center, index):
        if self.storage == ISCSI:
            status = hl_sd.addISCSIDataDomain(
                self.host,
                name,
                data_center,
                config.UNUSED_LUNS["lun_list"][index],
                config.UNUSED_LUNS["lun_addresses"][index],
                config.UNUSED_LUNS["lun_targets"][index],
                override_luns=True
            )

        elif self.storage == FCP:
            status = hl_sd.addFCPDataDomain(
                self.host,
                name,
                data_center,
                config.UNUSED_FC_LUNS[index],
                override_luns=True
            )
        elif self.storage == NFS:
            nfs_address = config.UNUSED_DATA_DOMAIN_ADDRESSES[index]
            nfs_path = config.UNUSED_DATA_DOMAIN_PATHS[index]
            status = hl_sd.addNFSDomain(
                host=self.host,
                storage=name,
                data_center=data_center,
                address=nfs_address,
                path=nfs_path,
                format=True
            )
        elif self.storage == GLUSTER:
            gluster_address = (
                config.UNUSED_GLUSTER_DATA_DOMAIN_ADDRESSES[index]
            )
            gluster_path = config.UNUSED_GLUSTER_DATA_DOMAIN_PATHS[index]
            status = hl_sd.addGlusterDomain(
                host=self.host,
                name=name,
                data_center=data_center,
                address=gluster_address,
                path=gluster_path,
                vfs_type=config.ENUMS['vfs_type_glusterfs']
            )
        elif self.storage == CEPH:
            name = "{0}_{1}".format(CEPH, self.non_master)
            self.non_master = name
            posix_address = (
                config.UNUSED_CEPHFS_DATA_DOMAIN_ADDRESSES[0]
            )
            posix_path = config.UNUSED_CEPHFS_DATA_DOMAIN_PATHS[0]
            status = hl_sd.addPosixfsDataDomain(
                host=self.host,
                storage=name,
                data_center=config.DATA_CENTER_NAME,
                address=posix_address,
                path=posix_path,
                vfs_type=CEPH,
                mount_options=config.CEPH_MOUNT_OPTIONS
            )
        if not status:
            raise exceptions.StorageDomainException(
                "Creating %s storage domain '%s' failed"
                % (self.storage, name)
            )
        ll_jobs.wait_for_jobs(
            [config.JOB_ADD_STORAGE_DOMAIN, config.JOB_ACTIVATE_DOMAIN]
        )
        ll_sd.waitForStorageDomainStatus(
            True, config.DATA_CENTER_NAME, name,
            config.SD_ACTIVE
        )
        test_utils.wait_for_tasks(
            config.VDC, config.VDC_PASSWORD, data_center
        )

    def _clean_environment(
        self, dc_name, cluster_name, sd_name, remove_param={'format': 'true'}
    ):
        """
        This function is used by tearDown
        """
        logger.info(
            "Checking if domain %s is active in dc %s", sd_name, dc_name
        )
        if ll_sd.is_storage_domain_active(dc_name, sd_name):
            logger.info("Domain %s is active in dc %s", sd_name, dc_name)

            self._secure_deactivate_domain(dc_name, sd_name)
        logger.info(
            "Domain %s is inactive in datacenter %s", sd_name, dc_name
        )

        if not ll_dc.remove_datacenter(True, dc_name):
            logger.error("Failed to remove dc %s" % dc_name)
            self.test_failed = True

        if not ll_hosts.deactivateHost(True, self.host):
            logger.error("Failed to deactivate host %s" % self.host)
            self.test_failed = True
        ll_hosts.waitForHostsStates(True, [self.host], config.HOST_MAINTENANCE)

        if not ll_hosts.updateHost(
            True, self.host, cluster=config.CLUSTER_NAME
        ):
            logger.error("Failed to update host %s" % self.host)
            self.test_failed = True

        if not ll_hosts.activateHost(True, self.host):
            logger.error("Failed to activate host %s" % self.host)
            self.test_failed = True
        ll_hosts.waitForHostsStates(True, [self.host], config.HOST_UP)

        if not ll_clusters.removeCluster(True, cluster_name):
            logger.error("Failed to remove cluster %s" % cluster_name)
            self.test_failed = True

        if not ll_sd.removeStorageDomain(
            True, sd_name, self.host, **remove_param
        ):
            logger.error("Failed to remove storage domain %s" % sd_name)
            self.test_failed = True

    def register_vm(self, vm_name):
        unregistered_vms = ll_sd.get_unregistered_vms(self.non_master)
        vm_names_to_register = [vm for vm in unregistered_vms if
                                (vm.get_name() == vm_name)]
        if vm_names_to_register:
            status = ll_sd.register_object(
                vm_names_to_register[0], cluster=config.CLUSTER_NAME
            )
            return status
        return False

    def tearDown(self):
        """
        Remove the storage domain
        """
        if self.vm_name and ll_vms.does_vm_exist(self.vm_name):
            if not ll_vms.safely_remove_vms([self.vm_name]):
                logger.error(
                    "Failed to remove vm %s", self.vm_name
                )
                self.test_failed = True
        if not self._secure_deactivate_detach_storage_domain(
            config.DATA_CENTER_NAME, self.non_master
        ):
            logger.error("Unable to detach %s", self.non_master)
            self.test_failed = True
        if not ll_sd.removeStorageDomain(
                True, self.non_master, self.host, format='true'
        ):
            logger.error(
                "Failed to remove storage domain %s", self.non_master
            )
            self.test_failed = True
        BaseTestCase.teardown_exception()


class CommonSetUp(BasicEnvironment):
    """
    Class for common setUp actions
    """

    def setUp(self):
        super(CommonSetUp, self).setUp()
        self._secure_deactivate_detach_storage_domain(
            config.DATA_CENTER_NAME, self.non_master
        )


class DomainImportWithTemplate(BasicEnvironment):
    """
    Create vm from imported domain's Template
    """
    vm_from_template = 'vm_from_temp'

    def setUp(self):
        """
        Create a vm and a template in the domain to be imported
        """
        self.vm_created = False
        self.template_name = 'temp_%s' % self.polarion_test_case
        super(DomainImportWithTemplate, self).setUp()
        self.create_vm()
        self.action_before_creating_template()

        if not ll_templates.createTemplate(
                True, vm=self.vm_name, name=self.template_name,
                cluster=config.CLUSTER_NAME, storagedomain=self.non_master
        ):
            raise exceptions.TemplateException(
                "Failed to create template %s from vm %s"
                % (self.template_name, self.vm_name)
            )

        self._secure_deactivate_detach_storage_domain(
            config.DATA_CENTER_NAME, self.non_master
        )
        if not ll_sd.removeStorageDomain(
                True, self.non_master, self.host, format='false'
        ):
            raise exceptions.StorageDomainException(
                "Failed to remove storage domain %s" % self.non_master
            )

    def action_before_creating_template(self):
        pass

    def new_vm_from_imported_domain_template(self):
        """
        - import data domain
        - verify template's existence
        - create VM from template
        """
        status = False
        if self.storage == ISCSI:
            status = hl_sd.import_iscsi_storage_domain(
                self.host, lun_address=config.UNUSED_LUNS["lun_addresses"][0],
                lun_target=config.UNUSED_LUNS["lun_targets"][0]
            )

        elif self.storage == FCP:
            status = hl_sd.import_fcp_storage_domain(self.host)

        elif self.storage == NFS:
            status = ll_sd.importStorageDomain(
                True, config.TYPE_DATA, NFS,
                config.UNUSED_DATA_DOMAIN_ADDRESSES[0],
                config.UNUSED_DATA_DOMAIN_PATHS[0], self.host
            )
        elif self.storage == GLUSTER:
            status = ll_sd.importStorageDomain(
                True, config.TYPE_DATA, GLUSTER,
                config.UNUSED_GLUSTER_DATA_DOMAIN_ADDRESSES[0],
                config.UNUSED_GLUSTER_DATA_DOMAIN_PATHS[0], self.host,
                vfs_type=GLUSTER
            )
        elif self.storage == CEPH:
            status = ll_sd.importStorageDomain(
                True, config.TYPE_DATA, POSIX,
                config.UNUSED_CEPHFS_DATA_DOMAIN_ADDRESSES[0],
                config.UNUSED_CEPHFS_DATA_DOMAIN_PATHS[0], self.host,
                vfs_type=CEPH, mount_options=config.CEPH_MOUNT_OPTIONS
            )
        assert status, "Failed to import storage domain"
        logger.info("Attaching storage domain %s", self.non_master)
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
        self.template_exists = ll_sd.register_object(
            template_to_register[0], cluster=config.CLUSTER_NAME
        )
        assert self.template_exists, "Template registration failed"
        assert ll_vms.createVm(
            True, self.vm_from_template, self.vm_from_template,
            template=self.template_name, cluster=config.CLUSTER_NAME
        ), "Unable to create vm %s from template %s" % (
            self.vm_from_template, self.template_name
        )

    def tearDown(self):
        """
        Remove template and vm
        """
        ll_templates.wait_for_template_disks_state(self.template_name)
        if not ll_templates.removeTemplate(True, self.template_name):
            logger.error(
                "Failed to remove template %s", self.template_name
            )
            self.test_failed = True
        ll_jobs.wait_for_jobs([config.JOB_REMOVE_TEMPLATE])

        if not ll_vms.safely_remove_vms([self.vm_from_template]):
            logger.error(
                "Failed to remove vm %s", self.vm_from_template
            )
            self.test_failed = True
        ll_jobs.wait_for_jobs([config.JOB_REMOVE_VM])
        super(DomainImportWithTemplate, self).tearDown()


@attr(tier=2)
class TestCase5299(BasicEnvironment):
    """
    Register vm without disks
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/
    workitem?id=RHEVM3-5299
    """
    __test__ = True
    polarion_test_case = '5299'
    vm_no_disks = "vm_without_disks"

    def setUp(self):
        self.vm_created = False
        super(TestCase5299, self).setUp()

        self.vm_created = ll_vms.addVm(
            True, name=self.vm_no_disks, cluster=config.CLUSTER_NAME,
            storagedomain=self.non_master
        )
        if not self.vm_created:
            raise exceptions.VMException(
                "Failed to create vm %s" % self.vm_no_disks
            )

        self._secure_deactivate_detach_storage_domain(
            config.DATA_CENTER_NAME, self.non_master
        )

    @polarion("RHEVM3-5299")
    @bz({'1138142': {'engine': ['rest', 'sdk']}})
    def test_register_vm_without_disks(self):
        """
        - Detach domain
        - Attach domain
        - Verify no vm was unregistered
        """
        logger.info("Attaching storage domain %s", self.non_master)
        hl_sd.attach_and_activate_domain(
            config.DATA_CENTER_NAME, self.non_master
        )
        ll_jobs.wait_for_jobs([config.JOB_ACTIVATE_DOMAIN])

        unregistered_vms = ll_sd.get_unregistered_vms(self.non_master)
        vm_to_import = [
            vm for vm in unregistered_vms if (
                vm.get_name() == self.vm_no_disks
            )
        ]
        logger.info("Unregistered vms: %s", vm_to_import)
        assert len(vm_to_import) == 0, "VM with no disks was unregistered"
        assert ll_vms.does_vm_exist(self.vm_no_disks), (
            "VM doesn't exist after importing storage domain"
        )

    def tearDown(self):
        """
        Remove vm
        """
        if self.vm_created:
            if not ll_vms.removeVm(True, self.vm_no_disks, wait='true'):
                logger.error("Failed to remove vm %s", self.vm_no_disks)
                self.test_failed = True
        super(TestCase5299, self).tearDown()


@attr(tier=2)
class TestCase5300(BasicEnvironment):
    """
    Import domain, preview snapshots and create vm from a snapshot
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/
    workitem?id=RHEVM3-5300
    """
    __test__ = True
    polarion_test_case = '5300'

    def setUp(self):
        """
        Add snapshot to the vm
        """
        self.snap_desc = 'snap_%s' % self.polarion_test_case
        self.cloned_vm = 'cloned_vm_%s' % self.polarion_test_case
        self.previewed = False
        super(TestCase5300, self).setUp()
        self.create_vm()

        if not ll_vms.addSnapshot(True, self.vm_name, self.snap_desc):
            exceptions.SnapshotException(
                "Failed to create snapshot %s" % self.snap_desc
            )
        ll_jobs.wait_for_jobs([config.JOB_CREATE_SNAPSHOT])

        self._secure_deactivate_detach_storage_domain(
            config.DATA_CENTER_NAME, self.non_master
        )

    @polarion("RHEVM3-5300")
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
        logger.info("Attaching storage domain %s", self.non_master)
        hl_sd.attach_and_activate_domain(
            config.DATA_CENTER_NAME, self.non_master
        )
        ll_jobs.wait_for_jobs([config.JOB_ACTIVATE_DOMAIN])

        unregistered_vms = ll_sd.get_unregistered_vms(self.non_master)
        vm_names = [vm.get_name() for vm in unregistered_vms]
        logger.info("Unregistered vms: %s", vm_names)
        assert ll_sd.register_object(
            unregistered_vms[0], cluster=config.CLUSTER_NAME
        )
        ll_jobs.wait_for_jobs([config.JOB_REGISTER_DISK])

        assert self.snap_desc in [
            snap.get_description() for snap in ll_vms.get_vm_snapshots(
                self.vm_name
            )
        ]
        self.previewed = ll_vms.preview_snapshot(
            True, self.vm_name, self.snap_desc, ensure_vm_down=True
        )
        ll_vms.wait_for_vm_snapshots(
            self.vm_name, config.SNAPSHOT_IN_PREVIEW, self.snap_desc
        )
        assert self.previewed

        ll_vms.undo_snapshot_preview(True, self.vm_name)
        ll_jobs.wait_for_jobs([config.JOB_RESTORE_SNAPSHOT])
        ll_vms.wait_for_vm_snapshots(self.vm_name, config.SNAPSHOT_OK)
        self.previewed = False

        logger.info(
            "Creating vm %s from snapshot %s", self.cloned_vm, self.snap_desc
        )
        assert ll_vms.cloneVmFromSnapshot(
            True, name=self.cloned_vm, cluster=config.CLUSTER_NAME,
            vm=self.vm_name, snapshot=self.snap_desc,
            storagedomain=self.non_master,
        )

    def tearDown(self):
        """
        Remove cloned vm
        """
        if self.previewed:
            if not ll_vms.undo_snapshot_preview(True, self.vm_name):
                logger.error("Failed to undo snapshot of vm")
                self.test_failed = True
            ll_vms.wait_for_vm_snapshots(
                self.vm_name, [config.SNAPSHOT_OK], [self.snap_desc]
            )
        if not ll_vms.removeVm(True, self.cloned_vm, stopVM=True):
            logger.error("Failed to remove cloned vm %s", self.cloned_vm)
            self.test_failed = True
        ll_jobs.wait_for_jobs([config.JOB_REMOVE_VM])
        super(TestCase5300, self).tearDown()


@attr(tier=4)
class TestCase5302(BasicEnvironment):
    """
    IP block during import domain
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/
    workitem?id=RHEVM3-5302
    """
    __test__ = True
    polarion_test_case = '5302'

    def setUp(self):
        self.imported = False
        super(TestCase5302, self).setUp()

        self._secure_deactivate_detach_storage_domain(
            config.DATA_CENTER_NAME, self.non_master
        )
        self.host_ip = ll_hosts.getHostIP(config.HOSTS[0])

    @polarion("RHEVM3-5302")
    def test_block_connection_during_import(self):
        """
        - verify that there are no IP blocks from vdsm->engine
          or engine->vdsm
        - import data domain to another DC
        - during the operation add IP block from host to engine's IP
        """
        logger.info('Checking if domain %s is attached to dc %s',
                    self.non_master, config.DATA_CENTER_NAME)

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

            assert utils.blockOutgoingConnection(
                self.host_ip, config.HOSTS_USER, config.HOSTS_PW, config.VDC
            )

        non_master_domains = ll_sd.findNonMasterStorageDomains(
            True, config.DATA_CENTER_NAME
        )
        if self.non_master in [
            sd['nonMasterDomains'] for sd in non_master_domains
        ]:
            self.imported = True
            # TODO: Expected results are not clear

    def tearDown(self):
        utils.unblockOutgoingConnection(
            self.host_ip, config.HOSTS_USER, config.HOSTS_PW, config.VDC
        )
        ll_dc.waitForDataCenterState(config.DATA_CENTER_NAME)
        super(TestCase5302, self).tearDown()


@attr(tier=2)
class TestCase5193(BasicEnvironment):
    """
    test mounted meta-data files when attaching a file domain
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/
    workitem?id=RHEVM3-5193
    """
    __test__ = NFS in opts['storages']
    storages = set([NFS])
    polarion_test_case = '5193'

    def setUp(self):
        super(TestCase5193, self).setUp()
        self.create_vm()
        self._secure_deactivate_detach_storage_domain(
            config.DATA_CENTER_NAME, self.non_master
        )
        ll_jobs.wait_for_jobs([config.JOB_DETACH_DOMAIN])

    @polarion("RHEVM3-5193")
    def test_attach_file_domain(self):
        """
        - detach an nfs domain
        - attach an nfs domain on different dc
        - register the vms
        """
        logger.info("Attaching storage domain %s", self.non_master)
        hl_sd.attach_and_activate_domain(
            config.DATA_CENTER_NAME, self.non_master
        )
        ll_jobs.wait_for_jobs([config.JOB_ACTIVATE_DOMAIN])

        unregistered_vms = ll_sd.get_unregistered_vms(self.non_master)
        vm_names = [vm.get_name() for vm in unregistered_vms]
        logger.info("Unregistered vms: %s", vm_names)
        assert ll_sd.register_object(
            unregistered_vms[0], cluster=config.CLUSTER_NAME
        )
        ll_jobs.wait_for_jobs([config.JOB_REGISTER_DISK])


@attr(tier=2)
class TestCase5194(BasicEnvironment):
    """
    test lv's existence when importing a block domain
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/
    workitem?id=RHEVM3-5194
    """
    __test__ = BaseTestCase.storage in config.BLOCK_TYPES
    polarion_test_case = '5194'

    def setUp(self):
        super(TestCase5194, self).setUp()
        self.create_vm()
        self._secure_deactivate_detach_storage_domain(
            config.DATA_CENTER_NAME, self.non_master
        )
        ll_jobs.wait_for_jobs([config.JOB_DETACH_DOMAIN])

    @polarion("RHEVM3-5194")
    def test_lv_exists_after_import_block_domain(self):
        """
        - detach block domain
        - attach the block domain to different dc (execute lvs,vgs)
        - register vms and disks
        """
        logger.info("Attaching storage domain %s", self.non_master)
        hl_sd.attach_and_activate_domain(
            config.DATA_CENTER_NAME, self.non_master
        )
        ll_jobs.wait_for_jobs([config.JOB_ACTIVATE_DOMAIN])

        unregistered_vms = ll_sd.get_unregistered_vms(self.non_master)
        vm_names = [vm.get_name() for vm in unregistered_vms]
        logger.info("Unregistered vms: %s", vm_names)
        assert ll_sd.register_object(
            unregistered_vms[0], cluster=config.CLUSTER_NAME
        ), "Failed to register vm %s" % unregistered_vms[0]
        ll_jobs.wait_for_jobs([config.JOB_REGISTER_DISK])

        assert ll_vms.startVms(
            [self.vm_name], wait_for_status=config.VM_UP
        ), "VM %s failed to restart" % self.vm_name

    def tearDown(self):
        """
        Remove vm and storage domain
        """
        if not ll_vms.safely_remove_vms([self.vm_name]):
            logger.error(
                "Failed to remove vm %s", self.vm_name
            )
            self.test_failed = True
        super(TestCase5194, self).tearDown()


@attr(tier=4)
class TestCase5205(CommonSetUp):
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
    def test_restart_vdsm_during_import_domain(self):
        """
        - import data domain on different dc
        - during the operation restart vdsm
        """
        self._restart_component(
            test_utils.restartVdsmd, config.HOSTS[0], config.HOSTS_PW
        )

    @polarion("RHEVM3-5205")
    def test_restart_engine_during_import_domain(self):
        """
        - import data domain on different dc
        - Restart the engine during the Import domain operation
        """
        self._restart_component(
            test_utils.restart_engine, config.ENGINE, 10, 300
        )


@attr(tier=4)
class TestCase5304(CommonSetUp):
    """
    Import domain during host reboot
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/
    workitem?id=RHEVM3-5304
    """
    __test__ = True
    polarion_test_case = '5304'

    @polarion("RHEVM3-5304")
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

        assert ll_hosts.rebootHost(
            True, config.HOSTS[0], config.HOSTS_USER, config.HOSTS_PW
        )
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


@attr(tier=2)
class BaseCaseInitializeDataCenter(BasicEnvironment):
    """
    Base class for initializing a data center with an imported domain
    """
    remove_param = None

    def setUp(self):
        """
        Create a new data center with a vm on it
        """
        self.dc_name = storage_helpers.create_unique_object_name(
            self.__class__.__name__, config.OBJECT_TYPE_DC
        )
        self.cluster_name = storage_helpers.create_unique_object_name(
            self.__class__.__name__, config.OBJECT_TYPE_CLUSTER
        )
        super(BaseCaseInitializeDataCenter, self).setUp()
        self.create_vm()
        self._create_environment(self.dc_name, self.cluster_name)
        self._secure_deactivate_domain(
            config.DATA_CENTER_NAME, self.non_master
        )
        if self.detach:
            if not ll_sd.detachStorageDomain(
                True, config.DATA_CENTER_NAME, self.non_master
            ):
                raise exceptions.StorageDomainException(
                    "Unable to detach domain %s on dc %s"
                    % (config.DATA_CENTER_NAME, self.non_master)
                )

        if not ll_sd.removeStorageDomain(
                True, self.non_master, self.host, **self.remove_param
        ):
            raise exceptions.StorageDomainException(
                "Failed to remove storage domain" % self.non_master
            )

    def execute_flow(self):
        """
        Import the data domain
        """
        status = False
        if self.storage == ISCSI:
            status = hl_sd.import_iscsi_storage_domain(
                self.host, lun_address=config.UNUSED_LUNS["lun_addresses"][0],
                lun_target=config.UNUSED_LUNS["lun_targets"][0]
            )

        elif self.storage == FCP:
            status = hl_sd.import_fcp_storage_domain(self.host)

        elif self.storage == NFS:
            status = ll_sd.importStorageDomain(
                True, config.TYPE_DATA, NFS,
                config.UNUSED_DATA_DOMAIN_ADDRESSES[0],
                config.UNUSED_DATA_DOMAIN_PATHS[0], self.host
            )
        elif self.storage == GLUSTER:
            status = ll_sd.importStorageDomain(
                True, config.TYPE_DATA, GLUSTER,
                config.UNUSED_GLUSTER_DATA_DOMAIN_ADDRESSES[0],
                config.UNUSED_GLUSTER_DATA_DOMAIN_PATHS[0], self.host
            )
        assert status, "Failed to import storage domain"

    def tearDown(self):
        """
        Remove data center
        """
        self._clean_environment(
            self.dc_name, self.cluster_name, self.non_master
        )
        BaseTestCase.teardown_exception()


class TestCase5201(BaseCaseInitializeDataCenter):
    """
    Initialize DC from an unattached imported domain
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/
    workitem?id=RHEVM3-5201
    """
    __test__ = True
    polarion_test_case = '5201'
    remove_param = {'format': 'false'}
    detach = True

    @polarion("RHEVM3-5201")
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
        logger.info("Attaching storage domain %s", self.non_master)
        hl_sd.attach_and_activate_domain(self.dc_name, self.non_master)
        ll_jobs.wait_for_jobs([config.JOB_ACTIVATE_DOMAIN])

        unregistered_vms = ll_sd.get_unregistered_vms(self.non_master)
        vm_names = [vm.get_name() for vm in unregistered_vms]
        logger.info("Unregistered vms: %s", vm_names)
        assert ll_sd.register_object(
            unregistered_vms[0], cluster=self.cluster_name
        ), "Unable to register vm %s in cluster %s" % (
            (vm_names[0], self.cluster_name)
        )
        ll_jobs.wait_for_jobs([config.JOB_REGISTER_DISK])
        assert ll_vms.startVm(
            True, self.vm_name, wait_for_status=config.VM_UP
        ), "VM %s failed to restart" % self.vm_name

    def tearDown(self):
        """
        Power off and remove vm
        """
        if not ll_vms.safely_remove_vms([self.vm_name]):
            logger.error(
                "Failed to remove vm %s", self.vm_name
            )
            self.test_failed = True
        super(TestCase5201, self).tearDown()


@attr(tier=2)
class TestCase12207(BaseCaseInitializeDataCenter):
    """
    Initialize DC from a destroyed domain
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/
    workitem?id=RHEVM3-12207
    """
    __test__ = True
    polarion_test_case = '12207'
    remove_param = {'destroy': True}
    detach = False

    @polarion("RHEVM3-12207")
    @bz({'1350966': {}})
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
        logger.info("Attaching storage domain %s", self.non_master)
        with pytest.raises(exceptions.StorageDomainException):
            hl_sd.attach_and_activate_domain(self.dc_name, self.non_master)

    def tearDown(self):
        """
        Wait for the domain to become active in case of a test failure
        """
        ll_jobs.wait_for_jobs([config.JOB_ACTIVATE_DOMAIN])
        # After a failure to activate the storage domain, this can only
        # be removed by destroying it
        self._clean_environment(
            self.dc_name, self.cluster_name, self.non_master,
            remove_param={'destroy': True}
        )
        if self.storage == NFS or self.storage == POSIX:
            storage.clean_mount_point(
                self.host, config.UNUSED_DATA_DOMAIN_ADDRESSES[0],
                config.UNUSED_DATA_DOMAIN_PATHS[0],
                rhevm_helpers.NFS_MNT_OPTS
            )
        elif self.storage == GLUSTER:
            storage.clean_mount_point(
                self.host, config.UNUSED_GLUSTER_DATA_DOMAIN_ADDRESSES[0],
                config.UNUSED_GLUSTER_DATA_DOMAIN_PATHS[0],
                rhevm_helpers.GLUSTER_MNT_OPTS
            )
        BaseTestCase.teardown_exception()


@attr(tier=2)
class TestCase10951(BasicEnvironment):
    """
    Import an export domain to the system

    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/
    workitem?id=RHEVM3-10951
    """
    __test__ = POSIX in opts['storages'] or GLUSTER in opts['storages']
    polarion_test_case = "10951"
    datacenter = config.DATA_CENTER_NAME
    nfs_version = None
    vfs_type = None

    def setUp(self):
        """
        Creates storage domains which will be later imported
        """
        super(TestCase10951, self).setUp()
        self.export_domain = 'test_%s_export_%s' % (
            self.polarion_test_case, self.storage
        )
        self.sd_type = ENUMS['storage_dom_type_export']
        self._secure_deactivate_detach_storage_domain(
            self.datacenter, config.EXPORT_DOMAIN_NAME
        )
        self.host = ll_hosts.getSPMHost(config.HOSTS)
        self.host_ip = ll_hosts.getHostIP(self.host)
        self.password = config.HOSTS_PW
        if self.storage == POSIX:
            self.export_address = config.UNUSED_DATA_DOMAIN_ADDRESSES[1]
            self.export_path = config.UNUSED_DATA_DOMAIN_PATHS[1]
            self.vfs_type = NFS
            self.nfs_version = 'v4.1'
            self.storage_type = POSIX

            status = hl_sd.addPosixfsDataDomain(
                self.host, self.export_domain, self.datacenter,
                self.export_address, self.export_path, vfs_type=self.vfs_type,
                sd_type=self.sd_type, nfs_version=self.nfs_version
            )
            if not status:
                raise exceptions.StorageDomainException(
                    "Creating POSIX domain '%s' failed" % self.export_domain
                )

        elif self.storage == GLUSTER:
            self.export_address = (
                config.UNUSED_GLUSTER_DATA_DOMAIN_ADDRESSES[1]
            )
            self.export_path = config.UNUSED_GLUSTER_DATA_DOMAIN_PATHS[1]
            self.vfs_type = ENUMS['vfs_type_glusterfs']
            self.storage_type = GLUSTER

            status = hl_sd.addGlusterDomain(
                self.host, self.export_domain, self.datacenter,
                self.export_address, self.export_path,
                vfs_type=self.vfs_type, sd_type=self.sd_type
            )
            if not status:
                raise exceptions.StorageDomainException(
                    "Creating GlusterFS domain '%s' failed"
                    % self.export_domain
                )
        test_utils.wait_for_tasks(config.VDC, config.VDC_ROOT_PASSWORD,
                                  self.datacenter)
        hl_sd.remove_storage_domain(
            self.export_domain, self.datacenter, self.host, False, config.VDC,
            config.VDC_PASSWORD
        )

    @polarion("RHEVM3-10951")
    def test_import_existing_export_domain(self):
        """
        - Import existing export storage domain
        - Attach it to the data center
        """
        assert ll_sd.importStorageDomain(
            True, self.sd_type, self.storage_type, self.export_address,
            self.export_path, self.host, nfs_version=self.nfs_version,
            vfs_type=self.vfs_type
        ), "Unable to import export domain %s" % self.export_domain
        logger.info("Attaching storage domain %s", self.export_domain)
        assert hl_sd.attach_and_activate_domain(
            config.DATA_CENTER_NAME, self.export_domain
        ), "Unable to attach export domain %s" % self.export_domain

    def tearDown(self):
        """
        Remove the attached export domain
        """
        ll_jobs.wait_for_jobs([config.JOB_ACTIVATE_DOMAIN])
        self._secure_deactivate_detach_storage_domain(
            self.datacenter, self.export_domain
        )
        hl_sd.attach_and_activate_domain(
            self.datacenter, config.EXPORT_DOMAIN_NAME
        )
        ll_jobs.wait_for_jobs([config.JOB_ACTIVATE_DOMAIN])
        hl_sd.remove_storage_domain(
            self.export_domain, self.datacenter, self.host, True, config.VDC,
            config.VDC_PASSWORD
        )
        super(TestCase10951, self).tearDown()


@attr(tier=2)
class BaseTestCase5192(BasicEnvironment):
    """
    Attach storage domain from older version into 3.5 data center
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/
    workitem?id=RHEVM3-5192
    """
    dc_version = None

    def setUp(self):
        """
        Create environment
        """
        self.dc_name = storage_helpers.create_unique_object_name(
            self.__class__.__name__, config.OBJECT_TYPE_DC
        )
        self.cluster_name = storage_helpers.create_unique_object_name(
            self.__class__.__name__, config.OBJECT_TYPE_CLUSTER
        )
        self._create_environment(
            self.dc_name, self.cluster_name, self.dc_version
        )
        self.master_domain = storage_helpers.create_unique_object_name(
            self.__class__.__name__, config.OBJECT_TYPE_SD
        )
        self.add_storage(self.master_domain, self.dc_name, 0)
        self.non_master = storage_helpers.create_unique_object_name(
            self.__class__.__name__, config.OBJECT_TYPE_SD
        )
        self.add_storage(self.non_master, self.dc_name, 1)
        self.create_vm(
            {
                'clone_from_template': False,
                'cluster': self.cluster_name
            }
        )
        self._secure_deactivate_detach_storage_domain(
            self.dc_name, self.non_master
        )

    def test_attach_from_older_version(self):
        """
        Configure two data centers, one dc_verion and other > 3.5
        Detach dc_version storage domain and attach it to > 3.5 data center and
        register the vms
        """
        hl_sd.attach_and_activate_domain(
            config.DATA_CENTER_NAME, self.non_master
        )
        ll_jobs.wait_for_jobs([config.JOB_ACTIVATE_DOMAIN])
        unregistered_vms = ll_sd.get_unregistered_vms(self.non_master)
        vm_names = [vm.get_name() for vm in unregistered_vms]
        logger.info("Unregistered vms: %s", vm_names)
        assert ll_sd.register_object(
            unregistered_vms[0], cluster=config.CLUSTER_NAME
        ), "Unable to register vm %s in cluster %s" % (
            (vm_names[0], config.CLUSTER_NAME)
        )

    def tearDown(self):
        """
        Remove storage domain
        """
        ll_jobs.wait_for_jobs([config.JOB_REGISTER_DISK])
        self._clean_environment(
            self.dc_name, self.cluster_name, self.master_domain
        )
        super(BaseTestCase5192, self).tearDown()


class TestCase5192_3_6(BaseTestCase5192):
    """
    Attach storage domain from 3.6 version into 4.0 data center
    """
    __test__ = True
    dc_version = "3.6"


# Bugzilla history:
# BZ1328071: Unexpected flow when importing a domain with a template with
# multiple disks on different domains
@attr(tier=2)
class TestCase5200(DomainImportWithTemplate):
    """
    Create vm from a template with two disks, one on a block domain
    and the other on a file domain, from an imported data domain
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/
    workitem?id=RHEVM3-5200
    """
    __test__ = ISCSI in opts['storages'] or FCP in opts['storages']
    storages = set([ISCSI, NFS])
    polarion_test_case = '5200'

    def setUp(self):
        """
        Create template and add disk in a file domain
        """
        self.disk_alias = None
        self.file_domain = ll_sd.getStorageDomainNamesForType(
            config.DATA_CENTER_NAME, NFS
        )[0]
        super(TestCase5200, self).setUp()
        # Since the template contains a disk in file domain, the template
        # is not removed by ovirt when the block domain is removed.
        # Remove the template so after importing the block domain the template
        # can be registered
        if not ll_templates.removeTemplate(True, self.template_name):
            raise exceptions.TemplateException(
                "Failed to remove template %s" % self.template_name
            )

    def action_before_creating_template(self):
        """
        Add disk to file storage domain
        """
        self.disk_alias = storage_helpers.create_unique_object_name(
            self.__class__.__name__, config.OBJECT_TYPE_DISK
        )
        ll_disks.addDisk(
            True, alias=self.disk_alias, provisioned_size=config.DISK_SIZE,
            interface=config.VIRTIO, format=config.RAW_DISK, sparse=False,
            active=True, storagedomain=self.file_domain
        )
        ll_disks.wait_for_disks_status(self.disk_alias)
        storage_helpers.prepare_disks_for_vm(self.vm_name, [self.disk_alias])

    def test_import_template_cross_domain(self):
        """
        - One data center with one block storage domain and one file domain
          with a template that contains a VM with disks on both domains
        - Detach the block domain and remove the template
        - Re-attach the block domain and register the template
        - Verify template's existence
        """
        self.new_vm_from_imported_domain_template()


@attr(tier=1)
class TestCase5297(DomainImportWithTemplate):
    """
    Create vm from a template from an imported data domain
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/
    workitem?id=RHEVM3-5297
    """
    __test__ = True
    polarion_test_case = '5297'

    @polarion("RHEVM3-5297")
    def test_new_vm_from_imported_domain_template(self):
        """
        - import data domain
        - verify template's existence
        - create VM from template
        """
        self.new_vm_from_imported_domain_template()
