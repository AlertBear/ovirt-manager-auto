import logging
import config
import pytest
from concurrent.futures import ThreadPoolExecutor
from art.unittest_lib import testflow
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
    storageconnections as ll_storageconnections,
    storagedomains as ll_sd,
    vms as ll_vms,
)
from art.test_handler.settings import ART_CONFIG
from art.test_handler.tools import bz, polarion
from art.test_handler import exceptions
from art.unittest_lib import (
    tier3,
    StorageTest,
)
from art.rhevm_api.utils import test_utils

from fixtures import (
    logout_all_iscsi_targets, remove_storage_domains,
    remove_storage_connections, add_storage_connections,
    add_storage_domain_and_connections, generate_random_storage_connections,
    initialize_variables_remove_leftover_domains, empty_dc,
    add_two_storage_domains, add_new_storage_connection,
    add_nfs_domain_generate_vms,
)

# load the initializer for the module
from fixtures import a0_initialize_variables_clean_storages  # noqa
from rhevmtests.storage.fixtures import deactivate_and_detach_export_domain  # noqa

from rhevmtests.storage.fixtures import remove_vms
import rhevmtests.storage.helpers as storage_helpers

from unittest2 import SkipTest

logger = logging.getLogger(__name__)


@pytest.fixture(scope='module', autouse=True)
def a1_add_new_datacenter(request):
    """
    Create a new environment for tests
    """
    def finalizer():
        """
        Remove empty DC
        """
        testflow.teardown(
            "Removing Datacenter %s", config.DATACENTER_ISCSI_CONNECTIONS
        )
        assert hl_dc.clean_datacenter(
            True, datacenter=config.DATACENTER_ISCSI_CONNECTIONS,
            format_exp_storage=True
        )
        assert ll_hosts.add_host(
            config.HOST_FOR_MOUNT, address=config.HOST_FOR_MOUNT_IP,
            wait=True, cluster=config.CLUSTER_NAME,
            root_password=config.VDC_ROOT_PASSWORD
        )
    request.addfinalizer(finalizer)

    if config.PPC_ARCH:
        # TODO: Enable for PPC when the targets are configured for the
        # environment and properly tested
        raise SkipTest("Additional iscsi targets not configured")
    addresses, targets = hl_sd.discover_addresses_and_targets(
        config.HOSTS[0], config.ISCSI_DOMAINS_KWARGS[0]['lun_address']
    )
    config.CONNECTIONS[0]['lun_address'] = addresses[0]
    logger.info("1st storage connection address to use is: %s", addresses[0])
    config.CONNECTIONS[0]['lun_target'] = targets[0]
    config.CONNECTIONS[1]['lun_address'] = addresses[1]
    logger.info("2nd storage connection address to use is: %s", addresses[1])
    config.CONNECTIONS[1]['lun_target'] = targets[1]

    testflow.setup("Adding Datacenter %s", config.DATACENTER_ISCSI_CONNECTIONS)
    if not ll_dc.addDataCenter(
        True, name=config.DATACENTER_ISCSI_CONNECTIONS,
        version=config.COMP_VERSION
    ):
        raise exceptions.DataCenterException(
            "Failed to create Data center '%s'" %
            config.DATACENTER_ISCSI_CONNECTIONS
        )
    if not ll_clusters.addCluster(
        True, name=config.CLUSTER_ISCSI_CONNECTIONS,
        cpu=config.CPU_NAME,
        data_center=config.DATACENTER_ISCSI_CONNECTIONS,
        version=config.COMP_VERSION
    ):
        raise exceptions.ClusterException(
            "Failed to create cluster '%s'" % config.CLUSTER_ISCSI_CONNECTIONS
        )
    if not hl_hosts.move_host_to_another_cluster(
        config.HOST_FOR_MOUNT, config.CLUSTER_ISCSI_CONNECTIONS
    ):
        raise exceptions.HostException(
            "Failed to migrate host '%s' into cluster '%s'" % (
                config.HOST_FOR_MOUNT, config.CLUSTER_ISCSI_CONNECTIONS
            )
        )


def _compare_connections(conn_1, conn_2):
    return conn_1.__dict__ == conn_2.__dict__


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


class TestCase(StorageTest):
    storages = set([config.STORAGE_TYPE_ISCSI])

    def get_all_new_connections(self):
        return _filter_storage_connections(
            self.original_conn,
            ll_storageconnections.get_all_storage_connections()
        )


@pytest.mark.usefixtures(
    logout_all_iscsi_targets.__name__,
    remove_storage_connections.__name__,
    remove_storage_domains.__name__,
)
class TestCase5243(TestCase):
    """
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_3_Storage_Manage_Storage_Connections
    """
    __test__ = config.STORAGE_TYPE_ISCSI in ART_CONFIG['RUN']['storages']
    polarion_test_case = '5243'
    conn = None
    sd_name = None

    @tier3
    @polarion("RHEVM3-5243")
    def test_adding_storage_connections(self):
        """
        test adding a storage connection to a dc without storage domains
        and to a dc with a storage domain
        """
        testflow.step(
            "Add a connection to the empty dc %s",
            config.DATACENTER_ISCSI_CONNECTIONS
        )
        conn_dict = dict(config.CONNECTIONS[0]).copy()
        conn_dict['type'] = config.STORAGE_TYPE_ISCSI
        conn, success = ll_storageconnections.add_connection(**conn_dict)
        assert success, "Adding storage connection failed"

        ll_storageconnections.remove_storage_connection(conn.id)
        self.sd_name = storage_helpers.create_unique_object_name(
            self.__name__, config.OBJECT_TYPE_SD
        )
        testflow.step("Add storage domain %s", self.sd_name)
        assert ll_sd.addStorageDomain(
            True, host=config.HOST_FOR_MOUNT, name=self.sd_name,
            type=config.TYPE_DATA, storage_type=config.STORAGE_TYPE_ISCSI,
            override_luns=True, lun=config.CONNECTIONS[0]['luns'][0],
            **(config.CONNECTIONS[0])
        ), "Failed to create storage domain '%s'" % self.sd_name
        self.storage_domains.append(self.sd_name)
        old_conns_for_sd = ll_sd.getConnectionsForStorageDomain(self.sd_name)
        assert len(old_conns_for_sd) == 1, "The connection count is not 1"
        old_conn = old_conns_for_sd[0]

        logger.info(
            "Add the same connection to a data center with a storage domain "
            "- should fail"
        )
        conn, success = ll_storageconnections.add_connection(**conn_dict)
        assert not success, "Adding the same storage connection succeeded"
        conns_for_sd = ll_sd.getConnectionsForStorageDomain(self.sd_name)
        assert len(conns_for_sd) == 1, "The connection count is not 1"
        new_conn = conns_for_sd[0]
        assert _compare_connections(old_conn, new_conn), (
            "The connection count is different before adding the duplicate "
            "connection"
        )


@pytest.mark.usefixtures(
    remove_storage_connections.__name__,
)
class TestCase5247(TestCase):
    """
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_3_Storage_Manage_Storage_Connections
    """
    __test__ = config.STORAGE_TYPE_ISCSI in ART_CONFIG['RUN']['storages']
    # Other apis try convert the value type so this cases will not work, only
    # execute on rest
    apis = set(['rest'])
    conn = None
    sd_name = None

    def add_connection_without_sth(self, param, value=None):
        testflow.step(
            "Add storage connention with parameter %s with value as %s",
            param, value
        )
        conn = dict(config.CONNECTIONS[0]).copy()
        conn['type'] = config.STORAGE_TYPE_ISCSI
        if value:
            conn[param] = value
        else:
            conn.pop(param)
        conn, success = ll_storageconnections.add_connection(**conn)
        assert not success, "Add storage connection was expected to fail"

    def add_connection_with_empty_sth(self, param):
        testflow.step(
            "Add storage connention without parameter %s", param
        )
        conn = dict(config.CONNECTIONS[0]).copy()
        conn['type'] = config.STORAGE_TYPE_ISCSI
        conn[param] = ''
        conn, success = ll_storageconnections.add_connection(**conn)
        assert not success, "Add storage connection was expected to fail"

    @tier3
    @polarion("RHEVM3-5247")
    def test_adding_storage_connection_without_ip(self):
        """ try to add an iscsi storage connection without LUN address
        """
        self.add_connection_without_sth('lun_address')
        self.add_connection_with_empty_sth('lun_address')

    # TODO: validator fails to send the request
    # @polarion("RHEVM3-5247")
    # def test_adding_storage_connection_without_port(self):
    #     """ try to add an iscsi storage connection without LUN port
    #     """
    #     self.add_connection_without_sth('lun_port')
    #     old_conn = ll_storageconnections.StorageConnection
    #     ll_storageconnections.StorageConnection = (
    #         hl_datastructures.StorageConnection
    #     )
    #     try:
    #         self.add_connection_with_empty_sth('lun_port')
    #     finally:
    #         ll_storageconnections.StorageConnection = old_conn

    @tier3
    @polarion("RHEVM3-5247")
    def test_adding_storage_connection_without_target(self):
        """ try to add an iscsi storage connection without LUN target
        """
        self.add_connection_without_sth('lun_target')
        self.add_connection_with_empty_sth('lun_target')

    # TODO: validator fails to send the request
    # @polarion("RHEVM3-5247")
    # def test_adding_storage_connection_with_string_as_port(self):
    #     """ try to add an iscsi storage connection with a string as a port
    #     """
    #     old_conn = ll_storageconnections.StorageConnection
    #     ll_storageconnections.StorageConnection = (
    #         hl_datastructures.StorageConnection
    #     )
    #     try:
    #         self.add_connection_without_sth('lun_port', 'aaa')
    #     finally:
    #         ll_storageconnections.StorageConnection = old_conn

    @tier3
    @polarion("RHEVM3-5247")
    def test_add_the_same_connection_twice(self):
        """ try to add an iscsi storage connection twice
            and add it after it was removed
        """
        conn = dict(config.CONNECTIONS[0]).copy()
        conn['type'] = config.STORAGE_TYPE_ISCSI
        conn_obj_1, success = ll_storageconnections.add_connection(**conn)
        assert success, "Add storage connection was expected to succeed"
        conn_obj_2, success = ll_storageconnections.add_connection(**conn)
        assert not success, "Add storage connection was expected to fail"
        assert ll_storageconnections.remove_storage_connection(
            conn_obj_1.id
        ), (
            "Removing storage connection failed"
        )
        conn_obj, success = ll_storageconnections.add_connection(**conn)
        assert success, "Add storage connection was expected to succeed"


@pytest.mark.usefixtures(
    add_storage_connections.__name__,
)
class TestCase5248(TestCase):
    """
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_3_Storage_Manage_Storage_Connections
    """
    __test__ = config.STORAGE_TYPE_ISCSI in ART_CONFIG['RUN']['storages']
    polarion_test_case = '5248'
    conn_1 = None
    conn_2 = None
    sd_name = None

    @tier3
    def change_connection_without_sth(self, conn, param):
        testflow.step("Change storage connection param %s to None", param)
        conn_params = {}
        conn_params[param] = ''
        conn_params['type'] = config.STORAGE_TYPE_ISCSI
        _, success = ll_storageconnections.update_connection(
            True, conn.id, **conn_params
        )
        assert not success, "Update storage connection was expected to fail"

    @tier3
    @polarion("RHEVM3-5248")
    def test_changing_storage_connection_without_ip(self):
        """ try to change an iscsi connection and set LUN address to nothing
        """
        self.change_connection_without_sth(self.conn_1, 'lun_address')

    # TODO: failure in datastructures
    # @polarion("RHEVM3-5248")
    # def test_changing_storage_connection_without_port(self):
    #     """ try to change an iscsi connection and set LUN port to nothing
    #     """
    #     old_conn = ll_storageconnections.StorageConnection
    #     ll_storageconnections.StorageConnection = (
    #         hl_datastructures.StorageConnection
    #     )
    #     try:
    #         self.change_connection_without_sth(self.conn_1, 'lun_port')
    #     finally:
    #         ll_storageconnections.StorageConnection = old_conn

    @tier3
    @polarion("RHEVM3-5248")
    def test_changing_storage_connection_without_target(self):
        """ try to change an iscsi connection and set LUN target to nothing
        """
        self.change_connection_without_sth(self.conn_1, 'lun_target')

    @tier3
    @polarion("RHEVM3-5248")
    def test_changing_storage_connection_to_existing_one(self):
        """ try to change an iscsi connection and set all values as in another
        """
        _, success = ll_storageconnections.update_connection(
            True, self.conn_1.id, **self.conn_2_params
        )
        assert not success, "update storage connection was expected to fail"


@bz({'1478869': {}})
@pytest.mark.usefixtures(
    logout_all_iscsi_targets.__name__,
    empty_dc.__name__,
    add_storage_domain_and_connections.__name__,
)
class TestCase5246(TestCase):
    """
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_3_Storage_Manage_Storage_Connections
    """
    __test__ = config.STORAGE_TYPE_ISCSI in ART_CONFIG['RUN']['storages']
    polarion_test_case = '5246'
    sd_name_1 = "sd_%s_1" % polarion_test_case
    sd_name_2 = "sd_%s_2" % polarion_test_case
    master_sd = "master_%s" % polarion_test_case

    @tier3
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
        testflow.step("Try to remove the storage connection - should fail")
        conns = ll_sd.getConnectionsForStorageDomain(self.sd_name_1)
        conn_id = conns[0].id
        assert not ll_storageconnections.remove_storage_connection(conn_id), (
            "Removing storage connection succeeded"
        )

        test_utils.wait_for_tasks(
            engine=config.ENGINE,
            datacenter=config.DATACENTER_ISCSI_CONNECTIONS
        )
        test_utils.wait_for_tasks(
            engine=config.ENGINE,
            datacenter=config.DATACENTER_ISCSI_CONNECTIONS
        )
        testflow.step("Put the first domain into maintenance")
        assert ll_sd.deactivateStorageDomain(
            True, config.DATACENTER_ISCSI_CONNECTIONS, self.sd_name_1
        ), "Deactivating storage domain '%s' failed" % self.sd_name_1
        testflow.step("Try to remove the storage connection - should fail")
        assert not ll_storageconnections.remove_storage_connection(conn_id), (
            "Removing the storage connection was expected to fail"
        )
        testflow.step("Detach the storage connection from the first domain")
        assert ll_sd.detachConnectionFromStorageDomain(
            self.sd_name_1, conn_id
        ), "Detaching storage connection failed"
        testflow.step("Try to remove the storage connection - should fail")
        assert not ll_storageconnections.remove_storage_connection(
            conn_id
        ), "Removing the storage connection was expected to fail"

        testflow.step("Put the second storage domain into maintenance")
        test_utils.wait_for_tasks(
            engine=config.ENGINE,
            datacenter=config.DATACENTER_ISCSI_CONNECTIONS
        )
        test_utils.wait_for_tasks(
            engine=config.ENGINE,
            datacenter=config.DATACENTER_ISCSI_CONNECTIONS
        )
        assert ll_sd.deactivateStorageDomain(
            True, config.DATACENTER_ISCSI_CONNECTIONS, self.sd_name_2
        ), "Deactivating storage domain '%s' failed" % self.sd_name_2
        testflow.step("Try to remove the storage connection - should fail")
        assert not ll_storageconnections.remove_storage_connection(conn_id), (
            "Removing the storage connection was expected to fail"
        )
        testflow.step("Detach the storage connection from the second domain")
        assert ll_sd.detachConnectionFromStorageDomain(
            self.sd_name_2, conn_id
        ), "Detaching connection from storage domain failed"
        testflow.step("Try to remove the storage connection - should succeed")
        assert ll_storageconnections.remove_storage_connection(
            conn_id
        ), "Removing storage connection failed"


@pytest.mark.usefixtures(
    generate_random_storage_connections.__name__,
)
class TestCase5240(TestCase):
    """
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_3_Storage_Manage_Storage_Connections
    """
    __test__ = config.STORAGE_TYPE_ISCSI in ART_CONFIG['RUN']['storages']
    polarion_test_case = '5240'
    conns = []
    no_of_conn = 10
    con_params = []

    @tier3
    @polarion("RHEVM3-5240")
    def test_change_multiple_connections(self):
        """
        Test steps:
        * Try to switch 2 connections
        * Try to change 10 connections at once
        """
        testflow.step("Trying to switch 2 connections")
        with ThreadPoolExecutor(max_workers=config.MAX_WORKERS) as executor:
            result_1 = executor.submit(
                ll_storageconnections.update_connection,
                True, self.conns[0].id, ** self.con_params[1]
            )
            result_2 = executor.submit(
                ll_storageconnections.update_connection,
                True, self.conns[1].id, ** self.con_params[0]
            )
        assert result_1.result()[1] == result_2.result()[1], (
            "Updating storage connections failed"
        )

        conn_1 = ll_storageconnections.get_storage_connection_object(
            self.conns[0].id, 'id'
        )
        conn_2 = ll_storageconnections.get_storage_connection_object(
            self.conns[1].id, 'id'
        )

        assert not _compare_connections(
            conn_1, conn_2
        ), "Connections were expected to be different"

        testflow.step("Trying to change 10 connections at once")
        results = []
        with ThreadPoolExecutor(max_workers=config.MAX_WORKERS) as executor:
            for conn in self.conns:
                results.append(
                    executor.submit(
                        ll_storageconnections.update_connection,
                        True, conn.id,
                        lun_target="aaa" + conn.target,
                        type=config.STORAGE_TYPE_ISCSI
                    )
                )
        for result in results:
            assert result.result(), "Connection failed"


@pytest.mark.usefixtures(
    logout_all_iscsi_targets.__name__,
    empty_dc.__name__,
    initialize_variables_remove_leftover_domains.__name__,
)
class TestCase5242(TestCase):
    """
    Verify the GET call works for various storage connection/storage domains
    combinations
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_3_Storage_Manage_Storage_Connections
    """
    __test__ = config.STORAGE_TYPE_ISCSI in ART_CONFIG['RUN']['storages']
    polarion_test_case = '5242'

    @tier3
    @polarion("RHEVM3-5242")
    def test_verify_one_orphaned_connection(self):
        """
        Verifying GET for one orphaned connection
        """
        testflow.step("Verifying get for one orphaned connection")
        conn_1 = dict(config.CONNECTIONS[0]).copy()
        conn_1['type'] = config.STORAGE_TYPE_ISCSI
        self.conn, success = ll_storageconnections.add_connection(**conn_1)
        assert success, "Error adding storage connection %s" % conn_1
        self.storage_connections.append(self.conn.id)
        new_conn = self.get_all_new_connections()
        assert len(new_conn) == 1, (
            "The number of new connections was expected to be 1"
        )
        ll_storageconnections.remove_storage_connection(self.conn.id)
        self.storage_connections.remove(self.conn.id)

    @tier3
    @polarion("RHEVM3-5242")
    def test_verify_one_storage_domain(self):
        """
        Verifying GET for one storage domain
        """
        testflow.step("Verifying get for one orphaned connection")
        sd_name = storage_helpers.create_unique_object_name(
            self.__name__, config.OBJECT_TYPE_SD
        )
        assert ll_sd.addStorageDomain(
            True, host=config.HOST_FOR_MOUNT, name=sd_name,
            type=config.TYPE_DATA, storage_type=config.STORAGE_TYPE_ISCSI,
            override_luns=True, lun=config.CONNECTIONS[0]['luns'][0],
            **(config.CONNECTIONS[0])
        ), "Failed to create storage domain %s" % sd_name
        self.storage_domains.append(sd_name)
        new_conn = self.get_all_new_connections()
        conn_for_sd = ll_sd.getConnectionsForStorageDomain(sd_name)
        assert len(new_conn) == 1, (
            "The number of storage connections was expected to be 1"
        )
        assert len(conn_for_sd) == 1, (
            "The number of storage connections for the storage domain was "
            "expected to be 1"
        )
        assert _compare_connections(new_conn[0], conn_for_sd[0]), (
            "The storage connection and the connection for the storage "
            "domain do not match"
        )
        assert ll_sd.removeStorageDomain(
            True, sd_name, config.HOST_FOR_MOUNT, 'true'
        ), "Failed to remove storage domain '%s'" % sd_name
        self.storage_domains.remove(sd_name)
        new_conn = self.get_all_new_connections()
        assert len(new_conn) == 0, "New connections was expected to be 0"

    @tier3
    @polarion("RHEVM3-5242")
    def test_verify_storage_domain_with_two_connections(self):
        """
        Verifying GET for one storage domain using multiple
        storage connections
        """
        testflow.step("Verifying get for one storage domain")
        sd_name = storage_helpers.create_unique_object_name(
            self.__name__, config.OBJECT_TYPE_SD
        )
        assert ll_sd.addStorageDomain(
            True, host=config.HOST_FOR_MOUNT, name=sd_name,
            type=config.TYPE_DATA, storage_type=config.STORAGE_TYPE_ISCSI,
            override_luns=True, lun=config.CONNECTIONS[0]['luns'][0],
            **(config.CONNECTIONS[0])
        ), "Failed to create storage domain '%s'" % sd_name
        self.storage_domains.append(sd_name)
        assert ll_sd.attachStorageDomain(
            True, config.DATACENTER_ISCSI_CONNECTIONS, sd_name
        ), "Failed to attach storage domain '%s'" % sd_name
        self.storage_domains.remove(sd_name)
        assert ll_sd.wait_for_storage_domain_status(
            True, config.DATACENTER_ISCSI_CONNECTIONS, sd_name,
            config.SD_ACTIVE
        ), "Storage domain '%s' failed to become active" % sd_name
        new_sd_connections = self.get_all_new_connections()
        logger.info(
            "The number of new connections created when storage domain '%s' "
            "was added is '%s'", sd_name, len(new_sd_connections)
        )
        hl_sd._ISCSIdiscoverAndLogin(
            config.HOST_FOR_MOUNT, config.CONNECTIONS[1]['lun_address'],
            config.CONNECTIONS[1]['lun_target']
        )
        assert ll_sd.extendStorageDomain(
            True, sd_name, storage_type=config.STORAGE_TYPE_ISCSI,
            host=config.HOST_FOR_MOUNT, override_luns=True,
            lun=config.CONNECTIONS[1]['luns'][1], **(config.CONNECTIONS[1])
        ), "Failed to extend storage domain '%s'" % sd_name
        connections_for_sd = ll_sd.getConnectionsForStorageDomain(sd_name)
        extend_sd_connections = self.get_all_new_connections()
        logger.info(
            "The number of new connections is: '%s'",
            len(extend_sd_connections)
        )
        assert len(connections_for_sd) == 2, (
            "2 storage connection are expected for storage domain '%s'" %
            sd_name
        )
        assert len(extend_sd_connections) == len(new_sd_connections) + 1, (
            "1 additional connection was expected after extending storage "
            "domain '%s'" % sd_name
        )

    @tier3
    @polarion("RHEVM3-5242")
    def test_verify_two_storage_domains_with_the_same_connection(self):
        """
        Verifying get for a storage domain with 2 connections
        """
        testflow.step("Verifying get for a storage domain with 2 connections")
        sd_name_1 = storage_helpers.create_unique_object_name(
            self.__name__, config.OBJECT_TYPE_SD
        )
        ll_sd.addStorageDomain(
            True, host=config.HOST_FOR_MOUNT, name=sd_name_1,
            type=config.TYPE_DATA, storage_type=config.STORAGE_TYPE_ISCSI,
            override_luns=True, lun=config.CONNECTIONS[0]['luns'][0],
            **(config.CONNECTIONS[0])
        )
        self.storage_domains.append(sd_name_1)
        sd_name_2 = storage_helpers.create_unique_object_name(
            self.__name__, config.OBJECT_TYPE_SD
        )
        ll_sd.addStorageDomain(
            True, host=config.HOST_FOR_MOUNT, name=sd_name_2,
            type=config.TYPE_DATA, storage_type=config.STORAGE_TYPE_ISCSI,
            override_luns=True, lun=config.CONNECTIONS[0]['luns'][1],
            **(config.CONNECTIONS[0])
        )
        self.storage_domains.append(sd_name_2)

        conn_sd_1 = ll_sd.getConnectionsForStorageDomain(sd_name_1)
        conn_sd_2 = ll_sd.getConnectionsForStorageDomain(sd_name_2)
        assert len(conn_sd_1) == len(conn_sd_2), (
            "The number of storage connections for storage domain '%s' and "
            "'%s' does not match" % (sd_name_1, sd_name_2)
        )
        assert _compare_connections(
            conn_sd_1[0], conn_sd_2[0]
        ), "The connections for storage domains '%s' and '%s' do not match" % (
            sd_name_1, sd_name_2
        )
        assert ll_sd.removeStorageDomain(
            True, sd_name_1, config.HOST_FOR_MOUNT, 'true'
        ), "Failed to remove storage domain '%s'" % sd_name_1
        self.storage_domains.remove(sd_name_1)
        assert ll_sd.removeStorageDomain(
            True, sd_name_2, config.HOST_FOR_MOUNT, 'true'
        ), "Failed to remove storage domain '%s'" % sd_name_2
        self.storage_domains.remove(sd_name_2)
        new_conn = self.get_all_new_connections()
        assert not new_conn, "No new connections were expected"

    @tier3
    @polarion("RHEVM3-5242")
    def test_verify_one_direct_lun(self):
        """
        Verifying get for direct LUN
        """
        testflow.step("Verifying get for direct LUN")
        alias = storage_helpers.create_unique_object_name(
            self.__name__, config.OBJECT_TYPE_DISK
        )
        ll_disks.addDisk(
            True, alias=alias, interface=config.DISK_INTERFACE_VIRTIO,
            format=config.DISK_FORMAT_COW, type_=config.STORAGE_TYPE_ISCSI,
            lun_id=config.CONNECTIONS[0]['luns'][0],
            lun_address=config.CONNECTIONS[0]['lun_address'],
            lun_target=config.CONNECTIONS[0]['lun_target']
        )

        self.disks.append(alias)
        new_conn = self.get_all_new_connections()
        assert len(new_conn) == 1, "1 new storage connection was expected"
        # TODO: When the API allows it, check the storage connection of
        # a direct lun, something like:
        # conn_disk = ll_disks.getConnectionsForDisk(alias)
        # assert _compare_connections(all_conn, conn_disk), "Text"
        # https://bugzilla.redhat.com/show_bug.cgi?id=1227322
        assert ll_disks.deleteDisk(
            True, alias
        ), "Deleting disk '%s' failed" % alias
        self.disks.remove(alias)


@pytest.mark.usefixtures(
    add_two_storage_domains.__name__,
    logout_all_iscsi_targets.__name__,
    empty_dc.__name__,
)
class TestCase5245(TestCase):
    """
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_3_Storage_Manage_Storage_Connections
    """
    __test__ = config.STORAGE_TYPE_ISCSI in ART_CONFIG['RUN']['storages']
    polarion_test_case = '5245'
    conn = None

    def _try_to_change_connection(self, conn_id, should_pass):
        """
        Try to update connection conn_id, should succeed if should_pass is True
        """
        for parameter in ['lun_address', 'lun_target', 'lun_port']:
            fail_action = 'Unable' if should_pass else 'Able'
            assert should_pass == ll_storageconnections.update_connection(
                True, conn_id, type=config.STORAGE_TYPE_ISCSI,
                **{parameter: config.CONNECTIONS[1][parameter]}
            )[1], "{0} to update the storage connection {1}".format(
                fail_action, conn_id
            )

    @tier3
    @polarion("RHEVM3-5245")
    def test_change_connection_in_sd(self):
        """
        Test steps:
        * Try to change the connection (IP address, port, target, user,
        password)
        * Put one of the storage domains into maintenance
        * Try to change the connection
        * Put the other storage domain into maintenance
        * Try to change the storage connection:
        * IP address
        * Port
        * Target
        * ID
        * Activate the storage domains
        * Try to change parameters of non existent storage domain
        """
        conn = ll_sd.getConnectionsForStorageDomain(self.sd_name_1)[0]
        testflow.step("Trying to change the connection - should fail")
        self._try_to_change_connection(conn.id, False)
        logger.info("Waiting for tasks before deactivating the storage domain")
        test_utils.wait_for_tasks(
            engine=config.ENGINE,
            datacenter=config.DATACENTER_ISCSI_CONNECTIONS
        )

        testflow.step("Deactivating one of the storage domains")
        assert ll_sd.deactivateStorageDomain(
            True, config.DATACENTER_ISCSI_CONNECTIONS, self.sd_name_2
        ), "Failed to deactivate storage domain '%s'" % self.sd_name_2
        testflow.step("Trying to change the connection - should fail")
        self._try_to_change_connection(conn.id, False)
        logger.info("Waiting for tasks before deactivating the storage domain")
        test_utils.wait_for_tasks(
            engine=config.ENGINE,
            datacenter=config.DATACENTER_ISCSI_CONNECTIONS
        )

        testflow.step("Deactivating both storage domains")
        assert ll_sd.deactivateStorageDomain(
            True, config.DATACENTER_ISCSI_CONNECTIONS, self.sd_name_1
        ), "Failed to deactivate storage domain '%s'" % self.sd_name_1
        testflow.step("Trying to change the connection - should succeed")
        self._try_to_change_connection(conn.id, True)
        assert ll_sd.activateStorageDomain(
            True, config.DATACENTER_ISCSI_CONNECTIONS, self.sd_name_1
        ), "Failed to activate storage domain '%s'" % self.sd_name_1
        assert ll_sd.activateStorageDomain(
            True, config.DATACENTER_ISCSI_CONNECTIONS, self.sd_name_2
        ), "Failed to activate storage domain '%s'" % self.sd_name_2


@pytest.mark.usefixtures(
    add_two_storage_domains.__name__,
    add_new_storage_connection.__name__,
    logout_all_iscsi_targets.__name__,
    empty_dc.__name__,
)
class TestCase5244(TestCase):
    """
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_3_Storage_Manage_Storage_Connections
    """
    __test__ = config.STORAGE_TYPE_ISCSI in ART_CONFIG['RUN']['storages']
    polarion_test_case = '5244'
    conn = None
    conn_idx = 1

    @tier3
    @polarion("RHEVM3-5244")
    def test_add_connection_to_sd(self):
        """
        Test steps:
        * Try to add the connection to one of the storage domains
        * Put one of the storages domain into maintenance
        * Add the iSCSI connection to the storage domain
        * Activate the storage domain
        * Put the other storage domain into maintenance
        * Add the iSCSI connection to the inactive storage domain
        * Try to add the same connection again
        * Activate the storage domain
        """
        assert not ll_sd.addConnectionToStorageDomain(
            self.sd_name_1, self.conn.id
        ), "Added storage connection to active domain '%s'" % (
            self.sd_name_1
        )
        logger.info("Waiting for tasks before deactivating the storage domain")
        test_utils.wait_for_tasks(
            engine=config.ENGINE,
            datacenter=config.DATACENTER_ISCSI_CONNECTIONS
        )
        assert hl_sd.deactivate_domain(
            config.DATACENTER_ISCSI_CONNECTIONS, self.sd_name_1, config.ENGINE
        ), "Failed to deactivate storage domain '%s'" % self.sd_name_1
        assert ll_sd.addConnectionToStorageDomain(
            self.sd_name_1, self.conn.id
        ), "Failed to add storage connection to domain '%s'" % self.sd_name_1
        assert ll_sd.activateStorageDomain(
            True, config.DATACENTER_ISCSI_CONNECTIONS, self.sd_name_1
        ), "Failed to activate storage domain '%s'" % self.sd_name_1
        logger.info("Waiting for tasks before deactivating the storage domain")
        test_utils.wait_for_tasks(
            engine=config.ENGINE,
            datacenter=config.DATACENTER_ISCSI_CONNECTIONS
        )
        assert ll_sd.deactivateStorageDomain(
            True, config.DATACENTER_ISCSI_CONNECTIONS, self.sd_name_2
        ), "Failed to deactivate storage domain '%s'" % self.sd_name_2
        assert ll_sd.addConnectionToStorageDomain(
            self.sd_name_2, self.conn.id
        ), "Failed to add storage connection to domain '%s'" % self.sd_name_2
        assert not ll_sd.addConnectionToStorageDomain(
            self.sd_name_2, self.conn.id
        ), "Succeeded to add a duplicate connection to storage domain '%s'" % (
            self.sd_name_2
        )
        assert ll_sd.activateStorageDomain(
            True, config.DATACENTER_ISCSI_CONNECTIONS, self.sd_name_2
        ), "Failed to activate storage domain '%s'" % self.sd_name_2


@bz({'1476119': {}})
@pytest.mark.usefixtures(
    add_nfs_domain_generate_vms.__name__,
    logout_all_iscsi_targets.__name__,
    empty_dc.__name__,
    remove_vms.__name__,
)
class TestCase5241(TestCase):
    """
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_3_Storage_Manage_Storage_Connections
    """
    __test__ = config.STORAGE_TYPE_ISCSI in ART_CONFIG['RUN']['storages']
    polarion_test_case = '5241'
    conn = None
    vm_name_1 = "vm_%s_1" % polarion_test_case
    vm_name_2 = "vm_%s_2" % polarion_test_case
    disk_1 = "disk_%s_1" % polarion_test_case
    sd_name = "sd_%s" % polarion_test_case
    disk_2 = "disk_%s_2" % polarion_test_case

    @tier3
    @polarion("RHEVM3-5241")
    def test_change_connection_in_lun(self):
        """
        Test steps:
        * Try to change the connection (IP address, port, target)
        * Stop one of the vms
        * Try to change the connection
        * Stop the other vm
        * Try to change the connection (IP address, port, target)
        * Run both vms again
        """
        # TODO: When the API allows it, get the storage connection of
        # a direct lun, instead of looping through all of them
        # https://bugzilla.redhat.com/show_bug.cgi?id=1227322
        connections = ll_storageconnections.get_all_storage_connections()
        lun_conn = None
        for conn in connections:
            if conn.target == config.CONNECTIONS[0]['lun_target']:
                lun_conn = conn
                break

        assert lun_conn, (
            "The connection target does not match the configured target"
        )

        assert not ll_storageconnections.update_connection(
            True, lun_conn.id,
            lun_address=config.CONNECTIONS[1]['lun_address'],
            type=config.STORAGE_TYPE_ISCSI
        )[1], "Succeeded to update connection in use"

        assert ll_vms.stopVm(True, self.vm_name_1), (
            "Failed to power off VM '%s'" % self.vm_name_1
        )
        assert ll_vms.waitForVMState(
            self.vm_name_1, config.VM_DOWN
        ), "VM '%s' failed to reach powered off state" % self.vm_name_1

        assert ll_storageconnections.update_connection(
            False, lun_conn.id,
            lun_address=config.CONNECTIONS[1]['lun_address'],
            type=config.STORAGE_TYPE_ISCSI
        )[1], "Succeeded to update a connection that is in use"

        assert ll_vms.stopVm(True, self.vm_name_2), (
            "Failed to power off VM '%s'" % self.vm_name_2
        )
        assert ll_vms.waitForVMState(
            self.vm_name_2, config.VM_DOWN
        ), "VM '%s' failed to reach powered off state" % self.vm_name_2

        assert ll_storageconnections.update_connection(
            True, lun_conn.id, type=config.STORAGE_TYPE_ISCSI,
            **(config.CONNECTIONS[1])
        )[1], "Failed to update storage connection"

        assert ll_vms.startVm(True, self.vm_name_1), (
            "Failed to power on VM '%s'" % self.vm_name_1
        )
        assert ll_vms.startVm(True, self.vm_name_2), (
            "Failed to power on VM '%s'" % self.vm_name_2
        )


@pytest.mark.usefixtures(
    add_new_storage_connection.__name__,
    logout_all_iscsi_targets.__name__,
    remove_storage_connections.__name__,
    remove_storage_domains.__name__,
)
class TestCase5249(TestCase):
    """
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_3_Storage_Manage_Storage_Connections
    """
    __test__ = config.STORAGE_TYPE_ISCSI in ART_CONFIG['RUN']['storages']
    polarion_test_case = '5249'
    conn = None
    conn_idx = 0

    @tier3
    @polarion("RHEVM3-5249")
    def test_adding_storage_domains(self):
        """
        Test steps:
        * a storage domain using a new connection (old flow)
        * a storage domain with all params specified (old flow), but
          the connection params are the same of an existing connection
          In the last case, new connection should not be added.
        """
        testflow.step("Adding a new storage domain with a new connection")
        sd_name_2 = storage_helpers.create_unique_object_name(
            self.__name__, config.OBJECT_TYPE_SD
        )
        assert ll_sd.addStorageDomain(
            True, name=sd_name_2, host=config.HOST_FOR_MOUNT,
            type=config.TYPE_DATA,
            storage_type=config.STORAGE_TYPE_ISCSI,
            override_luns=True, lun=config.CONNECTIONS[1]['luns'][0],
            **(config.CONNECTIONS[1])
        ), "Failed to create storage domain '%s'" % sd_name_2
        self.storage_domains.append(sd_name_2)

        sd_name_2_conn = ll_sd.getConnectionsForStorageDomain(sd_name_2)
        logger.info(
            "Connection of storage domain %s is: %s",
            sd_name_2, sd_name_2_conn[0].id
        )
        assert len(sd_name_2_conn) == 1, (
            "The expected number of storage connections was 1"
        )
        assert ll_sd.removeStorageDomain(
            True, sd_name_2, config.HOST_FOR_MOUNT, 'true'
        ), "Failed to remove storage domain '%s'" % sd_name_2
        self.storage_domains.remove(sd_name_2)

        testflow.step(
            "Adding a new domain specifying the parameters but using the "
            "existing connection"
        )
        sd_name_3 = storage_helpers.create_unique_object_name(
            self.__name__, config.OBJECT_TYPE_SD
        )
        assert ll_sd.addStorageDomain(
            True, name=sd_name_3, host=config.HOST_FOR_MOUNT,
            type=config.TYPE_DATA,
            storage_type=config.STORAGE_TYPE_ISCSI,
            override_luns=True, lun=config.CONNECTIONS[0]['luns'][1],
            **(config.CONNECTIONS[0])
        ), "Failed to create storage domain '%s'" % sd_name_3
        sd_name_3_conn = ll_sd.getConnectionsForStorageDomain(sd_name_3)
        logger.info(
            "Connection of storage domain %s is: %s",
            sd_name_3, sd_name_3_conn[0].id
        )
        self.storage_domains.append(sd_name_3)
