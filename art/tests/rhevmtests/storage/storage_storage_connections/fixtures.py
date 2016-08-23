import logging
import config
import helpers
import pytest
from art.rhevm_api.utils import test_utils
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
    storagedomains as ll_sd,
    storageconnections as ll_storageconnections,
    vms as ll_vms,
    templates as ll_templates,
    jobs as ll_jobs,
)
from art.unittest_lib import testflow

import rhevmtests.storage.helpers as storage_helpers
import rhevmtests.helpers as rhevm_helpers

logger = logging.getLogger(__name__)

ISCSI_SDS = []


@pytest.fixture(scope='module', autouse=True)
def a0_initialize_variables_clean_storages(request):
    """
    Initialize host and storage variables for tests.
    Clean the storage domains used
    """
    def finalizer():
        """
        Import back iscsi storage domains
        """
        if config.STORAGE_TYPE_ISCSI not in config.STORAGE_SELECTOR:
            return
        testflow.teardown("Importing iscsi storage domains back")
        # Importing all iscsi domains using the address and target of one of
        # them
        assert hl_sd.import_iscsi_storage_domain(
            config.HOST_FOR_MOUNT, config.LUN_ADDRESSES[0],
            config.LUN_TARGETS[0]
        ), "Failed to import iSCSI domains back"

        register_failed = False

        for sd in ISCSI_SDS:
            testflow.teardown("Attach and activate storage domain %s", sd)
            hl_sd.attach_and_activate_domain(config.DATA_CENTER_NAME, sd)

            testflow.teardown(
                "Copying templates disks to imported storage domain %s", sd
            )
            ll_templates.copyTemplateDisk(
                config.TEMPLATE_NAME[0], config.GOLDEN_GLANCE_IMAGE, sd
            )
            ll_jobs.wait_for_jobs([config.JOB_MOVE_COPY_DISK])
            ll_disks.wait_for_disks_status([config.GOLDEN_GLANCE_IMAGE])

            testflow.teardown(
                "importing VMs back to imported storage domain %s", sd
            )
            unregistered_vms = ll_sd.get_unregistered_vms(sd)
            if unregistered_vms:
                for vm in unregistered_vms:
                    if not ll_sd.register_object(
                        vm, cluster=config.CLUSTER_NAME
                    ):
                        logger.error(
                            "Failed to register vm %s from imported "
                            "domain %s", vm, sd
                        )
                        register_failed = True
            assert not register_failed, "Register of vms failed"

    request.addfinalizer(finalizer)
    config.HOST_FOR_MOUNT = config.HOSTS[-1]
    config.HOST_FOR_MOUNT_IP = ll_hosts.get_host_ip(config.HOST_FOR_MOUNT)
    config.HOSTS_FOR_TEST = config.HOSTS[:]
    config.HOSTS_FOR_TEST.remove(config.HOST_FOR_MOUNT)

    if config.STORAGE_TYPE_ISCSI not in config.STORAGE_SELECTOR:
        return

    rhevm_helpers.storage_cleanup()

    config.CONNECTIONS.append(config.ISCSI_STORAGE_ENTRIES.copy())
    config.CONNECTIONS.append(config.ISCSI_STORAGE_ENTRIES.copy())
    # After each test, we logout from all the targets by looping through
    # CONNECTIONS. Add the default target/ip so the host will also logout
    # from it
    config.CONNECTIONS.append({
        'lun_address': config.ISCSI_DOMAINS_KWARGS[0]['lun_address'],
        'lun_target':  config.ISCSI_DOMAINS_KWARGS[0]['lun_target'],
    })
    # TODO: Remove all setup_module and teardown_module when
    # https://bugzilla.redhat.com/show_bug.cgi?id=1146115 is fixed
    # All of the storage connections need to be removed, and the host
    # should be logged out from all targets for these tests. This is due
    # to the fact that when adding a new storage domain or direct lun,
    # ovirt will automatically link the storage  domains with the existing
    # host's logged targets
    global ISCSI_SDS
    testflow.setup("Removing all iscsi storage domains for test")
    ISCSI_SDS = ll_sd.getStorageDomainNamesForType(
        config.DATA_CENTER_NAME, config.STORAGE_TYPE_ISCSI
    )
    test_utils.wait_for_tasks(
        engine=config.ENGINE, datacenter=config.DATA_CENTER_NAME
    )
    for sd in ISCSI_SDS:
        hl_sd.detach_and_deactivate_domain(
            config.DATA_CENTER_NAME, sd, config.ENGINE
        )
        assert ll_sd.removeStorageDomain(
            positive=True, storagedomain=sd, host=config.HOST_FOR_MOUNT,
            format='false'
        )
    testflow.setup("Logging out from all iscsi targets")
    helpers.logout_from_all_iscsi_targets()


@pytest.fixture()
def logout_all_iscsi_targets(request, storage):
    """
    Log out all iscsi targets
    """
    def finalizer():
        testflow.teardown("Logging out from all iscsi targets")
        helpers.logout_from_all_iscsi_targets()
    request.addfinalizer(finalizer)


@pytest.fixture()
def remove_storage_domains(request, storage):
    """
    Remove storage domains
    """
    self = request.node.cls

    def finalizer():
        testflow.teardown("Removing storage domains")
        for storage_domain in self.storage_domains:
            assert ll_sd.removeStorageDomain(
                True, storage_domain, config.HOST_FOR_MOUNT, 'true'
            ), "Error removing %s" % self.sd_name
    request.addfinalizer(finalizer)

    if not hasattr(self, 'storage_domains'):
        self.storage_domains = list()


@pytest.fixture()
def remove_storage_connections(request, storage):
    """
    Remove storage_connection
    """
    def finalizer():
        testflow.teardown("Removing all iscsi storage connections")
        for conn in ll_storageconnections.get_all_storage_connections():
            if conn.get_type() == config.STORAGE_TYPE_ISCSI:
                ll_storageconnections.remove_storage_connection(conn.id)
    request.addfinalizer(finalizer)


@pytest.fixture(scope='class')
def add_storage_connections(request, storage):
    """
    Add two storage connections
    """
    self = request.node.cls

    def finalizer():
        """
        Remove the storage connections
        """
        ll_storageconnections.remove_storage_connection(self.conn_1.id)
        ll_storageconnections.remove_storage_connection(self.conn_2.id)

    request.addfinalizer(finalizer)
    conn = dict(config.CONNECTIONS[0]).copy()
    conn['type'] = config.STORAGE_TYPE_ISCSI
    self.conn_1, success = ll_storageconnections.add_connection(**conn)
    assert success, "Adding storage connection failed %s" % conn

    conn = dict(config.CONNECTIONS[1]).copy()
    conn['type'] = config.STORAGE_TYPE_ISCSI
    self.conn_2_params = conn
    self.conn_2, success = ll_storageconnections.add_connection(**conn)
    assert success, "Adding storage connection failed %s" % conn


@pytest.fixture()
def add_storage_domain_and_connections(
    request, storage, add_two_storage_domains
):
    """
    Add one storage domain and then another 2 storage domains that all use
    the same storage connection
    """
    self = request.node.cls

    def finalizer():
        test_utils.wait_for_tasks(
            engine=config.ENGINE,
            datacenter=config.DATACENTER_ISCSI_CONNECTIONS
        )
        if self.sd_name_1 is not None and self.sd_name_2 is not None:
            conn = dict(config.CONNECTIONS[0]).copy()
            conn['type'] = config.STORAGE_TYPE_ISCSI
            conn_1, success = ll_storageconnections.add_connection(**conn)
            if success:
                ll_sd.addConnectionToStorageDomain(self.sd_name_1, conn_1.id)
                ll_sd.addConnectionToStorageDomain(self.sd_name_2, conn_1.id)

    request.addfinalizer(finalizer)

    testflow.setup("Adding NFS domain")
    self.master_sd = storage_helpers.create_unique_object_name(
        self.__name__, config.OBJECT_TYPE_SD
    )
    assert ll_sd.addStorageDomain(
        True, host=config.HOST_FOR_MOUNT, name=self.master_sd,
        type=config.TYPE_DATA, storage_type=config.STORAGE_TYPE_NFS,
        address=config.NFS_DOMAINS_KWARGS[0]['address'],
        path=config.NFS_DOMAINS_KWARGS[0]['path']
    )
    assert ll_sd.attachStorageDomain(
        True, config.DATACENTER_ISCSI_CONNECTIONS, self.master_sd
    )


@pytest.fixture(scope='class')
def generate_random_storage_connections(request, storage):
    """
    Add multiple storage connections for testing
    """
    self = request.node.cls

    def finalizer():
        for conn in self.conns:
            ll_storageconnections.remove_storage_connection(conn.id)

    request.addfinalizer(finalizer)
    testflow.setup("Adding %s fake storage connections", self.no_of_conn)
    # put random str to iqn, we are not going to use the connection anyhow
    for i in range(self.no_of_conn):
        conn = dict(config.CONNECTIONS[0]).copy()
        conn['lun_target'] = 'sth%d.%s' % (i, conn['lun_target'])
        conn['type'] = config.STORAGE_TYPE_ISCSI
        self.con_params.append(conn)
        conn, success = ll_storageconnections.add_connection(**conn)
        assert success, (
            "Adding storage connection failed"
        )
        self.conns.append(conn)


@pytest.fixture()
def initialize_variables_remove_leftover_domains(request, storage):
    """
    Initialize variables and remove leftover domains
    """
    self = request.node.cls

    def finalizer():
        """
        Remove leftover disks, storage domains and storage connections
        """
        for alias in self.disks:
            ll_disks.deleteDisk(True, alias)
        for storage_domain in self.storage_domains:
            ll_sd.removeStorageDomain(
                True, storage_domain, config.HOST_FOR_MOUNT, 'true'
            )
        for storage_connection in self.storage_connections:
            ll_storageconnections.remove_storage_connection(storage_connection)
    request.addfinalizer(finalizer)
    self.disks = []
    self.storage_domains = []
    self.storage_connections = []
    self.original_conn = (
        ll_storageconnections.get_all_storage_connections()
    )


@pytest.fixture()
def empty_dc(request, storage):
    """
    Remove Data Center and logs out from all iscsi targets
    """
    def finalizer():
        """
        Remove the Data center, wiping all storage domains on it, re-create the
        data center with its cluster and host
        """
        dc_name = config.DATACENTER_ISCSI_CONNECTIONS
        cluster_name = config.CLUSTER_ISCSI_CONNECTIONS
        testflow.teardown("Removing Datacenter %s", dc_name)
        assert hl_dc.clean_datacenter(
            True, datacenter=dc_name, format_exp_storage='true',
            engine=config.ENGINE
        )
        assert ll_dc.addDataCenter(
            True, name=dc_name, version=config.COMP_VERSION
        )
        assert ll_clusters.addCluster(
            True, name=cluster_name,  cpu=config.CPU_NAME, data_center=dc_name,
            version=config.COMP_VERSION
        )
        assert ll_hosts.add_host(
            config.HOST_FOR_MOUNT, address=config.HOST_FOR_MOUNT_IP,
            wait=True, cluster=config.CLUSTER_ISCSI_CONNECTIONS,
            root_password=config.VDC_ROOT_PASSWORD
        )
    request.addfinalizer(finalizer)


@pytest.fixture()
def add_two_storage_domains(request, storage):
    """
    Add and attach two storage domains
    """
    self = request.node.cls

    testflow.setup("Adding two storage domains")
    self.sd_name_1 = storage_helpers.create_unique_object_name(
        self.__name__, config.OBJECT_TYPE_SD
    )
    assert ll_sd.addStorageDomain(
        True, host=config.HOST_FOR_MOUNT, name=self.sd_name_1,
        type=config.TYPE_DATA, storage_type=config.STORAGE_TYPE_ISCSI,
        override_luns=True, lun=config.CONNECTIONS[0]['luns'][0],
        **(config.CONNECTIONS[0])
    ), "Failed to create storage domain '%s'" % self.sd_name_1
    self.sd_name_2 = storage_helpers.create_unique_object_name(
        self.__name__, config.OBJECT_TYPE_SD
    )
    assert ll_sd.addStorageDomain(
        True, host=config.HOST_FOR_MOUNT, name=self.sd_name_2,
        type=config.TYPE_DATA, storage_type=config.STORAGE_TYPE_ISCSI,
        override_luns=True, lun=config.CONNECTIONS[0]['luns'][1],
        **(config.CONNECTIONS[0])
    ), "Failed to create storage domain '%s'" % self.sd_name_2
    assert ll_sd.attachStorageDomain(
        True, config.DATACENTER_ISCSI_CONNECTIONS, self.sd_name_1
    ), (
        "Failed to attach storage domain '%s' into Data center '%s'" %
        (self.sd_name_1, config.DATACENTER_ISCSI_CONNECTIONS)
    )
    assert ll_sd.attachStorageDomain(
        True, config.DATACENTER_ISCSI_CONNECTIONS, self.sd_name_2
    ), (
        "Failed to attach storage domain '%s' into Data center '%s'" %
        (self.sd_name_1, config.DATACENTER_ISCSI_CONNECTIONS)
    )
    ll_sd.wait_for_storage_domain_status(
        True, config.DATACENTER_ISCSI_CONNECTIONS, self.sd_name_1,
        config.SD_ACTIVE
    )
    ll_sd.wait_for_storage_domain_status(
        True, config.DATACENTER_ISCSI_CONNECTIONS, self.sd_name_2,
        config.SD_ACTIVE
    )


@pytest.fixture()
def add_new_storage_connection(request, storage):
    """
    Add a new connection
    """
    self = request.node.cls

    conn = dict(config.CONNECTIONS[self.conn_idx]).copy()
    conn['type'] = config.STORAGE_TYPE_ISCSI
    self.conn, success = ll_storageconnections.add_connection(**conn)
    assert success, "Failed to add storage connection '%s'" % conn
    self.original_conn = (
        ll_storageconnections.get_all_storage_connections()
    )


@pytest.fixture()
def add_nfs_domain_generate_vms(request, storage):
    """
    Add a nfs domain and vms
    """
    self = request.node.cls

    testflow.setup(
        "Adding one storage domain with vms with disks on those domains"
    )
    self.vm_names = list()
    self.vm_name_1 = storage_helpers.create_unique_object_name(
        self.__name__, config.OBJECT_TYPE_VM
    )
    self.disk_1 = storage_helpers.create_unique_object_name(
        self.__name__, config.OBJECT_TYPE_DISK
    )
    self.sd_name = storage_helpers.create_unique_object_name(
        self.__name__, config.OBJECT_TYPE_SD
    )
    assert ll_sd.addStorageDomain(
        True, host=config.HOST_FOR_MOUNT, name=self.sd_name,
        type=config.TYPE_DATA, storage_type=config.STORAGE_TYPE_NFS,
        address=config.NFS_DOMAINS_KWARGS[0]['address'],
        path=config.NFS_DOMAINS_KWARGS[0]['path']
    ), (
        "Failed to create storage domain '%s'" % self.sd_name
    )
    assert ll_sd.attachStorageDomain(
        True, config.DATACENTER_ISCSI_CONNECTIONS, self.sd_name
    ), (
        "Failed to attach storage domain '%s' into Data center '%s'" %
        (self.sd_name, config.DATACENTER_ISCSI_CONNECTIONS)
    )
    ll_sd.wait_for_storage_domain_status(
        True, config.DATACENTER_ISCSI_CONNECTIONS, self.sd_name,
        config.SD_ACTIVE
    )
    self.vm_name_2 = storage_helpers.create_unique_object_name(
        self.__name__, config.OBJECT_TYPE_VM
    )
    self.disk_2 = storage_helpers.create_unique_object_name(
        self.__name__, config.OBJECT_TYPE_DISK
    )
    for vm_name in (self.vm_name_1, self.vm_name_2):
        vm_args_copy = config.create_vm_args.copy()
        vm_args_copy['cluster'] = config.CLUSTER_ISCSI_CONNECTIONS
        vm_args_copy['installation'] = False
        vm_args_copy['provisioned_size'] = config.GB
        vm_args_copy['storageDomainName'] = self.sd_name
        vm_args_copy['vmName'] = vm_name
        vm_args_copy['vmDescription'] = vm_name
        assert storage_helpers.create_vm_or_clone(**vm_args_copy), (
            'Unable to create vm %s for test' % vm_name
        )
        logger.info('Shutting down VM %s', vm_name)
        self.vm_names.append(vm_name)

    assert ll_disks.addDisk(
        True, alias=self.disk_1,
        interface=config.VIRTIO,
        format=config.DISK_FORMAT_COW,
        lun_id=config.CONNECTIONS[0]['luns'][1],
        lun_address=config.CONNECTIONS[0]['lun_address'],
        lun_target=config.CONNECTIONS[0]['lun_target'],
        type_=config.STORAGE_TYPE_ISCSI
    ), (
        "Failed to create disk '%s'" % self.disk_1
    )
    assert ll_disks.addDisk(
        True, alias=self.disk_2,
        interface=config.VIRTIO,
        format=config.DISK_FORMAT_COW,
        lun_id=config.CONNECTIONS[0]['luns'][2],
        lun_address=config.CONNECTIONS[0]['lun_address'],
        lun_target=config.CONNECTIONS[0]['lun_target'],
        type_=config.STORAGE_TYPE_ISCSI
    ), (
        "Failed to create disk '%s'" % self.disk_2
    )
    assert ll_disks.attachDisk(True, self.disk_1, self.vm_name_1), (
        "Failed to attach disk '%s' to VM '%s'" % (
            self.disk_1, self.vm_name_1
        )
    )
    assert ll_disks.attachDisk(True, self.disk_2, self.vm_name_2), (
        "Failed to attach disk '%s' to VM '%s'" % (
            self.disk_2, self.vm_name_2
        )
    )
    assert ll_vms.startVms([self.vm_name_1, self.vm_name_2], config.VM_UP), (
        "Failed to power on vms %s" %
        ', '.join([self.vm_name_1, self.vm_name_2])
    )


@pytest.fixture()
def remove_added_storages_and_clean_connections(request, storage):
    """
    Remove added storage domains
    """
    self = request.node.cls

    def finalizer():
        testflow.teardown("Removing storage domains")
        for storage_domain in self.storage_domains:
            ll_sd.removeStorageDomain(
                True, storage_domain, config.HOST_FOR_MOUNT, 'true'
            )
        testflow.teardown("Removing storage connections")
        if self.conn.id in [
            connection.id for connection in
            ll_storageconnections.get_all_storage_connections()
        ]:
            ll_storageconnections.remove_storage_connection(self.conn.id)
        testflow.teardown("Logging out from all iscsi targets")
        helpers.logout_from_all_iscsi_targets()
    request.addfinalizer(finalizer)


@pytest.fixture(scope='class')
def create_environment_logout_session(request, storage):
    """
    Create environment and logout ISCSI sessions
    """
    self = request.node.cls

    def finalizer():
        testflow.teardown("Removing Datacenter %s", self.dc)
        test_utils.wait_for_tasks(
            engine=config.ENGINE, datacenter=self.dc
        )
        assert hl_dc.clean_datacenter(
            True, datacenter=self.dc, engine=config.ENGINE,
            format_exp_storage='true'
        )
        assert ll_hosts.add_host(
            name=self.host, address=self.host_ip,
            wait=True, cluster=config.CLUSTER_NAME,
            root_password=config.VDC_ROOT_PASSWORD
        )

    request.addfinalizer(finalizer)
    self.host = config.HOST_FOR_MOUNT
    self.host_ip = config.HOST_FOR_MOUNT_IP
    self.host_executor = rhevm_helpers.get_host_executor(
        ip=self.host_ip, password=config.ROOT_PASSWORD
    )
    self.storage_domains = []
    self.dc = storage_helpers.create_unique_object_name(
        self.__class__.__name__, config.OBJECT_TYPE_DC
    )
    self.cluster = storage_helpers.create_unique_object_name(
        self.__class__.__name__, config.OBJECT_TYPE_CLUSTER
    )
    testflow.step("Create Datacenter for test %s", self.dc)
    assert ll_dc.addDataCenter(
        True, name=self.dc, version=config.COMP_VERSION
    ), "Failed to create Data center '%s'" % self.dc
    assert ll_clusters.addCluster(
        True, name=self.cluster, cpu=config.CPU_NAME, data_center=self.dc,
        version=config.COMP_VERSION
    ), "Failed to create cluster '%s'" % self.cluster
    assert hl_hosts.move_host_to_another_cluster(
        self.host, self.cluster
    ), "Failed to migrate host '%s' into cluster '%s'" % (
        self.host, self.cluster
    )
    executor = rhevm_helpers.get_host_executor(
        ip=config.HOST_FOR_MOUNT_IP, password=config.HOSTS_PW
    )
    storage_helpers.logout_iscsi_sessions(executor)

    self.iscsi_domain = storage_helpers.create_unique_object_name(
        self.__class__.__name__, config.OBJECT_TYPE_SD
    )

    if self.add_iscsi_domain:
        assert hl_sd.add_iscsi_data_domain(
            self.host, self.iscsi_domain, self.dc,
            config.ISCSI_DOMAINS_KWARGS[0]['lun'],
            config.ISCSI_DOMAINS_KWARGS[0]['lun_address'],
            config.ISCSI_DOMAINS_KWARGS[0]['lun_target'],
            override_luns=True, login_all=self.login_all
        ), "Unable to add iscsi domain %s, %s, %s to data center %s" % (
            config.ISCSI_DOMAINS_KWARGS[0]['lun'],
            config.ISCSI_DOMAINS_KWARGS[0]['lun_address'],
            config.ISCSI_DOMAINS_KWARGS[0]['lun_target'], self.dc
        )
        self.storage_domains.append(self.iscsi_domain)
    self.nfs_domain = storage_helpers.create_unique_object_name(
        self.__class__.__name__, config.OBJECT_TYPE_SD
    )
    if self.add_nfs_domain:
        assert hl_sd.addNFSDomain(
            self.host, self.nfs_domain, self.dc,
            config.NFS_DOMAINS_KWARGS[0]['address'],
            config.NFS_DOMAINS_KWARGS[0]['path'],
            format=True, activate=True
        ), "Unable to add nfs domain %s, %s, to data center %s" % (
            config.NFS_DOMAINS_KWARGS[0]['address'],
            config.NFS_DOMAINS_KWARGS[0]['path'], self.dc
        )


@pytest.fixture()
def activate_host(request, storage):
    """
    Activate host
    """
    self = request.node.cls

    def finalizer():
        """
        Activate host
        """
        if ll_hosts.is_host_in_maintenance(True, self.host):
            assert ll_hosts.activate_host(True, self.host)
        assert ll_sd.wait_for_storage_domain_status(
            True, self.dc, self.iscsi_domain, config.SD_ACTIVE
        )
    request.addfinalizer(finalizer)


@pytest.fixture()
def add_additional_iscsi_domain(request, storage):
    """
    Add an additional ISCSI domain
    """
    self = request.node.cls

    self.iscsi_domain2 = storage_helpers.create_unique_object_name(
        self.__class__.__name__, config.OBJECT_TYPE_SD
    )
    assert hl_sd.add_iscsi_data_domain(
        self.host, self.iscsi_domain2, self.dc,
        config.ISCSI_DOMAINS_KWARGS[1]['lun'],
        config.ISCSI_DOMAINS_KWARGS[1]['lun_address'],
        config.ISCSI_DOMAINS_KWARGS[1]['lun_target'],
        override_luns=True, login_all=False,
    ), "Unable to add iscsi domain %s, %s, %s to data center %s" % (
        config.ISCSI_DOMAINS_KWARGS[1]['lun'],
        config.ISCSI_DOMAINS_KWARGS[1]['lun_address'],
        config.ISCSI_DOMAINS_KWARGS[1]['lun_target'], self.dc
    )


@pytest.fixture(scope='module', autouse=True)
def a1_initializer_module_nfs(request):
    """
    Removes one host
    """
    def finalizer_module():
        """
        Add back host to the environment
        """
        assert ll_hosts.add_host(
            name=config.HOST_FOR_MOUNT, cluster=HOST_CLUSTER,
            root_password=config.HOSTS_PW, address=config.HOST_FOR_MOUNT_IP
        ), (
            "Failed to add host %s back to GE environment"
            % config.HOST_FOR_MOUNT
        )
    request.addfinalizer(finalizer_module)
    # Remove the host, this is needed to copy the data between
    # storage domains
    global HOST_CLUSTER
    HOST_CLUSTER = ll_hosts.get_host_cluster(config.HOST_FOR_MOUNT)
    assert ll_hosts.deactivate_host(True, config.HOST_FOR_MOUNT), (
        "Failed to deactivate host %s" % config.HOST_FOR_MOUNT
    )
    assert ll_hosts.remove_host(True, config.HOST_FOR_MOUNT), (
        "Failed to remove host %s" % config.HOST_FOR_MOUNT
    )


@pytest.fixture()
def add_storage_domain(request, storage):
    """
    Add a storage domain for the test
    """

    self = request.node.cls

    def finalizer():
        logger.info("Detaching and deactivating domain")
        test_utils.wait_for_tasks(
            engine=config.ENGINE, datacenter=config.DATA_CENTER_NAME
        )
        assert hl_sd.detach_and_deactivate_domain(
            config.DATA_CENTER_NAME, self.sd_name, config.ENGINE
        )
        logger.info("Removing domain %s", self.sd_name)
        assert ll_sd.removeStorageDomain(
            True, self.sd_name, self.host, 'true'
        )
        rhevm_helpers.cleanup_file_resources([self.storage])

    request.addfinalizer(finalizer)

    self.sd_name = storage_helpers.create_unique_object_name(
        self.__name__, config.OBJECT_TYPE_SD
    )
    self.address = config.UNUSED_RESOURCE[self.storage][0]['address']
    self.path = config.UNUSED_RESOURCE[self.storage][0]['path']
    ll_dc.waitForDataCenterState(config.DATA_CENTER_NAME)
    self.host = ll_hosts.get_spm_host(config.HOSTS_FOR_TEST)
    if not self.storage_type:
        self.storage_type = self.storage
    if 'vfs_type' in self.additional_params:
        self.additional_params['vfs_type'] = self.storage
    assert ll_sd.addStorageDomain(
        True, address=self.address, path=self.path,
        storage_type=self.storage_type, host=self.host,
        type=self.storage_domain_type,
        name=self.sd_name, **self.additional_params
    ), "Failed to add new storage domain %s" % self.sd_name

    assert ll_sd.attachStorageDomain(
        True, config.DATA_CENTER_NAME, self.sd_name
    ), "Failed to attach new storage domain %s to datacenter %s" % (
        self.sd_name, config.DATA_CENTER_NAME
    )

    ll_sd.wait_for_storage_domain_status(
        True, config.DATA_CENTER_NAME, self.sd_name,
        config.SD_ACTIVE
    )

    conns = ll_sd.getConnectionsForStorageDomain(self.sd_name)
    assert len(conns) == 1, (
        "Storage domain %s should have only one storage connection "
        "actual amount of connections: %s" %
        (self.sd_name, len(conns))
    )
    self.conn = conns[0].id
