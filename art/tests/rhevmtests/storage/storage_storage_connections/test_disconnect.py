"""
3.6 Storage iSCSI disconnect scenarios
https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
Storage/3_6_Storage_iSCSI_disconnect_scenarios
"""
import config
import logging
import pytest

from art.rhevm_api.tests_lib.high_level import (
    datacenters as hl_dc,
    hosts as hl_hosts,
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
)
from rrmngmnt.host import Host
from rrmngmnt.user import User

from art.core_api.apis_utils import TimeoutingSampler
from art.core_api.apis_exceptions import APITimeout
from art.rhevm_api.utils.test_utils import wait_for_tasks
from art.test_handler import exceptions
from art.test_handler.settings import opts
from art.test_handler.tools import polarion  # pylint: disable=E0611
from art.unittest_lib import attr, StorageTest
import rhevmtests.storage.helpers as storage_helpers

logger = logging.getLogger(__name__)
ISCSI = config.STORAGE_TYPE_ISCSI
ISCSIADM_SESSION = ["iscsiadm", "-m", "session"]
ISCSIADM_LOGOUT = ["iscsiadm", "-m", "session", "-u"]

# The iscsi session can be open up to 30 seconds after the operation is
# executed (deactivate domain, remove direct LUN disk, ...)
TIME_UNTIL_ISCSI_SESSION_DISAPPEARS = 30


@pytest.fixture(scope='module')
def initializer_module(request):
    """
    Remove all the iscsi domains as a workaround for bugzilla
    https://bugzilla.redhat.com/show_bug.cgi?id=1146115
    """
    # TODO: Remove all setup_module and teardown_module when
    # https://bugzilla.redhat.com/show_bug.cgi?id=1146115 is fixed

    def finalizer_module():
        """
        Add the iscsi storage domains back
        """
        test_failed = False
        # TODO: WA for bug https://bugzilla.redhat.com/show_bug.cgi?id=1302780
        # Add iSCSI domains back
        # 1) Remove block1 when bug is fixed
        # 2) Uncomment block2 when bug is fixed

        # TODO: block1
        logger.info("Adding iscsi storage domains back")
        iscsi_sds = [sd['name'] for sd in config.DC['storage_domains']
                     if sd['storage_type'] == config.STORAGE_TYPE_ISCSI]
        for name, lun, target, address in zip(
                iscsi_sds, config.LUNS, config.LUN_TARGETS,
                config.LUN_ADDRESSES
        ):
            hl_sd.addISCSIDataDomain(
                config.HOST_FOR_MOUNT, name, config.DATA_CENTER_NAME,
                lun, address, target, override_luns=True, login_all=True
            )
        # TODO: block1 END

        # TODO: block2
        # logger.info("Importing iscsi storage domains back")
        # # Importing all iscsi domains using the address and target of one of
        # them imported = hl_sd.importBlockStorageDomain(
        #     config.HOST_FOR_MOUNT, config.LUN_ADDRESSES[0],
        #     config.LUN_TARGETS[0]
        # )
        # if not imported:
        #     logger.error("Failed to import iSCSI domains back")
        #     test_failed = True
        # if imported:
        #     register_failed = False
        #     for sd in ISCSI_SDS:
        #         hl_sd.attach_and_activate_domain(config.DATA_CENTER_NAME, sd)
        #         unregistered_vms = ll_sd.get_unregistered_vms(sd)
        #         if unregistered_vms:
        #             for vm in unregistered_vms:
        #                 if not ll_sd.register_object(
        #                     vm, cluster=config.CLUSTER_NAME
        #                 ):
        #                     logger.error(
        #                         "Failed to register vm %s from imported "
        #                         "domain %s", vm, sd
        #                     )
        #                     register_failed = True
        #     if register_failed:
        #         raise exceptions.TearDownException(
        #             "TearDown failed to register all vms from imported "
        #             "domain"
        #         )
        # TODO: block2 END

        # TODO: WA for bug https://bugzilla.redhat.com/show_bug.cgi?id=1302780
        # Copying template disk to the new iSCSI domains and create 2 vms
        # Delete this block when fix

        template_name = config.TEMPLATE_NAME[0]
        disk = ll_templates.getTemplateDisks(template_name)[0].get_alias()
        for sd in iscsi_sds:
            logger.info(
                "Copying disk %s for template %s to sd %s", disk,
                template_name, sd
            )
            try:
                ll_templates.copyTemplateDisk(template_name, disk, sd)
            except exceptions.DiskException:
                test_failed = True
                logger.error(
                    "Failed to copy template disk to imported iSCSI domain %s",
                    sd
                )
            ll_templates.wait_for_template_disks_state(template_name)

        for vm in config.ISCSI_VMS:
            vm_args = config.create_vm_args.copy()
            vm_args['storageDomainName'] = iscsi_sds[0]
            vm_args['vmName'] = vm
            if not storage_helpers.create_vm_or_clone(**vm_args):
                test_failed = True
                logger.error("Unable to create vm %s", vm)
        # TODO END - Delete this block when fixed

        if test_failed:
            raise exceptions.TearDownException("TearDown failed")

    request.addfinalizer(finalizer_module)
    global ISCSI_SDS
    ISCSI_SDS = ll_sd.getStorageDomainNamesForType(
        config.DATA_CENTER_NAME, config.STORAGE_TYPE_ISCSI
    )
    wait_for_tasks(
        config.VDC_HOST, config.VDC_ROOT_PASSWORD, config.DATA_CENTER_NAME
    )
    for sd in ISCSI_SDS:
        hl_sd.detach_and_deactivate_domain(
            config.DATA_CENTER_NAME, sd
        )
        # We want to destroy the domains so we will be able to restore the
        # data on them
        # TODO: WA for bug https://bugzilla.redhat.com/show_bug.cgi?id=1302780
        # 1) We are formatting the domain (format='false' => format='true')
        #    Change back to 'false' when bug is fixed
        if not ll_sd.removeStorageDomain(
            positive=True, storagedomain=sd, host=config.HOST_FOR_MOUNT,
            format='true'
        ):
            raise exceptions.StorageDomainException(
                "Failed to remove and format storage domain '%s'" % sd
            )
        # TODO END

    # Due to https://bugzilla.redhat.com/show_bug.cgi?id=1146115
    # iscsi connections sessions are not closed when there are multiple
    # consumers on the target, logout from all session in all hosts
    for host in config.HOSTS:
        host_ip = ll_hosts.getHostIP(host)
        host = Host(host_ip)
        user = User(config.HOSTS_USER, config.HOSTS_PW)
        host.users.append(user)
        host_executor = host.executor(user)
        rc, out, error = host_executor.run_cmd(ISCSIADM_LOGOUT)
        if error and "No matching sessions found" not in error:
            raise Exception(
                "Error executing %s command: %s" % (ISCSIADM_LOGOUT, error)
            )


class BaseTestCase(StorageTest):
    storages = set([ISCSI])

    def initializer_BaseTestCase(self):
        """
        Initialize host variables
        """
        self.host = config.HOST_FOR_MOUNT
        self.host_ip = config.HOST_FOR_MOUNT_IP
        host = Host(self.host_ip)
        user = User(config.HOSTS_USER, config.HOSTS_PW)
        host.users.append(user)
        self.host_executor = host.executor(user)

    def logout_sessions(self):
        """
        Logout all iscsi sessions before starting the test
        """
        rc, out, error = self.host_executor.run_cmd(ISCSIADM_LOGOUT)
        if error and "No matching sessions found" not in error:
            raise Exception(
                "Error executing %s command: %s" % (ISCSIADM_LOGOUT, error)
            )

    def host_iscsi_sessions(self):
        """
        Return the output from executing "iscsiadm -m session" command
        """
        rc, out, error = self.host_executor.run_cmd(ISCSIADM_SESSION)
        if rc:
            if "No active sessions" in error:
                return []
            else:
                logger.error(
                    "Unable execute %s command on host %s", ISCSIADM_SESSION,
                    self.host
                )
                raise Exception(
                    "Error executing %s command: %s"
                    % (ISCSIADM_SESSION, error)
                )
        return out.rstrip().split('\n')

    def timeout_sampling_iscsi_session(self):
        """
        Wait until all sessions have been removed from the host
        """
        try:
            for sessions in TimeoutingSampler(
                TIME_UNTIL_ISCSI_SESSION_DISAPPEARS, 5,
                self.host_iscsi_sessions,
            ):
                if not sessions:
                    return True
        except APITimeout:
            return False


class BaseTestCaseNewDC(BaseTestCase):

    add_iscsi_domain = True
    add_nfs_domain = False
    login_all = False

    def finalizer_BaseTestCaseNewDC(self):
        """
        Remove the created data center
        """
        wait_for_tasks(config.VDC_HOST, config.VDC_ROOT_PASSWORD, self.dc)
        if not hl_dc.clean_datacenter(
            True, datacenter=self.dc, formatExpStorage='true',
            vdc=config.VDC, vdc_password=config.VDC_PASSWORD
        ):
            self.test_failed = True
            logger.error(
                "Failed to clean Data center '%s'", self.dc
            )
        if not ll_hosts.addHost(
            True, self.host, address=self.host_ip,
            wait=True, reboot=True, cluster=config.CLUSTER_NAME,
            root_password=config.VDC_ROOT_PASSWORD
        ):
            self.test_failed = True
            logger.error(
                "Failed to add host '%s' into cluster '%s'",
                self.host, config.CLUSTER_NAME
            )
        BaseTestCase.teardown_exception()

    @pytest.fixture(scope='function')
    def initializer_BaseTestCaseNewDC_fixture(
        self, request, initializer_module
    ):
        """
        Fixture for initializer_BaseTestCaseNewDC
        """
        request.addfinalizer(self.finalizer_BaseTestCaseNewDC)
        self.initializer_BaseTestCaseNewDC()

    def initializer_BaseTestCaseNewDC(self):
        """
        Create a new data center, cluster and add a host
        """
        self.initializer_BaseTestCase()
        self.dc = storage_helpers.create_unique_object_name(
            self.__class__.__name__, config.OBJECT_TYPE_DC
        )
        self.cluster = storage_helpers.create_unique_object_name(
            self.__class__.__name__, config.OBJECT_TYPE_CLUSTER
        )
        if not ll_dc.addDataCenter(
            True, name=self.dc, version=config.COMP_VERSION
        ):
            raise exceptions.DataCenterException(
                "Failed to create Data center '%s'" % self.dc
            )
        if not ll_clusters.addCluster(
            True, name=self.cluster, cpu=config.CPU_NAME, data_center=self.dc,
            version=config.COMP_VERSION
        ):
            raise exceptions.ClusterException(
                "Failed to create cluster '%s'" % self.cluster
            )
        if not hl_hosts.move_host_to_another_cluster(
            self.host, self.cluster
        ):
            raise exceptions.HostException(
                "Failed to migrate host '%s' into cluster '%s'" % (
                    self.host, self.cluster
                )
            )

        self.logout_sessions()
        if len(self.host_iscsi_sessions()) != 0:
            raise exceptions.HostException(
                "Host %s has active iscsi connections before starting "
                "the test" % self.host
            )

        self.iscsi_domain = storage_helpers.create_unique_object_name(
            self.__class__.__name__, config.OBJECT_TYPE_SD
        )

        if self.add_iscsi_domain:
            if not hl_sd.addISCSIDataDomain(
                self.host, self.iscsi_domain, self.dc,
                config.UNUSED_LUNS[0], config.UNUSED_LUN_ADDRESSES[0],
                config.UNUSED_LUN_TARGETS[0],
                override_luns=True, login_all=self.login_all
            ):
                raise exceptions.StorageDomainException(
                    "Unable to add iscsi domain %s, %s, %s to data center %s"
                    % (
                        config.UNUSED_LUNS[0], config.UNUSED_LUN_ADDRESSES[0],
                        config.UNUSED_LUN_TARGETS[0], self.dc
                    )
                )
        self.nfs_domain = storage_helpers.create_unique_object_name(
            self.__class__.__name__, config.OBJECT_TYPE_SD
        )
        if self.add_nfs_domain:
            if not hl_sd.addNFSDomain(
                self.host, self.nfs_domain, self.dc,
                config.UNUSED_DATA_DOMAIN_ADDRESSES[0],
                config.UNUSED_DATA_DOMAIN_PATHS[0],
                format=True, activate=True
            ):
                raise exceptions.StorageDomainException(
                    "Unable to add nfs domain %s, %s, to data center %s"
                    % (
                        config.UNUSED_DATA_DOMAIN_ADDRESSES[0],
                        config.UNUSED_DATA_DOMAIN_PATHS[0], self.dc
                    )
                )


@attr(tier=2)
class TestCase11196(BaseTestCaseNewDC):
    """
    RHEVM3-11196 - Place host in maintenance mode

    https://polarion.engineering.redhat.com/polarion/#/project/
    RHEVM3/workitem?id=RHEVM3-11196
    """
    __test__ = ISCSI in opts['storages']

    @pytest.fixture(scope='function')
    def initializer_TestCase11196(self, request, initializer_module):
        """
        Add finalizer
        """
        def finalizer_TestCase11196():
            """
            Reactivate host
            """
            if ll_hosts.isHostInMaintenance(True, self.host):
                if not ll_hosts.activateHost(True, self.host):
                    self.test_failed = True
                    logger.error(
                        "Error activating host %s", self.host
                    )
            if not ll_sd.waitForStorageDomainStatus(
                True, self.dc, self.iscsi_domain, config.SD_ACTIVE
            ):
                self.test_failed = True
                logger.error(
                    "Error activating storage domain %s", self.iscsi_domain
                )
            self.finalizer_BaseTestCaseNewDC()
        self.initializer_BaseTestCaseNewDC()
        request.addfinalizer(finalizer_TestCase11196)

    @polarion("RHEVM3-11196")
    @pytest.mark.usefixtures("initializer_TestCase11196")
    def test_place_host_maintenance_mode(self):
        """
        Test setup:
        - Have 1 or more iSCSI domains in the DC

        Test flow:
        - Check that the host in the Data center has iscsi sessions with the
        iSCSI storage server with 'iscsiadm -m session'  ->  Host should have
        iscsi connections
        - Place the host in maintenance mode
        - Run command 'iscsiadm -m session' ->  Host shouldn't have any iscsi
        connections
        """
        assert self.host_iscsi_sessions(), (
            "Host %s does not have iscsi connections" % self.host
        )
        assert ll_hosts.deactivateHost(True, self.host), (
            "Unable to place host %s in maintenance mode" % self.host
        )
        assert self.timeout_sampling_iscsi_session(), (
            "Host %s has active iscsi connections" % self.host
        )


class BasicDeactivateStorageDomain(BaseTestCaseNewDC):
    add_nfs_domain = True

    def deactivate_last_iscsi_domain(self):
        assert self.host_iscsi_sessions(), (
            "Host %s does not have iscsi connections" % self.host
        )
        assert ll_sd.deactivateStorageDomain(
            True, self.dc, self.iscsi_domain
        ), (
            "Unable to place iscsi domain %s in maintenance mode"
            % self.iscsi_domain
        )
        assert self.timeout_sampling_iscsi_session(), (
            "Host %s has active iscsi connections" % self.host
        )


@attr(tier=2)
@pytest.mark.usefixtures("initializer_BaseTestCaseNewDC_fixture")
class TestCase11200(BasicDeactivateStorageDomain):
    """
    RHEVM3-11200 - Deactivate last iSCSI domain

    https://polarion.engineering.redhat.com/polarion/#/project/
    RHEVM3/workitem?id=RHEVM3-11200
    """
    __test__ = ISCSI in opts['storages']

    @polarion("RHEVM3-11200")
    def test_deactivate_storage_domain(self):
        """
        Test setup:
        - Have one active iSCSI domain and one other non-iSCSI domain

        Test flow:
        - Check that the host in the Data center has iscsi sessions with the
        iSCSI storage server with 'iscsiadm -m session' ->  Host should have
        iscsi connections
        - Place the iSCSI domain in maintenance mode
        - Run command 'iscsiadm -m session' ->
        Host shouldn't have any iscsi connections
        """
        self.deactivate_last_iscsi_domain()


@attr(tier=2)
@pytest.mark.usefixtures("initializer_BaseTestCaseNewDC_fixture")
class TestCase11230(BasicDeactivateStorageDomain):
    """
    RHEVM3-11230 -  Deactivate storage domain consisting of LUNs from several
                    storage servers

    https://polarion.engineering.redhat.com/polarion/#/project/
    RHEVM3/workitem?id=RHEVM3-11230
    """
    __test__ = ISCSI in opts['storages']

    @polarion("RHEVM3-11230")
    def test_deactivate_storage_domain_several_storage_servers(self):
        """
        Test setup:
        - One active iSCSI storage domain consisting of LUNS residing in more
        than one storage server. At least one non-iSCSI active domain

        Test flow:
        - Check that the host in the Data center has iscsi sessions with the
        iSCSI storage server with 'iscsiadm -m session' -> Host should
        have iscsi connections
        - Place the iSCSI domain in maintenance mode
        - Run command 'iscsiadm -m session' -> Host shouldn't have any iscsi
        connections
        """
        self.deactivate_last_iscsi_domain()


@attr(tier=2)
class TestCase11201(BaseTestCaseNewDC):
    """
    RHEVM3-11201 - Deactivate one of multiple domain

    https://polarion.engineering.redhat.com/polarion/#/project/
    RHEVM3/workitem?id=RHEVM3-11201
    """
    __test__ = ISCSI in opts['storages']

    @pytest.fixture(scope='function')
    def initializer_TestCase11201(self, request, initializer_module):
        """
        Add an aditional iscsi domain
        """
        request.addfinalizer(self.finalizer_BaseTestCaseNewDC)
        self.initializer_BaseTestCaseNewDC()
        self.iscsi_domain2 = storage_helpers.create_unique_object_name(
            self.__class__.__name__, config.OBJECT_TYPE_SD
        )
        if not hl_sd.addISCSIDataDomain(
            self.host, self.iscsi_domain2, self.dc,
            config.UNUSED_LUNS[1], config.UNUSED_LUN_ADDRESSES[1],
            config.UNUSED_LUN_TARGETS[1],
            override_luns=True, login_all=False,
        ):
            raise exceptions.StorageDomainException(
                "Unable to add iscsi domain %s, %s, %s to data center %s"
                % (
                    config.UNUSED_LUNS[1], config.UNUSED_LUN_ADDRESSES[1],
                    config.UNUSED_LUN_TARGETS[1], self.dc
                )
            )

    @pytest.mark.usefixtures("initializer_TestCase11201")
    @polarion("RHEVM3-11201")
    def test_deactivate_one_storage_domain(self):
        """
        Test setup:
        - 2 or more iSCSI domains should exist in the Data center

        Test flow:
        - Check that the host in the Data center has iscsi sessions with the
        iSCSI storage server with 'iscsiadm -m session'-> Host should have
        iscsi connections
        - Place one of the iSCSI domains in maintenance mode
        - Run command 'iscsiadm -m session' -> Host should have iscsi
        connections
        """
        assert self.host_iscsi_sessions(), (
            "Host %s does not have iscsi connections" % self.host
        )
        assert ll_sd.deactivateStorageDomain(
            True, self.dc, self.iscsi_domain2
        ), (
            "Unable to place iscsi domain %s in maintenance mode" %
            self.iscsi_domain2
        )
        assert self.host_iscsi_sessions(), (
            "Host %s does not have iscsi connections" % self.host
        )


@attr(tier=2)
class TestCase11257(BaseTestCaseNewDC):
    """
    RHEVM3-11257 -  iSCSI logout after storage domain detachment

    https://polarion.engineering.redhat.com/polarion/#/project/
    RHEVM3/workitem?id=RHEVM3-11257
    """
    __test__ = ISCSI in opts['storages']
    add_nfs_domain = True

    @pytest.fixture(scope='function')
    def initializer_TestCase11257(self, request, initializer_module):
        """
        Add finalizer
        """
        def finalizer_TestCase11257():
            """
            Remove iscsi domain
            """
            if not ll_sd.removeStorageDomain(
                True, self.iscsi_domain, self.host, format='true'
            ):
                self.test_failed = True
                logger.error(
                    "Unable to remove iscsi domain %s", self.iscsi_domain
                )
            self.finalizer_BaseTestCaseNewDC()

        self.initializer_BaseTestCaseNewDC()
        request.addfinalizer(finalizer_TestCase11257)

    @polarion("RHEVM3-11257")
    @pytest.mark.usefixtures("initializer_TestCase11257")
    def test_storage_domain_detachment(self):
        """
        Test setup:
        - One iSCSI domain should exist in the Data center

        Test flow:
        - Check that the host in the Data center has iscsi sessions with the
        iSCSI storage server with 'iscsiadm -m session' -> Host should have
        iscsi connections
        - Place one of the iSCSI domains in maintenance mode
        - Run command 'iscsiadm -m session'
        - Detach the domain from the DC
        - Once the remove task is finished, run command'iscsiadm -m session' ->
        Host shouldn't have iscsi connections
        """
        assert self.host_iscsi_sessions(), (
            "Host %s does not have iscsi connections" % self.host
        )
        assert ll_sd.deactivateStorageDomain(
            True, self.dc, self.iscsi_domain
        ), "Unable to place iscsi domain %s in maintenance mode" % (
            self.iscsi_domain
        )
        assert self.timeout_sampling_iscsi_session(), (
            "Host %s has active iscsi connections" % self.host
        )
        assert ll_sd.detachStorageDomain(True, self.dc, self.iscsi_domain), (
            "Unable to detach iscsi domain %s" % self.iscsi_domain
        )
        wait_for_tasks(config.VDC_HOST, config.VDC_ROOT_PASSWORD, self.dc)
        assert self.timeout_sampling_iscsi_session(), (
            "Host %s has active iscsi connections" % self.host
        )


@attr(tier=2)
@pytest.mark.usefixtures("initializer_BaseTestCaseNewDC_fixture")
class TestCase11233(BaseTestCaseNewDC):
    """
    RHEVM3-11233 - iSCSI logout after storage domain is removed (using
                   the format option)

    https://polarion.engineering.redhat.com/polarion/#/project/
    RHEVM3/workitem?id=RHEVM3-11233
    """
    __test__ = ISCSI in opts['storages']
    add_nfs_domain = True

    @polarion("RHEVM3-11233")
    def test_storage_domain_detachment(self):
        """
        Test flow:
        - 2 or more iSCSI domains should exist in the Data center

        Test setup:
        - Check that the host in the Data center has iscsi sessions with the
        iSCSI storage server with 'iscsiadm -m session' -> Host should have
        iscsi connections
        - Place one of the iSCSI domains in maintenance mode
        - Detach the domain from the DC
        - Once the remove domain task has completed, run command
        'iscsiadm -m session' -> Host shouldn't have iscsi connections
        """
        assert self.host_iscsi_sessions(), (
            "Host %s does not have iscsi connections" % self.host
        )
        assert ll_sd.deactivateStorageDomain(
            True, self.dc, self.iscsi_domain
        ), (
            "Unable to place iscsi domain %s in maintenance mode" %
            self.iscsi_domain
        )
        assert ll_sd.detachStorageDomain(True, self.dc, self.iscsi_domain), (
            "Unable to detach iscsi domain %s" % self.iscsi_domain
        )
        assert ll_sd.removeStorageDomain(
            True, self.iscsi_domain, self.host, format='true'
        ), "Unable to remove iscsi domain %s" % self.iscsi_domain
        wait_for_tasks(config.VDC_HOST, config.VDC_ROOT_PASSWORD, self.dc)
        assert self.timeout_sampling_iscsi_session(), (
            "Host %s has active iscsi connections" % self.host
        )


@attr(tier=2)
@pytest.mark.usefixtures("initializer_BaseTestCaseNewDC_fixture")
class TestCase11231(BaseTestCaseNewDC):
    """
    RHEVM3-11231 -  iSCSI logout after removal of the last direct LUN

    https://polarion.engineering.redhat.com/polarion/#/project/
    RHEVM3/workitem?id=RHEVM3-11231
    """
    __test__ = ISCSI in opts['storages']
    add_nfs_domain = True
    add_iscsi_domain = False

    @polarion("RHEVM3-11231")
    def test_remove_lun(self):
        """
        Test setup:
        - One or more active non-iSCSI active storage domain

        Test flow:
        - Add a direct LUN disk to the Data Center
        - Check that the host in the Data center has iscsi sessions with the
        iSCSI storage server with 'iscsiadm -m session' -> Host should have
        iscsi connections
        - Remove the direct LUN
        - Run command 'iscsiadm -m session' -> Host should have iscsi
        connections
        """
        self.lun_alias = storage_helpers.create_unique_object_name(
            self.__class__.__name__, config.OBJECT_TYPE_DISK
        )
        self.lun_kwargs = {
            "lun_address": config.UNUSED_LUN_ADDRESSES[0],
            "lun_target": config.UNUSED_LUN_TARGETS[0],
            "lun_id": config.UNUSED_LUNS[0],
            "interface": config.VIRTIO_SCSI,
            "alias":  self.lun_alias,
            "type_": ISCSI,
        }
        assert hl_sd._ISCSIdiscoverAndLogin(
            self.host, config.UNUSED_LUN_ADDRESSES[0],
            config.UNUSED_LUN_TARGETS[0]
        ), "Unable to discover and login targets for %s, %s on host %s" % (
            config.UNUSED_LUN_ADDRESSES[0], config.UNUSED_LUN_TARGETS[0],
            self.host
        )
        assert ll_disks.addDisk(True, **self.lun_kwargs), (
            "Failed to add direct LUN %s" % self.lun_alias
        )
        ll_jobs.wait_for_jobs([config.JOB_ADD_DISK])
        assert self.host_iscsi_sessions(), (
            "Host %s does not have iscsi connections" % self.host
        )
        assert ll_disks.deleteDisk(True, self.lun_alias), (
            "Failed to remove LUN %s" % self.lun_alias
        )
        ll_jobs.wait_for_jobs([config.JOB_REMOVE_DISK])
        assert self.host_iscsi_sessions(), (
            "Host %s does not have iscsi connections" % self.host
        )


# TODO: Wait for infra to make storage_api ready and implement CHAP
# authentication https://projects.engineering.redhat.com/browse/RHEVM-2638
"""
RHEVM3-11232 - Connect to an existing storage with new credentials
               (direct LUN)
"""
"""
RHEVM3-11215 - Connect to an existing storage with new credentials
               (storage domain)
"""
"""
RHEVM3-11216 - Check LUNs list after host is unmapped from devices
"""
"""
RHEVM3-11588 - Update vdsm after removal of LUN
"""
