"""
3.6 Storage iSCSI disconnect scenarios
https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
Storage/3_6_Storage_iSCSI_disconnect_scenarios
"""
import config
import logging
import pytest

from art.rhevm_api.tests_lib.high_level import (
    storagedomains as hl_sd,
    datacenters as hl_dc,
    hosts as hl_hosts,
)
from art.rhevm_api.tests_lib.low_level import (
    disks as ll_disks,
    hosts as ll_hosts,
    jobs as ll_jobs,
    storagedomains as ll_sd,
    datacenters as ll_dc,
    clusters as ll_clusters,
)
from rrmngmnt.host import Host
from rrmngmnt.user import User
from art.core_api.apis_utils import TimeoutingSampler
from art.core_api.apis_exceptions import APITimeout
from art.rhevm_api.utils.test_utils import wait_for_tasks
from art.test_handler import exceptions
from art.test_handler.settings import ART_CONFIG
from art.test_handler.tools import polarion  # pylint: disable=E0611
from art.unittest_lib import (
    tier2,
    tier3,
    StorageTest,
    testflow,
)
import rhevmtests.storage.helpers as storage_helpers

from fixtures import (
    create_environment_logout_session, activate_host,
    add_additional_iscsi_domain, remove_storage_domains,
)
from fixtures import a0_initialize_variables_clean_storages  # noqa

logger = logging.getLogger(__name__)
ISCSI = config.STORAGE_TYPE_ISCSI
ISCSIADM_SESSION = ["iscsiadm", "-m", "session"]
ISCSIADM_LOGOUT = ["iscsiadm", "-m", "session", "-u"]

# The iscsi session can be open up to 30 seconds after the operation is
# executed (deactivate domain, remove direct LUN disk, ...)
TIME_UNTIL_ISCSI_SESSION_DISAPPEARS = 30


class BaseTestCase(StorageTest):
    storages = set([ISCSI])
    add_iscsi_domain = True
    add_nfs_domain = False
    login_all = False

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

    @classmethod
    def host_iscsi_sessions(cls):
        """
        Return the output from executing "iscsiadm -m session" command
        """
        rc, out, error = cls.host_executor.run_command(ISCSIADM_SESSION)
        if rc:
            if "No active sessions" in error:
                return []
            else:
                logger.error(
                    "Unable execute %s command on host %s", ISCSIADM_SESSION,
                    cls.host
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
        wait_for_tasks(config.ENGINE, self.dc)
        if not hl_dc.clean_datacenter(
            True, datacenter=self.dc, format_exp_storage=True,
            engine=config.ENGINE
        ):
            self.test_failed = True
            logger.error(
                "Failed to clean Data center '%s'", self.dc
            )
        if not ll_hosts.add_host(
            name=self.host, address=self.host_ip,
            wait=True, cluster=config.CLUSTER_NAME,
            root_password=config.VDC_ROOT_PASSWORD
        ):
            self.test_failed = True
            logger.error(
                "Failed to add host '%s' into cluster '%s'",
                self.host, config.CLUSTER_NAME
            )
        BaseTestCase.teardown_exception()

    @pytest.fixture(scope='function')  # noqa: F811
    def initializer_BaseTestCaseNewDC_fixture(
        self, request, a0_initialize_variables_clean_storages
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
            if not hl_sd.add_iscsi_data_domain(
                self.host, self.iscsi_domain, self.dc,
                config.ISCSI_DOMAINS_KWARGS[0]['lun'],
                config.ISCSI_DOMAINS_KWARGS[0]['lun_address'],
                config.ISCSI_DOMAINS_KWARGS[0]['lun_target'],
                override_luns=True, login_all=self.login_all
            ):
                raise exceptions.StorageDomainException(
                    "Unable to add iscsi domain %s, %s, %s to data center %s"
                    % (
                        config.ISCSI_DOMAINS_KWARGS[0]['lun'],
                        config.ISCSI_DOMAINS_KWARGS[0]['lun_address'],
                        config.ISCSI_DOMAINS_KWARGS[0]['lun_target'], self.dc
                    )
                )
        self.nfs_domain = storage_helpers.create_unique_object_name(
            self.__class__.__name__, config.OBJECT_TYPE_SD
        )
        if self.add_nfs_domain:
            if not hl_sd.addNFSDomain(
                self.host, self.nfs_domain, self.dc,
                config.NFS_DOMAINS_KWARGS[0]['address'],
                config.NFS_DOMAINS_KWARGS[0]['path'],
                format=True, activate=True
            ):
                raise exceptions.StorageDomainException(
                    "Unable to add nfs domain %s, %s, to data center %s"
                    % (
                        config.NFS_DOMAINS_KWARGS[0]['address'],
                        config.NFS_DOMAINS_KWARGS[0]['path'], self.dc
                    )
                )


@pytest.mark.usefixtures(
    create_environment_logout_session.__name__,
    activate_host.__name__,
)
class TestCase11196(BaseTestCase):
    """
    RHEVM3-11196 - Place host in maintenance mode

    https://polarion.engineering.redhat.com/polarion/#/project/
    RHEVM3/workitem?id=RHEVM3-11196
    """
    __test__ = ISCSI in ART_CONFIG['RUN']['storages']

    @tier2
    @polarion("RHEVM3-11196")
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
        wait_for_tasks(engine=config.ENGINE, datacenter=self.dc)
        testflow.step("Deactivate host %s", self.host)
        assert ll_hosts.deactivate_host(True, self.host), (
            "Unable to place host %s in maintenance mode" % self.host
        )
        assert self.timeout_sampling_iscsi_session(), (
            "Host %s has active iscsi connections" % self.host
        )


class BasicDeactivateStorageDomain(BaseTestCase):
    add_nfs_domain = True

    def deactivate_last_iscsi_domain(self):
        assert self.host_iscsi_sessions(), (
            "Host %s does not have iscsi connections" % self.host
        )
        testflow.step("Deactivate storage domain %s", self.iscsi_domain)
        assert ll_sd.deactivateStorageDomain(
            True, self.dc, self.iscsi_domain
        ), (
            "Unable to place iscsi domain %s in maintenance mode"
            % self.iscsi_domain
        )
        assert self.timeout_sampling_iscsi_session(), (
            "Host %s has active iscsi connections" % self.host
        )


@pytest.mark.usefixtures(
    create_environment_logout_session.__name__,
)
class TestCase11200(BasicDeactivateStorageDomain):
    """
    RHEVM3-11200 - Deactivate last iSCSI domain

    https://polarion.engineering.redhat.com/polarion/#/project/
    RHEVM3/workitem?id=RHEVM3-11200
    """
    __test__ = ISCSI in ART_CONFIG['RUN']['storages']

    @tier2
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


@pytest.mark.usefixtures(
    create_environment_logout_session.__name__,
)
class TestCase11230(BasicDeactivateStorageDomain):
    """
    RHEVM3-11230 -  Deactivate storage domain consisting of LUNs from several
                    storage servers

    https://polarion.engineering.redhat.com/polarion/#/project/
    RHEVM3/workitem?id=RHEVM3-11230
    """
    __test__ = ISCSI in ART_CONFIG['RUN']['storages']

    @tier2
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


@pytest.mark.usefixtures(
    create_environment_logout_session.__name__,
    add_additional_iscsi_domain.__name__,
)
class TestCase11201(BaseTestCaseNewDC):
    """
    RHEVM3-11201 - Deactivate one of multiple domain

    https://polarion.engineering.redhat.com/polarion/#/project/
    RHEVM3/workitem?id=RHEVM3-11201
    """
    __test__ = ISCSI in ART_CONFIG['RUN']['storages']

    @tier3
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
        testflow.step("Deactivate storage domain %s", self.iscsi_domain2)
        assert ll_sd.deactivateStorageDomain(
            True, self.dc, self.iscsi_domain2
        ), (
            "Unable to place iscsi domain %s in maintenance mode" %
            self.iscsi_domain2
        )
        assert self.host_iscsi_sessions(), (
            "Host %s does not have iscsi connections" % self.host
        )


@pytest.mark.usefixtures(
    create_environment_logout_session.__name__,
    remove_storage_domains.__name__,
)
class TestCase11257(BaseTestCase):
    """
    RHEVM3-11257 -  iSCSI logout after storage domain detachment

    https://polarion.engineering.redhat.com/polarion/#/project/
    RHEVM3/workitem?id=RHEVM3-11257
    """
    __test__ = ISCSI in ART_CONFIG['RUN']['storages']
    add_nfs_domain = True

    @tier2
    @polarion("RHEVM3-11257")
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
        wait_for_tasks(engine=config.ENGINE, datacenter=self.dc)
        testflow.step("Deactivate storage domain %s", self.iscsi_domain)
        assert ll_sd.deactivateStorageDomain(
            True, self.dc, self.iscsi_domain
        ), "Unable to place iscsi domain %s in maintenance mode" % (
            self.iscsi_domain
        )
        assert self.timeout_sampling_iscsi_session(), (
            "Host %s has active iscsi connections" % self.host
        )
        testflow.step("Detaching storage domain %s", self.iscsi_domain)
        assert ll_sd.detachStorageDomain(True, self.dc, self.iscsi_domain), (
            "Unable to detach iscsi domain %s" % self.iscsi_domain
        )
        wait_for_tasks(engine=config.ENGINE, datacenter=self.dc)
        assert self.timeout_sampling_iscsi_session(), (
            "Host %s has active iscsi connections" % self.host
        )


@pytest.mark.usefixtures(
    create_environment_logout_session.__name__,
)
class TestCase11233(BaseTestCase):
    """
    RHEVM3-11233 - iSCSI logout after storage domain is removed (using
                   the format option)

    https://polarion.engineering.redhat.com/polarion/#/project/
    RHEVM3/workitem?id=RHEVM3-11233
    """
    __test__ = ISCSI in ART_CONFIG['RUN']['storages']
    add_nfs_domain = True

    @tier2
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
        testflow.step("Deactivate host %s", self.host)
        assert ll_sd.deactivateStorageDomain(
            True, self.dc, self.iscsi_domain
        ), (
            "Unable to place iscsi domain %s in maintenance mode" %
            self.iscsi_domain
        )
        testflow.step("Detaching storage domain %s", self.iscsi_domain)
        assert ll_sd.detachStorageDomain(True, self.dc, self.iscsi_domain), (
            "Unable to detach iscsi domain %s" % self.iscsi_domain
        )
        testflow.step("Removing storage domain %s", self.iscsi_domain)
        assert ll_sd.removeStorageDomain(
            True, self.iscsi_domain, self.host, format='true'
        ), "Unable to remove iscsi domain %s" % self.iscsi_domain
        wait_for_tasks(engine=config.ENGINE, datacenter=self.dc)
        assert self.timeout_sampling_iscsi_session(), (
            "Host %s has active iscsi connections" % self.host
        )


@pytest.mark.usefixtures(
    create_environment_logout_session.__name__,
)
class TestCase11231(BaseTestCase):
    """
    RHEVM3-11231 -  iSCSI logout after removal of the last direct LUN

    https://polarion.engineering.redhat.com/polarion/#/project/
    RHEVM3/workitem?id=RHEVM3-11231
    """
    __test__ = ISCSI in ART_CONFIG['RUN']['storages']
    add_nfs_domain = True
    add_iscsi_domain = False

    @tier2
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
            "lun_address": config.ISCSI_DOMAINS_KWARGS[0]['lun_address'],
            "lun_target": config.ISCSI_DOMAINS_KWARGS[0]['lun_target'],
            "lun_id": config.ISCSI_DOMAINS_KWARGS[0]['lun'],
            "interface": config.VIRTIO_SCSI,
            "alias":  self.lun_alias,
            "type_": ISCSI,
        }
        assert hl_sd._ISCSIdiscoverAndLogin(
            self.host, config.ISCSI_DOMAINS_KWARGS[0]['lun_address'],
            config.ISCSI_DOMAINS_KWARGS[0]['lun_target']
        ), "Unable to discover and login targets for %s, %s on host %s" % (
            config.ISCSI_DOMAINS_KWARGS[0]['lun_address'],
            config.ISCSI_DOMAINS_KWARGS[0]['lun_target'],
            self.host
        )
        testflow.step("Adding LUN disk %s", self.lun_alias)
        assert ll_disks.addDisk(True, **self.lun_kwargs), (
            "Failed to add direct LUN %s" % self.lun_alias
        )
        ll_jobs.wait_for_jobs([config.JOB_ADD_DISK])
        assert self.host_iscsi_sessions(), (
            "Host %s does not have iscsi connections" % self.host
        )
        testflow.step("Removing LUN disk %s", self.lun_alias)
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
