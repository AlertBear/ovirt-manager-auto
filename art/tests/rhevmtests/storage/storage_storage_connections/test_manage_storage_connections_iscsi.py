import config
import logging
from art.unittest_lib import StorageTest, attr
from concurrent.futures import ThreadPoolExecutor
from art.test_handler.tools import polarion  # pylint: disable=E0611
import art.test_handler.exceptions as errors
from art.rhevm_api.utils import test_utils
import rhevmtests.storage.helpers as storage_helpers
from art.rhevm_api.tests_lib.low_level import storagedomains
from art.rhevm_api.tests_lib.low_level import storageconnections
from art.rhevm_api.tests_lib.low_level import disks
from art.rhevm_api.tests_lib.low_level import hosts
from art.rhevm_api.tests_lib.low_level import vms
from art.rhevm_api.tests_lib.low_level import clusters
from art.rhevm_api.tests_lib.low_level import datacenters as ll_dc
from art.rhevm_api.tests_lib.high_level import storagedomains as hl_sd
from art.rhevm_api.tests_lib.high_level import datastructures
from art.rhevm_api.tests_lib.high_level import hosts as hl_hosts

from art.test_handler.settings import opts

from utilities.machine import Machine
logger = logging.getLogger(__name__)

api = test_utils.get_api('storage_connection', 'storageconnections')
sd_api = test_utils.get_api('storage_domain', 'storagedomains')
dc_api = test_utils.get_api('data_center', 'datacenters')

vmArgs = {
    'vmDescription': 'storage_connections_description',
    'diskInterface': config.VIRTIO,
    'volumeFormat': config.COW_DISK,
    'cluster': config.CLUSTER_ISCSI_CONNECTIONS,
    'installation': True,
    'size': config.VM_DISK_SIZE,
    'nic': config.NIC_NAME[0],
    'useAgent': True,
    'os_type': config.ENUMS['rhel6'],
    'user': config.VM_USER,
    'password': config.VM_PASSWORD,
    'network': config.MGMT_BRIDGE,
    'image': config.COBBLER_PROFILE,
}
ISCSI_SDS = []


def setup_module():
    """
    Remove all the storage domains since we need an empty DC
    """
    global ISCSI_SDS
    # All of the storage connections need to be removed, and the host
    # should be logged out from all targets for these tests. This is due
    # to the fact that when adding a new storage domain or direct lun,
    # ovirt will automatically link the storage  domains with the existing
    # host's logged targets
    logger.info("Removing all iscsi storage domains for test")
    ISCSI_SDS = storagedomains.getStorageDomainNamesForType(
        config.DATA_CENTER_NAME, config.STORAGE_TYPE_ISCSI
    )
    addresses, targets = hl_sd.discover_addresses_and_targets(
        config.HOSTS[0], config.UNUSED_LUN_ADDRESSES[0]
    )
    config.CONNECTIONS[0]['lun_address'] = addresses[0]
    config.CONNECTIONS[0]['lun_target'] = targets[0]
    config.CONNECTIONS[1]['lun_address'] = addresses[1]
    config.CONNECTIONS[1]['lun_target'] = targets[1]

    test_utils.wait_for_tasks(
        config.VDC, config.VDC_PASSWORD, config.DATA_CENTER_NAME
    )
    for sd in ISCSI_SDS:
        hl_sd.detach_and_deactivate_domain(
            config.DATA_CENTER_NAME, sd
        )
        # We want to destroy the domains so we will be able to restore the
        # data on them
        assert storagedomains.removeStorageDomain(
            positive=True, storagedomain=sd, host=config.HOST_FOR_MOUNT,
            format='false'
        )

    assert ll_dc.addDataCenter(
        True, name=config.DATACENTER_ISCSI_CONNECTIONS,
        storage_type=config.STORAGE_TYPE_ISCSI,
        version=config.COMP_VERSION
    )
    assert clusters.addCluster(
        True, name=config.CLUSTER_ISCSI_CONNECTIONS,
        cpu=config.CPU_NAME,
        data_center=config.DATACENTER_ISCSI_CONNECTIONS,
        version=config.COMP_VERSION
    )
    hl_hosts.move_host_to_another_cluster(
        config.HOST_FOR_MOUNT, config.CLUSTER_ISCSI_CONNECTIONS
    )
    _logout_from_all_iscsi_targets()


def teardown_module():
    """
    Remove empty DC
    """
    test_failed = False
    if not hl_hosts.move_host_to_another_cluster(
        config.HOST_FOR_MOUNT, config.CLUSTER_NAME
    ):
        logger.error(
            "Failed to move host %s to cluster %s",
            config.HOST_FOR_MOUNT, config.CLUSTER_NAME
        )
        test_failed = True
    if not ll_dc.removeDataCenter(
        True, config.DATACENTER_ISCSI_CONNECTIONS
    ):
        logger.error(
            "Error removing data center %s",
            config.DATACENTER_ISCSI_CONNECTIONS
        )
        test_failed = True
    if not clusters.removeCluster(True, config.CLUSTER_ISCSI_CONNECTIONS):
        logger.error(
            "Error removing cluster %s", config.CLUSTER_ISCSI_CONNECTIONS
        )
        test_failed = True
    _logout_from_all_iscsi_targets()
    logger.info("Importing iscsi storage domains back")
    # Importing all iscsi domains using the address and target of one of them
    imported = hl_sd.importBlockStorageDomain(
        config.HOST_FOR_MOUNT, config.LUN_ADDRESSES[0],
        config.LUN_TARGETS[0]
    )
    if not imported:
        logger.error("Failed to import iSCSI domains back")
        test_failed = True
    if imported:
        register_failed = False
        for sd in ISCSI_SDS:
            hl_sd.attach_and_activate_domain(config.DATA_CENTER_NAME, sd)
            unregistered_vms = storagedomains.get_unregistered_vms(sd)
            if unregistered_vms:
                for vm in unregistered_vms:
                    if not storagedomains.register_object(
                        vm, cluster=config.CLUSTER_NAME
                    ):
                        logger.error(
                            "Failed to register vm %s from imported domain %s",
                            vm, sd
                        )
                        register_failed = True
        if register_failed:
            raise errors.TearDownException(
                "TearDown failed to register all vms from imported domain"
            )
    if test_failed:
        raise errors.TearDownException("TearDown failed")


def _compare_connections(conn_1, conn_2):
    return conn_1.__dict__ == conn_2.__dict__


def _get_all_storage_connections():
    return api.get(absLink=False)


def _logout_from_all_iscsi_targets():
    """
    Logout from all the targets used in the test
    """
    machine = Machine(
        host=config.HOST_FOR_MOUNT_IP, user=config.HOSTS_USER,
        password=config.HOSTS_PW
    ).util('linux')
    addresses, targets = hl_sd.discover_addresses_and_targets(
        config.HOSTS[0], config.UNUSED_LUN_ADDRESSES[0]
    )
    for address, target in zip(addresses, targets):
        machine.logoutTargets(
            mode='node', targetName=target, portalIp=address
        )


def _filter_storage_connections(connection_list1, connection_list2):
    """
    Return a list of all connection objects from conn_list2 that are not
    in conn_list1
    """
    return_connection = []
    connection_list1_ids = [connection.id for connection in connection_list1]
    for connection in connection_list2:
        if connection.id not in connection_list1_ids:
            return_connection.append(connection)
    return return_connection


def _restore_empty_dc(datacenter=config.DATACENTER_ISCSI_CONNECTIONS):
    found_master, master_sd = storagedomains.findMasterStorageDomain(
        True, datacenter
    )
    if found_master:
        non_master_sds = storagedomains.findNonMasterStorageDomains(
            True, datacenter
        )[1]['nonMasterDomains']
        if non_master_sds:
            for sd in non_master_sds:
                hl_sd.remove_storage_domain(
                    sd, datacenter, config.HOST_FOR_MOUNT, True
                )
        master_sd = master_sd['masterDomain']
        logger.info("Waiting for tasks before deactivating the storage domain")
        test_utils.wait_for_tasks(config.VDC, config.VDC_PASSWORD,
                                  datacenter)
        assert storagedomains.deactivateStorageDomain(
            True, datacenter, master_sd
        )
        dcObj = dc_api.find(datacenter)
        cluster = dc_api.getElemFromLink(
            dcObj, link_name='clusters', attr='cluster',
            get_href=False
        )[0].name
        assert ll_dc.removeDataCenter(True, datacenter)
        assert storagedomains.removeStorageDomain(
            True, master_sd, config.HOST_FOR_MOUNT, 'true'
        )
        assert ll_dc.addDataCenter(
            True, storage_type=config.STORAGE_TYPE_ISCSI,
            name=datacenter, version=config.COMP_VERSION
        )
        assert hosts.deactivateHost(True, config.HOST_FOR_MOUNT)
        assert clusters.connectClusterToDataCenter(
            True, cluster, datacenter
        )
        assert hosts.activateHost(True, config.HOST_FOR_MOUNT)
        assert hosts.waitForHostsStates(True, config.HOST_FOR_MOUNT)


class TestCase(StorageTest):
    storages = set([config.STORAGE_TYPE_ISCSI])
    # TODO: enable cli after http://bugzilla.redhat.com/show_bug.cgi?id=1236718
    # is fixed
    # TODO: enable java after
    # https://projects.engineering.redhat.com/browse/RHEVM-2234 is fixed
    apis = StorageTest.apis - set(['cli', 'java'])

    def get_all_new_connections(self):
        return _filter_storage_connections(
            self.original_conn, _get_all_storage_connections()
        )


@attr(tier=1)
class TestCase5243(TestCase):
    """
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_3_Storage_Manage_Storage_Connections

    **Author**: Katarzyna Jachim
    """
    __test__ = (config.STORAGE_TYPE_ISCSI in opts['storages'])
    polarion_test_case = '5243'
    conn = None
    sd_name = None
    bz = {'1275845': {'engine': None, 'version': ['3.6']}}

    @polarion("RHEVM3-5243")
    def test_adding_storage_connections(self):
        """ test adding a storage connection to a dc without storage domains
            and to a dc with a storage domain
        """
        logger.info(
            "Add a connection to the empty dc %s",
            config.DATACENTER_ISCSI_CONNECTIONS
        )
        conn = dict(config.CONNECTIONS[0]).copy()
        conn['type'] = config.STORAGE_TYPE_ISCSI
        self.conn, success = storageconnections.add_connection(**conn)
        assert success

        storageconnections.remove_storage_connection(self.conn.id)
        self.conn = None
        self.sd_name = 'sd_%s' % self.polarion_test_case
        assert storagedomains.addStorageDomain(
            True, host=config.HOST_FOR_MOUNT, name=self.sd_name,
            type=config.ENUMS['storage_dom_type_data'],
            storage_type=config.STORAGE_TYPE_ISCSI, override_luns=True,
            lun=config.CONNECTIONS[0]['luns'][0], **(config.CONNECTIONS[0])
        )
        old_conns_for_sd = storagedomains.getConnectionsForStorageDomain(
            self.sd_name)
        assert len(old_conns_for_sd) == 1
        old_conn = old_conns_for_sd[0]

        logger.info(
            "Add the same connection to a data center with a storage domain "
            "- should fail"
        )
        self.conn, success = storageconnections.add_connection(**conn)
        assert not success
        conns_for_sd = storagedomains.getConnectionsForStorageDomain(
            self.sd_name)
        assert len(conns_for_sd) == 1
        new_conn = conns_for_sd[0]
        assert _compare_connections(old_conn, new_conn)

    def tearDown(self):
        """
        Remove the storage domain and the storage connection
        """
        if self.sd_name:
            storagedomains.removeStorageDomain(
                True, self.sd_name, config.HOST_FOR_MOUNT, 'true'
            )
        if self.conn:
            storageconnections.remove_storage_connection(self.conn.id)
        _logout_from_all_iscsi_targets()


@attr(tier=2)
class TestCase5247(TestCase):
    """
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_3_Storage_Manage_Storage_Connections

    **Author**: Katarzyna Jachim
    """
    __test__ = (config.STORAGE_TYPE_ISCSI in opts['storages'])
    # Other apis try convert the value type so this cases will not work, only
    # execute on rest
    apis = set(['rest'])
    polarion_test_case = '5247'
    conn = None
    sd_name = None

    def add_connection_without_sth(self, param, value=None):
        conn = dict(config.CONNECTIONS[0]).copy()
        conn['type'] = config.STORAGE_TYPE_ISCSI
        conn[param] = value
        self.conn, success = storageconnections.add_connection(**conn)
        if not success:
            self.conn = None
        assert (not success)

    def add_connection_with_empty_sth(self, param):
        conn = dict(config.CONNECTIONS[0]).copy()
        conn['type'] = config.STORAGE_TYPE_ISCSI
        conn[param] = ''
        self.conn, success = storageconnections.add_connection(**conn)
        if not success:
            self.conn = None
        assert (not success)

    @polarion("RHEVM3-5247")
    def test_adding_storage_connection_without_ip(self):
        """ try to add an iscsi storage connection without LUN address
        """
        self.add_connection_without_sth('lun_address')
        self.add_connection_with_empty_sth('lun_address')

    @polarion("RHEVM3-5247")
    def test_adding_storage_connection_without_port(self):
        """ try to add an iscsi storage connection without LUN port
        """
        self.add_connection_without_sth('lun_port')
        old_conn = storageconnections.StorageConnection
        storageconnections.StorageConnection = datastructures.StorageConnection
        try:
            self.add_connection_with_empty_sth('lun_port')
        finally:
            storageconnections.StorageConnection = old_conn

    @polarion("RHEVM3-5247")
    def test_adding_storage_connection_without_target(self):
        """ try to add an iscsi storage connection without LUN target
        """
        self.add_connection_without_sth('lun_target')
        self.add_connection_with_empty_sth('lun_target')

    @polarion("RHEVM3-5247")
    def test_adding_storage_connection_with_string_as_port(self):
        """ try to add an iscsi storage connection with a string as a port
        """
        old_conn = storageconnections.StorageConnection
        storageconnections.StorageConnection = datastructures.StorageConnection
        try:
            self.add_connection_without_sth('lun_port', 'aaa')
        finally:
            storageconnections.StorageConnection = old_conn

    @polarion("RHEVM3-5247")
    def test_add_the_same_connection_twice(self):
        """ try to add an iscsi storage connection twice
            and add it after it was removed
        """
        conn = dict(config.CONNECTIONS[0]).copy()
        conn['type'] = config.STORAGE_TYPE_ISCSI
        self.conn, success = storageconnections.add_connection(**conn)
        assert success
        _, success = storageconnections.add_connection(**conn)
        assert (not success)
        assert storageconnections.remove_storage_connection(self.conn.id)
        self.conn, success = storageconnections.add_connection(**conn)
        assert success

    def tearDown(self):
        """
        Remove the added storage connection
        """
        if self.conn:
            storageconnections.remove_storage_connection(self.conn.id)


@attr(tier=2)
class TestCase5248(TestCase):
    """
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_3_Storage_Manage_Storage_Connections

    **Author**: Katarzyna Jachim
    """
    __test__ = (config.STORAGE_TYPE_ISCSI in opts['storages'])
    polarion_test_case = '5248'
    conn_1 = None
    conn_2 = None
    sd_name = None

    @classmethod
    def setup_class(cls):
        """
        Add two storage connections
        """
        conn = dict(config.CONNECTIONS[0]).copy()
        conn['type'] = config.STORAGE_TYPE_ISCSI
        cls.conn_1, success = storageconnections.add_connection(**conn)
        assert success

        conn = dict(config.CONNECTIONS[1]).copy()
        conn['type'] = config.STORAGE_TYPE_ISCSI
        cls.conn_2_params = conn
        cls.conn_2, success = storageconnections.add_connection(**conn)
        assert success

    def change_connection_without_sth(self, conn, param):
        conn_params = {}
        conn_params[param] = ''
        conn_params['type'] = config.STORAGE_TYPE_ISCSI
        _, success = storageconnections.update_connection(
            conn.id, **conn_params)
        assert (not success)

    @polarion("RHEVM3-5248")
    def test_changing_storage_connection_without_ip(self):
        """ try to change an iscsi connection and set LUN address to nothing
        """
        self.change_connection_without_sth(self.conn_1, 'lun_address')

    @polarion("RHEVM3-5248")
    def test_changing_storage_connection_without_port(self):
        """ try to change an iscsi connection and set LUN port to nothing
        """
        old_conn = storageconnections.StorageConnection
        storageconnections.StorageConnection = datastructures.StorageConnection
        try:
            self.change_connection_without_sth(self.conn_1, 'lun_port')
        finally:
            storageconnections.StorageConnection = old_conn

    @polarion("RHEVM3-5248")
    def test_changing_storage_connection_without_target(self):
        """ try to change an iscsi connection and set LUN target to nothing
        """
        self.change_connection_without_sth(self.conn_1, 'lun_target')

    @polarion("RHEVM3-5248")
    def test_changing_storage_connection_to_existing_one(self):
        """ try to change an iscsi connection and set all values as in another
        """
        _, success = storageconnections.update_connection(
            self.conn_1.id, **self.conn_2_params)
        assert not success

    @classmethod
    def teardown_class(cls):
        """
        Remove the storage connections
        """
        storageconnections.remove_storage_connection(cls.conn_1.id)
        storageconnections.remove_storage_connection(cls.conn_2.id)


@attr(tier=2)
class TestCase5246(TestCase):
    """
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_3_Storage_Manage_Storage_Connections

    **Author**: Katarzyna Jachim
    """
    __test__ = (config.STORAGE_TYPE_ISCSI in opts['storages'])
    polarion_test_case = '5246'
    sd_name_1 = "sd_%s_1" % polarion_test_case
    sd_name_2 = "sd_%s_2" % polarion_test_case
    master_sd = "master_%s" % polarion_test_case
    bz = {'1272110': {'engine': None, 'version': ["3.6"]}}

    def setUp(self):
        """
        Add one storage domain and then another 2 storage domains that all
        use the same storage connection
        """
        assert storagedomains.addStorageDomain(
            True, host=config.HOST_FOR_MOUNT, name=self.master_sd,
            type=config.ENUMS['storage_dom_type_data'],
            storage_type=config.STORAGE_TYPE_NFS,
            address=config.EXTRA_DOMAIN_ADDRESSES[0],
            path=config.EXTRA_DOMAIN_PATHS[0]
        )

        assert storagedomains.attachStorageDomain(
            True, config.DATACENTER_ISCSI_CONNECTIONS, self.master_sd
        )

        assert storagedomains.addStorageDomain(
            True, host=config.HOST_FOR_MOUNT, name=self.sd_name_1,
            type=config.ENUMS['storage_dom_type_data'],
            storage_type=config.STORAGE_TYPE_ISCSI, override_luns=True,
            lun=config.CONNECTIONS[0]['luns'][1], **(config.CONNECTIONS[0])
        )

        assert storagedomains.attachStorageDomain(
            True, config.DATACENTER_ISCSI_CONNECTIONS, self.sd_name_1
        )

        assert storagedomains.addStorageDomain(
            True, host=config.HOST_FOR_MOUNT, name=self.sd_name_2,
            type=config.ENUMS['storage_dom_type_data'],
            storage_type=config.STORAGE_TYPE_ISCSI, override_luns=True,
            lun=config.CONNECTIONS[0]['luns'][2], **(config.CONNECTIONS[0])
        )

        assert storagedomains.attachStorageDomain(
            True, config.DATACENTER_ISCSI_CONNECTIONS, self.sd_name_2
        )

    @polarion("RHEVM3-5246")
    def test_removing_storage_connection(self):
        """ Test scenario:
            * try to delete the connection
            * put one of the storage domain into maintenance
            * try to delete the connection
            * detach the storage connection from the inactive storage domain
            * try to delete the connection
            * put the other storage domain into maintenance
            * try to delete the connection
            * detach the storage connection from the storage domain
            * try to delete the storage connection
        """
        logger.info("Try to remove the storage connection - should fail")
        conns = storagedomains.getConnectionsForStorageDomain(self.sd_name_1)
        conn_id = conns[0].id
        assert not storageconnections.remove_storage_connection(conn_id)

        test_utils.wait_for_tasks(config.VDC, config.VDC_PASSWORD,
                                  config.DATACENTER_ISCSI_CONNECTIONS)
        logger.info("Put the first domain into maintenance")
        assert storagedomains.deactivateStorageDomain(
            True, config.DATACENTER_ISCSI_CONNECTIONS, self.sd_name_1)
        logger.info("Try to remove the storage connection - should fail")
        assert not storageconnections.remove_storage_connection(conn_id)

        logger.info("Deatch the storage connection from the first domain")
        assert storagedomains.detachConnectionFromStorageDomain(
            self.sd_name_1, conn_id)
        logger.info("Try to remove the storage connection - should fail")
        assert not storageconnections.remove_storage_connection(conn_id)

        logger.info("Put the second sorage domain into maintenance")
        test_utils.wait_for_tasks(config.VDC, config.VDC_PASSWORD,
                                  config.DATACENTER_ISCSI_CONNECTIONS)
        assert storagedomains.deactivateStorageDomain(
            True, config.DATACENTER_ISCSI_CONNECTIONS, self.sd_name_2)
        logger.info("Try to remove the storage connection - should fail")
        assert not storageconnections.remove_storage_connection(conn_id)

        logger.info("Deatch the storage connection from the second domain")
        assert storagedomains.detachConnectionFromStorageDomain(
            self.sd_name_2, conn_id)
        logger.info("Try to remove the storage connection - should succeed")
        assert storageconnections.remove_storage_connection(conn_id)

    def tearDown(self):
        test_utils.wait_for_tasks(config.VDC, config.VDC_PASSWORD,
                                  config.DATACENTER_ISCSI_CONNECTIONS)
        if self.sd_name_1 is not None and self.sd_name_2 is not None:
            conn = dict(config.CONNECTIONS[0]).copy()
            conn['type'] = config.STORAGE_TYPE_ISCSI
            conn_1, success = storageconnections.add_connection(**conn)
            if success:
                storagedomains.addConnectionToStorageDomain(
                    self.sd_name_1, conn_1.id)
                storagedomains.addConnectionToStorageDomain(
                    self.sd_name_2, conn_1.id)
        _restore_empty_dc()
        _logout_from_all_iscsi_targets()


@attr(tier=2)
class TestCase5240(TestCase):
    """
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_3_Storage_Manage_Storage_Connections

    **Author**: Katarzyna Jachim
    """
    __test__ = (config.STORAGE_TYPE_ISCSI in opts['storages'])
    polarion_test_case = '5240'
    conns = []
    no_of_conn = 10
    con_params = []

    @classmethod
    def setup_class(cls):
        # put sth random to iqn, we are not going to use the connection anyhow
        for i in range(cls.no_of_conn):
            conn = dict(config.CONNECTIONS[0]).copy()
            conn['lun_target'] = 'sth%d.%s' % (i, conn['lun_target'])
            conn['type'] = config.STORAGE_TYPE_ISCSI
            cls.con_params.append(conn)
            conn, success = storageconnections.add_connection(**conn)
            assert success
            cls.conns.append(conn)

    @polarion("RHEVM3-5240")
    def test_change_multiple_connections(self):
        """
            Test steps:
            * try to switch 2 connections
            * try to change 10 connections at once
        """
        logger.info("Trying to switch 2 connections")
        with ThreadPoolExecutor(max_workers=config.MAX_WORKERS) as executor:
            result_1 = executor.submit(
                storageconnections.update_connection,
                self.conns[0].id, ** self.con_params[1]
            )
            result_2 = executor.submit(
                storageconnections.update_connection,
                self.conns[1].id, ** self.con_params[0]
            )
        assert result_1.result()[1] == result_2.result()[1]

        conn_1 = api.find(self.conns[0].id, 'id')
        conn_2 = api.find(self.conns[1].id, 'id')

        assert not _compare_connections(conn_1, conn_2)

        logger.info("Trying to change 10 connections at once")
        results = []
        with ThreadPoolExecutor(max_workers=config.MAX_WORKERS) as executor:
            for conn in self.conns:
                results.append(
                    executor.submit(
                        storageconnections.update_connection,
                        conn.id,
                        lun_target="aaa" + conn.target,
                        type=config.STORAGE_TYPE_ISCSI
                    )
                )
        for result in results:
            assert result.result()

    @classmethod
    def teardown_class(cls):
        for conn in cls.conns:
            storageconnections.remove_storage_connection(conn.id)


@attr(tier=2)
class TestCase5242(TestCase):
    """
    Verify the GET call works for various storage connection/storage domains
    combinations
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_3_Storage_Manage_Storage_Connections

    **Author**: Katarzyna Jachim
    """
    __test__ = (config.STORAGE_TYPE_ISCSI in opts['storages'])
    polarion_test_case = '5242'
    bz = {'1272110': {'engine': None, 'version': ["3.6"]}}

    def setUp(self):
        self.disks = []
        self.storage_domains = []
        self.storage_connections = []
        self.original_conn = _get_all_storage_connections()

    @polarion("RHEVM3-5242")
    def test_verify_one_orphaned_connection(self):
        """
        Verifying GET for one orphaned connection
        """
        logger.info("Verifying get for one orphaned connection")
        conn_1 = dict(config.CONNECTIONS[0]).copy()
        conn_1['type'] = config.STORAGE_TYPE_ISCSI
        self.conn, success = storageconnections.add_connection(**conn_1)
        self.assertTrue(success, "Error adding storage connection %s" % conn_1)
        self.storage_connections.append(self.conn.id)
        new_conn = self.get_all_new_connections()
        assert len(new_conn) == 1
        storageconnections.remove_storage_connection(self.conn.id)
        self.storage_connections.remove(self.conn.id)

    @polarion("RHEVM3-5242")
    def test_verify_one_storage_domain(self):
        """
        Verifying GET for one storage domain
        """
        logger.info("Verifying get for one orphaned connection")
        sd_name = "sd_1_%s" % self.polarion_test_case
        assert storagedomains.addStorageDomain(
            True, host=config.HOST_FOR_MOUNT, name=sd_name,
            type=config.ENUMS['storage_dom_type_data'],
            storage_type=config.STORAGE_TYPE_ISCSI, override_luns=True,
            lun=config.CONNECTIONS[0]['luns'][0], **(config.CONNECTIONS[0]))
        self.storage_domains.append(sd_name)
        new_conn = self.get_all_new_connections()
        conn_for_sd = storagedomains.getConnectionsForStorageDomain(sd_name)
        assert len(new_conn) == 1
        assert len(conn_for_sd) == 1
        assert _compare_connections(new_conn[0], conn_for_sd[0])
        assert storagedomains.removeStorageDomain(
            True, sd_name, config.HOST_FOR_MOUNT, 'true',
        )
        self.storage_domains.remove(sd_name)
        new_conn = self.get_all_new_connections()
        assert len(new_conn) == 0

    @polarion("RHEVM3-5242")
    def test_verify_storage_domain_with_two_connections(self):
        """
        Verifying GET for one storage domain using multiple
        storage connections
        """
        logger.info("Verifying get for one storage domain")
        sd_name = "sd_2_%s" % self.polarion_test_case
        assert storagedomains.addStorageDomain(
            True, host=config.HOST_FOR_MOUNT, name=sd_name,
            type=config.ENUMS['storage_dom_type_data'],
            storage_type=config.STORAGE_TYPE_ISCSI, override_luns=True,
            lun=config.CONNECTIONS[0]['luns'][0], **(config.CONNECTIONS[0])
        )
        self.storage_domains.append(sd_name)
        assert storagedomains.attachStorageDomain(
            True, config.DATACENTER_ISCSI_CONNECTIONS, sd_name)
        self.storage_domains.remove(sd_name)
        assert storagedomains.waitForStorageDomainStatus(
            True, config.DATACENTER_ISCSI_CONNECTIONS, sd_name,
            config.ENUMS['storage_domain_state_active'])
        assert storagedomains.extendStorageDomain(
            True, sd_name, storage_type=config.STORAGE_TYPE_ISCSI,
            host=config.HOST_FOR_MOUNT, override_luns=True,
            lun=config.CONNECTIONS[1]['luns'][1], **(config.CONNECTIONS[1])
        )

        new_conn = self.get_all_new_connections()
        conn_for_sd = storagedomains.getConnectionsForStorageDomain(sd_name)
        assert len(new_conn) == 2
        assert len(conn_for_sd) == 2

    @polarion("RHEVM3-5242")
    def test_verify_two_storage_domains_with_the_same_connection(self):
        """
        Verifying get for a storage domain with 2 connections
        """
        logger.info("Verifying get for a storage domain with 2 connections")
        sd_name_1 = "sd_3_%s" % self.polarion_test_case
        storagedomains.addStorageDomain(
            True, host=config.HOST_FOR_MOUNT, name=sd_name_1,
            type=config.ENUMS['storage_dom_type_data'],
            storage_type=config.STORAGE_TYPE_ISCSI, override_luns=True,
            lun=config.CONNECTIONS[0]['luns'][0], **(config.CONNECTIONS[0])
        )
        self.storage_domains.append(sd_name_1)
        sd_name_2 = "sd_4_%s" % self.polarion_test_case
        storagedomains.addStorageDomain(
            True, host=config.HOST_FOR_MOUNT, name=sd_name_2,
            type=config.ENUMS['storage_dom_type_data'],
            storage_type=config.STORAGE_TYPE_ISCSI, override_luns=True,
            lun=config.CONNECTIONS[0]['luns'][1], **(config.CONNECTIONS[0])
        )
        self.storage_domains.append(sd_name_2)

        conn_sd_1 = storagedomains.getConnectionsForStorageDomain(sd_name_1)
        conn_sd_2 = storagedomains.getConnectionsForStorageDomain(sd_name_2)
        assert len(conn_sd_1) == len(conn_sd_2)
        assert _compare_connections(conn_sd_1[0], conn_sd_2[0])
        storagedomains.removeStorageDomain(
            True, sd_name_1, config.HOST_FOR_MOUNT, 'true',
        )
        self.storage_domains.remove(sd_name_1)
        storagedomains.removeStorageDomain(
            True, sd_name_2, config.HOST_FOR_MOUNT, 'true',
        )
        self.storage_domains.remove(sd_name_2)
        new_conn = self.get_all_new_connections()
        assert not new_conn

    @polarion("RHEVM3-5242")
    def test_verify_one_direct_lun(self):
        """
        Verifying get for direct LUN
        """
        logger.info("Verifying get for direct LUN")
        alias = "disk_1_%s" % self.polarion_test_case
        disks.addDisk(
            True, alias=alias, interface=config.DISK_INTERFACE_VIRTIO,
            format=config.DISK_FORMAT_COW, type_=config.STORAGE_TYPE_ISCSI,
            lun_id=config.CONNECTIONS[0]['luns'][0],
            lun_address=config.CONNECTIONS[0]['lun_address'],
            lun_target=config.CONNECTIONS[0]['lun_target']
        )

        self.disks.append(alias)
        new_conn = self.get_all_new_connections()
        assert len(new_conn) == 1
        # TODO: When the API allows it, check the storage connection of
        # a direct lun, something like:
        # conn_disk = disks.getConnectionsForDisk(alias)
        # assert _compare_connections(all_conn, conn_disk)
        # https://bugzilla.redhat.com/show_bug.cgi?id=1227322
        assert disks.deleteDisk(True, alias)
        self.disks.remove(alias)

    def tearDown(self):
        """
        Remove leftover disks, storage domains and storage connections
        """
        for alias in self.disks:
            disks.deleteDisk(True, alias)
        for storage_domain in self.storage_domains:
            storagedomains.removeStorageDomain(
                True, storage_domain, config.HOST_FOR_MOUNT, 'true'
            )
        for storage_connection in self.storage_connections:
            storageconnections.remove_storage_connection(storage_connection)
        _restore_empty_dc()
        _logout_from_all_iscsi_targets()


@attr(tier=2)
class TestCase5245(TestCase):
    """
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_3_Storage_Manage_Storage_Connections

    **Author**: Katarzyna Jachim
    """
    __test__ = (config.STORAGE_TYPE_ISCSI in opts['storages'])
    polarion_test_case = '5245'
    conn = None
    sd_name_1 = "sd_%s_1" % polarion_test_case
    sd_name_2 = "sd_%s_2" % polarion_test_case
    bz = {'1272110': {'engine': None, 'version': ["3.6"]}}

    def setUp(self):
        """
        Add and attach two storage domains
        """
        assert storagedomains.addStorageDomain(
            True, host=config.HOST_FOR_MOUNT, name=self.sd_name_1,
            type=config.ENUMS['storage_dom_type_data'],
            storage_type=config.STORAGE_TYPE_ISCSI, override_luns=True,
            lun=config.CONNECTIONS[0]['luns'][0], **(config.CONNECTIONS[0])
        )

        assert storagedomains.addStorageDomain(
            True, host=config.HOST_FOR_MOUNT, name=self.sd_name_2,
            type=config.ENUMS['storage_dom_type_data'],
            storage_type=config.STORAGE_TYPE_ISCSI, override_luns=True,
            lun=config.CONNECTIONS[0]['luns'][1], **(config.CONNECTIONS[0])
        )

        assert storagedomains.attachStorageDomain(
            True, config.DATACENTER_ISCSI_CONNECTIONS, self.sd_name_1)
        assert storagedomains.attachStorageDomain(
            True, config.DATACENTER_ISCSI_CONNECTIONS, self.sd_name_2)
        storagedomains.waitForStorageDomainStatus(
            True, config.DATACENTER_ISCSI_CONNECTIONS, self.sd_name_1,
            config.ENUMS['storage_domain_state_active'])
        storagedomains.waitForStorageDomainStatus(
            True, config.DATACENTER_ISCSI_CONNECTIONS, self.sd_name_2,
            config.ENUMS['storage_domain_state_active'])

    def _try_to_change_connection(self, conn_id, should_pass):
        """
        Try to update connection conn_id, should succeed if should_pass is True
        """
        for parameter in ['lun_address', 'lun_target', 'lun_port']:
            fail_action = 'Unable' if should_pass else 'Able'
            self.assertTrue(
                should_pass == storageconnections.update_connection(
                    conn_id, type=config.STORAGE_TYPE_ISCSI,
                    **{parameter: config.CONNECTIONS[1][parameter]}
                )[1],
                "{0} to update the storage connection {1}".format(
                    fail_action, conn_id
                )
            )

    @polarion("RHEVM3-5245")
    def test_change_connection_in_sd(self):
        """ test steps:
            * try to change the connection (IP address, port, target, user,
                password)
            * put one of the storage domains into maintenance
            * try to change the connection
            * put the other storage domain into maintenance
            * try to change the storage connection:
                * IP address
                * port
                * target
                * ID
            * activate the storage domains
            * try to change parameters of non existent storage domain
        """
        conn = storagedomains.getConnectionsForStorageDomain(self.sd_name_1)[0]
        logger.info("Trying to change the connection - should fail")
        self._try_to_change_connection(conn.id, False)
        logger.info("Waiting for tasks before deactivating the storage domain")
        test_utils.wait_for_tasks(config.VDC, config.VDC_PASSWORD,
                                  config.DATACENTER_ISCSI_CONNECTIONS)

        logger.info("Deactivating one of the storage domains")
        assert storagedomains.deactivateStorageDomain(
            True, config.DATACENTER_ISCSI_CONNECTIONS, self.sd_name_2)
        logger.info("Trying to change the connection - should fail")
        self._try_to_change_connection(conn.id, False)
        logger.info("Waiting for tasks before deactivating the storage domain")
        test_utils.wait_for_tasks(config.VDC, config.VDC_PASSWORD,
                                  config.DATACENTER_ISCSI_CONNECTIONS)

        logger.info("Deactivating both storage domains")
        assert storagedomains.deactivateStorageDomain(
            True, config.DATACENTER_ISCSI_CONNECTIONS, self.sd_name_1)
        logger.info("Trying to change the connection - should succeed")
        self._try_to_change_connection(conn.id, True)
        assert storagedomains.activateStorageDomain(
            True, config.DATACENTER_ISCSI_CONNECTIONS, self.sd_name_1)
        assert storagedomains.activateStorageDomain(
            True, config.DATACENTER_ISCSI_CONNECTIONS, self.sd_name_2)

    def tearDown(self):
        """
        Remove added storage domains
        """
        _restore_empty_dc()
        _logout_from_all_iscsi_targets()


@attr(tier=2)
class TestCase5244(TestCase):
    """
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_3_Storage_Manage_Storage_Connections

    **Author**: Katarzyna Jachim
    """
    __test__ = (config.STORAGE_TYPE_ISCSI in opts['storages'])
    polarion_test_case = '5244'
    conn = None
    sd_name_1 = "sd_%s_1" % polarion_test_case
    sd_name_2 = "sd_%s_2" % polarion_test_case
    bz = {'1272110': {'engine': None, 'version': ["3.6"]}}

    def setUp(self):
        """
        Add two storage domains sharing the same storage connection
        Add a new storage connection
        """
        assert storagedomains.addStorageDomain(
            True, host=config.HOST_FOR_MOUNT, name=self.sd_name_1,
            type=config.ENUMS['storage_dom_type_data'],
            storage_type=config.STORAGE_TYPE_ISCSI, override_luns=True,
            lun=config.CONNECTIONS[0]['luns'][0], **(config.CONNECTIONS[0])
        )

        assert storagedomains.addStorageDomain(
            True, host=config.HOST_FOR_MOUNT, name=self.sd_name_2,
            type=config.ENUMS['storage_dom_type_data'],
            storage_type=config.STORAGE_TYPE_ISCSI, override_luns=True,
            lun=config.CONNECTIONS[0]['luns'][1], **(config.CONNECTIONS[0])
        )

        assert storagedomains.attachStorageDomain(
            True, config.DATACENTER_ISCSI_CONNECTIONS, self.sd_name_1)
        assert storagedomains.attachStorageDomain(
            True, config.DATACENTER_ISCSI_CONNECTIONS, self.sd_name_2)

        conn = dict(config.CONNECTIONS[1]).copy()
        conn['type'] = config.STORAGE_TYPE_ISCSI
        self.conn, success = storageconnections.add_connection(**conn)
        assert success

    @polarion("RHEVM3-5244")
    def test_add_connection_to_sd(self):
        """ test steps:
                * try to add the connection to one of the storage domains
                * put one of the storages domain into maintenance
                * add the iSCSI connection to the storage domain
                * activate the storage domain
                * put the other storage domain into maintenance
                * add the iSCSI connection to the inactive storage domain
                * try to add the same connection again
                * activate the storage domain
        """
        assert not storagedomains.addConnectionToStorageDomain(
            self.sd_name_1, self.conn.id)
        logger.info("Waiting for tasks before deactivating the storage domain")
        test_utils.wait_for_tasks(config.VDC, config.VDC_PASSWORD,
                                  config.DATACENTER_ISCSI_CONNECTIONS)
        assert storagedomains.deactivateStorageDomain(
            True, config.DATACENTER_ISCSI_CONNECTIONS, self.sd_name_1)
        assert storagedomains.addConnectionToStorageDomain(
            self.sd_name_1, self.conn.id)
        assert storagedomains.activateStorageDomain(
            True, config.DATACENTER_ISCSI_CONNECTIONS, self.sd_name_1)

        logger.info("Waiting for tasks before deactivating the storage domain")
        test_utils.wait_for_tasks(config.VDC, config.VDC_PASSWORD,
                                  config.DATACENTER_ISCSI_CONNECTIONS)
        assert storagedomains.deactivateStorageDomain(
            True, config.DATACENTER_ISCSI_CONNECTIONS, self.sd_name_2)
        assert storagedomains.addConnectionToStorageDomain(
            self.sd_name_2, self.conn.id)
        assert not storagedomains.addConnectionToStorageDomain(
            self.sd_name_2, self.conn.id)
        assert storagedomains.activateStorageDomain(
            True, config.DATACENTER_ISCSI_CONNECTIONS, self.sd_name_2)

    def tearDown(self):
        _restore_empty_dc()
        _logout_from_all_iscsi_targets()


@attr(tier=2)
class TestCase5241(TestCase):
    """
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_3_Storage_Manage_Storage_Connections

    **Author**: Katarzyna Jachim
    """
    __test__ = (config.STORAGE_TYPE_ISCSI in opts['storages'])
    polarion_test_case = '5241'
    conn = None
    vm_name_1 = "vm_%s_1" % polarion_test_case
    vm_name_2 = "vm_%s_2" % polarion_test_case
    disk_1 = "disk_%s_1" % polarion_test_case
    sd_name = "sd_%s" % polarion_test_case
    disk_2 = "disk_%s_2" % polarion_test_case
    bz = {'1272110': {'engine': None, 'version': ["3.6"]}}

    def setUp(self):
        assert storagedomains.addStorageDomain(
            True, host=config.HOST_FOR_MOUNT, name=self.sd_name,
            type=config.ENUMS['storage_dom_type_data'],
            storage_type=config.STORAGE_TYPE_NFS,
            address=config.EXTRA_DOMAIN_ADDRESSES[0],
            path=config.EXTRA_DOMAIN_PATHS[0],
        )

        assert storagedomains.attachStorageDomain(
            True, config.DATACENTER_ISCSI_CONNECTIONS, self.sd_name)

        assert storagedomains.waitForStorageDomainStatus(
            True, config.DATACENTER_ISCSI_CONNECTIONS, self.sd_name,
            config.ENUMS['storage_domain_state_active'])

        for vm_name in (self.vm_name_1, self.vm_name_2):
            vm_args_copy = vmArgs.copy()
            vm_args_copy['storageDomainName'] = self.sd_name
            vm_args_copy['vmName'] = vm_name
            vm_args_copy['vmDescription'] = vm_name

            if not storage_helpers.create_vm_or_clone(**vm_args_copy):
                raise errors.VMException(
                    'Unable to create vm %s for test' % vm_name
                )
            logger.info('Shutting down VM %s', vm_name)
            vms.stop_vms_safely([vm_name])

        assert disks.addDisk(
            True, alias=self.disk_1,
            interface=config.VIRTIO,
            format=config.DISK_FORMAT_COW,
            lun_id=config.CONNECTIONS[0]['luns'][1],
            lun_address=config.CONNECTIONS[0]['lun_address'],
            lun_target=config.CONNECTIONS[0]['lun_target'],
            type_=config.STORAGE_TYPE_ISCSI
        )

        assert disks.addDisk(
            True, alias=self.disk_2,
            interface=config.VIRTIO,
            format=config.DISK_FORMAT_COW,
            lun_id=config.CONNECTIONS[0]['luns'][2],
            lun_address=config.CONNECTIONS[0]['lun_address'],
            lun_target=config.CONNECTIONS[0]['lun_target'],
            type_=config.STORAGE_TYPE_ISCSI
        )

        assert disks.attachDisk(True, self.disk_1, self.vm_name_1)
        assert disks.attachDisk(True, self.disk_2, self.vm_name_2)

        assert vms.startVm(True, self.vm_name_1)
        assert vms.startVm(True, self.vm_name_2)

    @polarion("RHEVM3-5241")
    def test_change_connection_in_lun(self):
        """ test steps:
            * try to change the connection (IP address, port, target)
            * stop one of the vms
            * try to change the connection
            * stop the other vm
            * try to change the connection (IP address, port, target)
            * run both vms again
        """
        assert vms.waitForVMState(self.vm_name_1)
        assert vms.waitForVMState(self.vm_name_2)

        # TODO: When the API allows it, get the storage connection of
        # a direct lun, instead of looping through all of them
        # https://bugzilla.redhat.com/show_bug.cgi?id=1227322
        connections = api.get(absLink=False)
        lun_conn = None
        for conn in connections:
            if conn.target == config.CONNECTIONS[0]['lun_target']:
                lun_conn = conn
                break

        assert lun_conn

        assert not storageconnections.update_connection(
            lun_conn.id, lun_address=config.CONNECTIONS[1]['lun_address'],
            type=config.STORAGE_TYPE_ISCSI
        )[1]

        assert vms.stopVm(True, self.vm_name_1)
        assert vms.waitForVMState(
            self.vm_name_1, config.ENUMS['vm_state_down'])

        assert not storageconnections.update_connection(
            lun_conn.id, lun_address=config.CONNECTIONS[1]['lun_address'],
            type=config.STORAGE_TYPE_ISCSI
        )[1]

        assert vms.stopVm(True, self.vm_name_2)
        assert vms.waitForVMState(
            self.vm_name_2, config.ENUMS['vm_state_down'])

        assert storageconnections.update_connection(
            lun_conn.id, type=config.STORAGE_TYPE_ISCSI,
            **(config.CONNECTIONS[1])
        )[1]

        assert vms.startVm(True, self.vm_name_1)
        assert vms.startVm(True, self.vm_name_2)

    def tearDown(self):
        """
        Remove vms and added storage domains
        """
        vms.safely_remove_vms([self.vm_name_1, self.vm_name_2])
        _restore_empty_dc()
        _logout_from_all_iscsi_targets()


@attr(tier=1)
class TestCase5249(TestCase):
    """
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_3_Storage_Manage_Storage_Connections

    **Author**: Katarzyna Jachim
    """
    __test__ = (config.STORAGE_TYPE_ISCSI in opts['storages'])
    polarion_test_case = '5249'
    conn = None

    def setUp(self):
        self.storage_domains = []
        conn = dict(config.CONNECTIONS[0]).copy()
        conn['type'] = config.STORAGE_TYPE_ISCSI
        self.conn, success = storageconnections.add_connection(**conn)
        assert success
        self.original_conn = _get_all_storage_connections()

    @polarion("RHEVM3-5249")
    def test_adding_storage_domains(self):
        """ Adds:
            * a storage domain using a new connection (old flow)
            * a storage domain with all params specified (old flow), but
              the connection params are the same of an existing connection
            In the last case, new connection should not be added.
        """
        logger.info("Adding a new storage domain with a new connection")
        sd_name_2 = "sd_%s_2" % self.polarion_test_case

        assert storagedomains.addStorageDomain(
            True, name=sd_name_2, host=config.HOST_FOR_MOUNT,
            type=config.ENUMS['storage_dom_type_data'],
            storage_type=config.STORAGE_TYPE_ISCSI, override_luns=True,
            lun=config.CONNECTIONS[1]['luns'][0], **(config.CONNECTIONS[1])
        )
        self.storage_domains.append(sd_name_2)

        sd_name_2_conn = storagedomains.getConnectionsForStorageDomain(
            sd_name_2
        )
        logger.info(
            "Connection of storage domain %s is: %s",
            sd_name_2, sd_name_2_conn[0].id
        )
        assert len(sd_name_2_conn) == 1
        assert storagedomains.removeStorageDomain(
            True, sd_name_2, config.HOST_FOR_MOUNT, 'true'
        )
        self.storage_domains.remove(sd_name_2)

        logger.info(
            "Adding a new domain specifying the parameters but using the "
            "existing connection"
        )
        sd_name_3 = "sd_%s_3" % self.polarion_test_case
        assert storagedomains.addStorageDomain(
            True, name=sd_name_3, host=config.HOST_FOR_MOUNT,
            type=config.ENUMS['storage_dom_type_data'],
            storage_type=config.STORAGE_TYPE_ISCSI, override_luns=True,
            lun=config.CONNECTIONS[0]['luns'][1],
            **(config.CONNECTIONS[0])
        )
        sd_name_3_conn = storagedomains.getConnectionsForStorageDomain(
            sd_name_3
        )
        logger.info(
            "Connection of storage domain %s is: %s",
            sd_name_3, sd_name_3_conn[0].id
        )
        self.storage_domains.append(sd_name_3)

    def tearDown(self):
        """
        Remove added storage domains
        """
        for storage_domain in self.storage_domains:
            storagedomains.removeStorageDomain(
                True, storage_domain, config.HOST_FOR_MOUNT, 'true'
            )
        if self.conn.id in [
            connection.id for connection in _get_all_storage_connections()
        ]:
            storageconnections.remove_storage_connection(self.conn.id)
        _logout_from_all_iscsi_targets()
