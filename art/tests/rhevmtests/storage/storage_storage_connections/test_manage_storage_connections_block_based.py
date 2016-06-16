from concurrent.futures import ThreadPoolExecutor
import logging
from unittest2 import SkipTest
import config
import helpers
from art.rhevm_api.utils import test_utils
from art.rhevm_api.tests_lib.high_level import (
    datacenters as hl_dc,
    datastructures as hl_datastructures,
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
    templates as ll_templates,
    vms as ll_vms,
)
import art.test_handler.exceptions as errors
from art.test_handler.settings import opts
from art.test_handler.tools import bz, polarion
from art.test_handler import exceptions
from art.unittest_lib import attr, StorageTest
import rhevmtests.storage.helpers as storage_helpers

logger = logging.getLogger(__name__)

ISCSI_SDS = []


def setup_module():
    """
    Remove all the storage domains since we need an empty DC
    """
    if config.PPC_ARCH:
        # TODO: Enable for PPC when the targets are configured for the
        # environment and properly tested
        raise SkipTest("Additional iscsi targets not configured")
    global ISCSI_SDS
    # All of the storage connections need to be removed, and the host
    # should be logged out from all targets for these tests. This is due
    # to the fact that when adding a new storage domain or direct lun,
    # ovirt will automatically link the storage  domains with the existing
    # host's logged targets
    logger.info("Removing all iscsi storage domains for test")
    ISCSI_SDS = ll_sd.getStorageDomainNamesForType(
        config.DATA_CENTER_NAME, config.STORAGE_TYPE_ISCSI
    )
    addresses, targets = hl_sd.discover_addresses_and_targets(
        config.HOSTS[0], config.UNUSED_LUN_ADDRESSES[0]
    )
    config.CONNECTIONS[0]['lun_address'] = addresses[0]
    logger.info("1st storage connection address to use is: %s", addresses[0])
    config.CONNECTIONS[0]['lun_target'] = targets[0]
    config.CONNECTIONS[1]['lun_address'] = addresses[1]
    logger.info("2nd storage connection address to use is: %s", addresses[1])
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
        if not ll_sd.removeStorageDomain(
            positive=True, storagedomain=sd, host=config.HOST_FOR_MOUNT,
            format='false'
        ):
            raise exceptions.StorageDomainException(
                "Failed to remove and format storage domain '%s'" % sd
            )

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
    helpers.logout_from_all_iscsi_targets()


def teardown_module():
    """
    Remove empty DC
    """
    test_failed = False
    if not hl_dc.clean_datacenter(
        True, datacenter=config.DATACENTER_ISCSI_CONNECTIONS,
        formatExpStorage='true', vdc=config.VDC,
        vdc_password=config.VDC_PASSWORD
    ):
        logger.error(
            "Failed to clean Data center '%s'",
            config.DATACENTER_ISCSI_CONNECTIONS
        )
        test_failed = True
    if not ll_hosts.addHost(
        True, config.HOST_FOR_MOUNT, address=config.HOST_FOR_MOUNT_IP,
        wait=True, reboot=False, cluster=config.CLUSTER_NAME,
        root_password=config.VDC_ROOT_PASSWORD
    ):
        logger.error(
            "Failed to add host '%s' into cluster '%s'",
            config.HOST_FOR_MOUNT, config.CLUSTER_NAME
        )
        test_failed = True
    helpers.logout_from_all_iscsi_targets()

    logger.info("Importing iscsi storage domains back")
    # Importing all iscsi domains using the address and target of one of them
    imported = hl_sd.importBlockStorageDomain(
        config.HOSTS[0], config.LUN_ADDRESSES[0],
        config.LUN_TARGETS[0]
    )
    if not imported:
        logger.error("Failed to import iSCSI domains back")
    for sd in ISCSI_SDS:
        hl_sd.attach_and_activate_domain(config.DATA_CENTER_NAME, sd)
    hl_dc.ensure_data_center_and_sd_are_active(config.DATA_CENTER_NAME)
    template_name = config.TEMPLATE_NAME[0]
    disk = ll_templates.getTemplateDisks(template_name)[0].get_alias()
    if imported:
        register_failed = False
        for sd in ISCSI_SDS:
            logger.info(
                "Copying disk %s for template %s to sd %s",
                disk, template_name, sd
            )
            if not ll_templates.copyTemplateDisk(template_name, disk, sd):
                logger.error(
                    "Failed to copy template disk to imported iSCSI domain %s",
                    sd
                )
            ll_templates.wait_for_template_disks_state(template_name)
            unregistered_vms = ll_sd.get_unregistered_vms(sd)
            if unregistered_vms:
                for vm in unregistered_vms:
                    if not ll_sd.register_object(
                        vm, cluster=config.CLUSTER_NAME
                    ):
                        logger.error(
                            "Failed to register vm %s from imported domain "
                            "%s", vm, sd
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


def _restore_empty_dc():
    """
    Remove the Data center, wiping all storage domains on it, re-create the
    data center with its cluster and host
    """
    dc_name = config.DATACENTER_ISCSI_CONNECTIONS
    cluster_name = config.CLUSTER_ISCSI_CONNECTIONS
    if not hl_dc.clean_datacenter(
        True, datacenter=dc_name, formatExpStorage='true', vdc=config.VDC,
        vdc_password=config.VDC_PASSWORD
    ):
        raise exceptions.DataCenterException(
            "Failed to clean Data center '%s'" % dc_name
        )
    if not ll_dc.addDataCenter(
        True, name=dc_name, version=config.COMP_VERSION
    ):
        raise exceptions.DataCenterException(
            "Failed to create Data center '%s'" % dc_name
        )
    if not ll_clusters.addCluster(
        True, name=cluster_name,  cpu=config.CPU_NAME, data_center=dc_name,
        version=config.COMP_VERSION
    ):
        raise exceptions.ClusterException(
            "Failed to create cluster '%s'" % cluster_name
        )
    if not ll_hosts.addHost(
        True, config.HOST_FOR_MOUNT, address=config.HOST_FOR_MOUNT_IP,
        wait=True, reboot=False, cluster=config.CLUSTER_ISCSI_CONNECTIONS,
        root_password=config.VDC_ROOT_PASSWORD
    ):
        raise exceptions.HostException(
            "Failed to add host '%s' into cluster '%s'" % (
                config.HOST_FOR_MOUNT, config.CLUSTER_ISCSI_CONNECTIONS
            )
        )


class TestCase(StorageTest):
    storages = set([config.STORAGE_TYPE_ISCSI])
    # Bugzilla history:
    # 1236718: RSDL incorrectly documents storageconnection parameter
    # set for iscsi (parameter is target not iqn)

    def get_all_new_connections(self):
        return _filter_storage_connections(
            self.original_conn,
            ll_storageconnections.get_all_storage_connections()
        )


@attr(tier=2)
class TestCase5243(TestCase):
    """
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_3_Storage_Manage_Storage_Connections
    """
    __test__ = config.STORAGE_TYPE_ISCSI in opts['storages']
    polarion_test_case = '5243'
    conn = None
    sd_name = None

    @polarion("RHEVM3-5243")
    @bz({'1275845': {}})
    def test_adding_storage_connections(self):
        """
        test adding a storage connection to a dc without storage domains
        and to a dc with a storage domain
        """
        logger.info(
            "Add a connection to the empty dc %s",
            config.DATACENTER_ISCSI_CONNECTIONS
        )
        conn = dict(config.CONNECTIONS[0]).copy()
        conn['type'] = config.STORAGE_TYPE_ISCSI
        self.conn, success = ll_storageconnections.add_connection(**conn)
        self.assertTrue(success, "Adding storage connection failed")

        ll_storageconnections.remove_storage_connection(self.conn.id)
        self.conn = None
        self.sd_name = 'sd_%s' % self.polarion_test_case
        self.assertTrue(
            ll_sd.addStorageDomain(
                True, host=config.HOST_FOR_MOUNT, name=self.sd_name,
                type=config.TYPE_DATA, storage_type=config.STORAGE_TYPE_ISCSI,
                override_luns=True, lun=config.CONNECTIONS[0]['luns'][0],
                **(config.CONNECTIONS[0])
            ), "Failed to create storage domain '%s'" % self.sd_name
        )
        old_conns_for_sd = ll_sd.getConnectionsForStorageDomain(self.sd_name)
        self.assertEqual(
            len(old_conns_for_sd), 1, "The connection count is not 1"
        )
        old_conn = old_conns_for_sd[0]

        logger.info(
            "Add the same connection to a data center with a storage domain "
            "- should fail"
        )
        self.conn, success = ll_storageconnections.add_connection(**conn)
        self.assertFalse(
            success, "Adding the same storage connection succeeded"
        )
        conns_for_sd = ll_sd.getConnectionsForStorageDomain(self.sd_name)
        self.assertEqual(
            len(conns_for_sd), 1, "The connection count is not 1"
        )
        new_conn = conns_for_sd[0]
        self.assertTrue(
            _compare_connections(old_conn, new_conn),
            "The connection count is different before adding the duplicate "
            "connection"
        )

    def tearDown(self):
        """
        Remove the storage domain and the storage connection
        """
        if self.sd_name:
            ll_sd.removeStorageDomain(
                True, self.sd_name, config.HOST_FOR_MOUNT, 'true'
            )
        if self.conn:
            ll_storageconnections.remove_storage_connection(self.conn.id)
        helpers.logout_from_all_iscsi_targets()


@attr(tier=2)
class TestCase5247(TestCase):
    """
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_3_Storage_Manage_Storage_Connections
    """
    __test__ = config.STORAGE_TYPE_ISCSI in opts['storages']
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
        self.conn, success = ll_storageconnections.add_connection(**conn)
        if not success:
            self.conn = None
        self.assertFalse(
            success, "Add storage connection was expected to fail"
        )

    def add_connection_with_empty_sth(self, param):
        conn = dict(config.CONNECTIONS[0]).copy()
        conn['type'] = config.STORAGE_TYPE_ISCSI
        conn[param] = ''
        self.conn, success = ll_storageconnections.add_connection(**conn)
        if not success:
            self.conn = None
        self.assertFalse(
            success, "Add storage connection was expected to fail"
        )

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
        old_conn = ll_storageconnections.StorageConnection
        ll_storageconnections.StorageConnection = (
            hl_datastructures.StorageConnection
        )
        try:
            self.add_connection_with_empty_sth('lun_port')
        finally:
            ll_storageconnections.StorageConnection = old_conn

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
        old_conn = ll_storageconnections.StorageConnection
        ll_storageconnections.StorageConnection = (
            hl_datastructures.StorageConnection
        )
        try:
            self.add_connection_without_sth('lun_port', 'aaa')
        finally:
            ll_storageconnections.StorageConnection = old_conn

    @polarion("RHEVM3-5247")
    def test_add_the_same_connection_twice(self):
        """ try to add an iscsi storage connection twice
            and add it after it was removed
        """
        conn = dict(config.CONNECTIONS[0]).copy()
        conn['type'] = config.STORAGE_TYPE_ISCSI
        self.conn, success = ll_storageconnections.add_connection(**conn)
        self.assertTrue(
            success, "Add storage connection was expected to succeed"
        )
        _, success = ll_storageconnections.add_connection(**conn)
        self.assertFalse(
            success, "Add storage connection was expected to fail"
        )
        self.assertTrue(
            ll_storageconnections.remove_storage_connection(self.conn.id),
            "Removing storage connection failed"
        )
        self.conn, success = ll_storageconnections.add_connection(**conn)
        self.assertTrue(
            success, "Add storage connection was expected to succeed"
        )

    def tearDown(self):
        """
        Remove the added storage connection
        """
        if self.conn:
            ll_storageconnections.remove_storage_connection(self.conn.id)


@attr(tier=2)
class TestCase5248(TestCase):
    """
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_3_Storage_Manage_Storage_Connections

    **Author**: Katarzyna Jachim
    """
    __test__ = config.STORAGE_TYPE_ISCSI in opts['storages']
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
        cls.conn_1, success = ll_storageconnections.add_connection(**conn)
        if not success:
            raise exceptions.StorageDomainException(
                "Adding storage connection failed"
            )

        conn = dict(config.CONNECTIONS[1]).copy()
        conn['type'] = config.STORAGE_TYPE_ISCSI
        cls.conn_2_params = conn
        cls.conn_2, success = ll_storageconnections.add_connection(**conn)
        if not success:
            raise exceptions.StorageDomainException(
                "Adding storage connection failed"
            )

    def change_connection_without_sth(self, conn, param):
        conn_params = {}
        conn_params[param] = ''
        conn_params['type'] = config.STORAGE_TYPE_ISCSI
        _, success = ll_storageconnections.update_connection(
            conn.id, **conn_params
        )
        self.assertFalse(
            success, "Update storage connection was expected to fail"
        )

    @polarion("RHEVM3-5248")
    def test_changing_storage_connection_without_ip(self):
        """ try to change an iscsi connection and set LUN address to nothing
        """
        self.change_connection_without_sth(self.conn_1, 'lun_address')

    @polarion("RHEVM3-5248")
    def test_changing_storage_connection_without_port(self):
        """ try to change an iscsi connection and set LUN port to nothing
        """
        old_conn = ll_storageconnections.StorageConnection
        ll_storageconnections.StorageConnection = (
            hl_datastructures.StorageConnection
        )
        try:
            self.change_connection_without_sth(self.conn_1, 'lun_port')
        finally:
            ll_storageconnections.StorageConnection = old_conn

    @polarion("RHEVM3-5248")
    def test_changing_storage_connection_without_target(self):
        """ try to change an iscsi connection and set LUN target to nothing
        """
        self.change_connection_without_sth(self.conn_1, 'lun_target')

    @polarion("RHEVM3-5248")
    def test_changing_storage_connection_to_existing_one(self):
        """ try to change an iscsi connection and set all values as in another
        """
        _, success = ll_storageconnections.update_connection(
            self.conn_1.id, **self.conn_2_params
        )
        self.assertFalse(
            success, "update storage connection was expected to fail"
        )

    @classmethod
    def teardown_class(cls):
        """
        Remove the storage connections
        """
        ll_storageconnections.remove_storage_connection(cls.conn_1.id)
        ll_storageconnections.remove_storage_connection(cls.conn_2.id)


@attr(tier=2)
class TestCase5246(TestCase):
    """
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_3_Storage_Manage_Storage_Connections

    **Author**: Katarzyna Jachim
    """
    __test__ = config.STORAGE_TYPE_ISCSI in opts['storages']
    polarion_test_case = '5246'
    sd_name_1 = "sd_%s_1" % polarion_test_case
    sd_name_2 = "sd_%s_2" % polarion_test_case
    master_sd = "master_%s" % polarion_test_case

    def setUp(self):
        """
        Add one storage domain and then another 2 storage domains that all use
        the same storage connection
        """
        if not ll_sd.addStorageDomain(
            True, host=config.HOST_FOR_MOUNT, name=self.master_sd,
            type=config.TYPE_DATA, storage_type=config.STORAGE_TYPE_NFS,
            address=config.UNUSED_DATA_DOMAIN_ADDRESSES[0],
            path=config.UNUSED_DATA_DOMAIN_PATHS[0]
        ):
            raise exceptions.StorageDomainException(
                "Failed to create storage domain '%s'" % self.master_sd
            )
        if not ll_sd.attachStorageDomain(
            True, config.DATACENTER_ISCSI_CONNECTIONS, self.master_sd
        ):
            raise exceptions.StorageDomainException(
                "Failed to attach storage domain '%s' into Data center '%s'" %
                (self.master_sd, config.DATACENTER_ISCSI_CONNECTIONS)
            )
        if not ll_sd.addStorageDomain(
            True, host=config.HOST_FOR_MOUNT, name=self.sd_name_1,
            type=config.TYPE_DATA, storage_type=config.STORAGE_TYPE_ISCSI,
            override_luns=True, lun=config.CONNECTIONS[0]['luns'][1],
            **(config.CONNECTIONS[0])
        ):
            raise exceptions.StorageDomainException(
                "Failed to create storage domain '%s'" % self.sd_name_1
            )
        if not ll_sd.attachStorageDomain(
            True, config.DATACENTER_ISCSI_CONNECTIONS, self.sd_name_1
        ):
            raise exceptions.StorageDomainException(
                "Failed to attach storage domain '%s' into Data center '%s'" %
                (self.sd_name_1, config.DATACENTER_ISCSI_CONNECTIONS)
            )
        if not ll_sd.addStorageDomain(
            True, host=config.HOST_FOR_MOUNT, name=self.sd_name_2,
            type=config.TYPE_DATA, storage_type=config.STORAGE_TYPE_ISCSI,
            override_luns=True, lun=config.CONNECTIONS[0]['luns'][2],
            **(config.CONNECTIONS[0])
        ):
            raise exceptions.StorageDomainException(
                "Failed to create storage domain '%s'" % self.sd_name_2
            )
        if not ll_sd.attachStorageDomain(
            True, config.DATACENTER_ISCSI_CONNECTIONS, self.sd_name_2
        ):
            raise exceptions.StorageDomainException(
                "Failed to attach storage domain '%s' into Data center '%s'" %
                (self.sd_name_2, config.DATACENTER_ISCSI_CONNECTIONS)
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
        conns = ll_sd.getConnectionsForStorageDomain(self.sd_name_1)
        conn_id = conns[0].id
        self.assertFalse(
            ll_storageconnections.remove_storage_connection(conn_id),
            "Removing storage connection succeeded"
        )

        test_utils.wait_for_tasks(
            config.VDC, config.VDC_PASSWORD,
            config.DATACENTER_ISCSI_CONNECTIONS
        )
        logger.info("Put the first domain into maintenance")
        self.assertTrue(
            ll_sd.deactivateStorageDomain(
                True, config.DATACENTER_ISCSI_CONNECTIONS, self.sd_name_1
            ), "Deactivating storage domain '%s' failed" % self.sd_name_1
        )
        logger.info("Try to remove the storage connection - should fail")
        self.assertFalse(
            ll_storageconnections.remove_storage_connection(conn_id),
            "Removing the storage connection was expected to fail"
        )

        logger.info("Detach the storage connection from the first domain")
        self.assertTrue(
            ll_sd.detachConnectionFromStorageDomain(self.sd_name_1, conn_id),
            "Detaching storage connection failed"
        )
        logger.info("Try to remove the storage connection - should fail")
        self.assertFalse(
            ll_storageconnections.remove_storage_connection(conn_id),
            "Removing the storage connection was expected to fail"
        )

        logger.info("Put the second storage domain into maintenance")
        test_utils.wait_for_tasks(
            config.VDC, config.VDC_PASSWORD,
            config.DATACENTER_ISCSI_CONNECTIONS
        )
        self.assertTrue(
            ll_sd.deactivateStorageDomain(
                True, config.DATACENTER_ISCSI_CONNECTIONS, self.sd_name_2
            ), "Deactivating storage domain '%s' failed" % self.sd_name_2
        )
        logger.info("Try to remove the storage connection - should fail")
        self.assertFalse(
            ll_storageconnections.remove_storage_connection(conn_id),
            "Removing the storage connection was expected to fail"
        )
        logger.info("Detach the storage connection from the second domain")
        self.assertTrue(
            ll_sd.detachConnectionFromStorageDomain(self.sd_name_2, conn_id),
            "Detaching connection from storage domain failed"
        )
        logger.info("Try to remove the storage connection - should succeed")
        self.assertTrue(
            ll_storageconnections.remove_storage_connection(conn_id),
            "Removing storage connection failed"
        )

    def tearDown(self):
        test_utils.wait_for_tasks(
            config.VDC, config.VDC_PASSWORD,
            config.DATACENTER_ISCSI_CONNECTIONS
        )
        if self.sd_name_1 is not None and self.sd_name_2 is not None:
            conn = dict(config.CONNECTIONS[0]).copy()
            conn['type'] = config.STORAGE_TYPE_ISCSI
            conn_1, success = ll_storageconnections.add_connection(**conn)
            if success:
                ll_sd.addConnectionToStorageDomain(self.sd_name_1, conn_1.id)
                ll_sd.addConnectionToStorageDomain(self.sd_name_2, conn_1.id)
        _restore_empty_dc()
        helpers.logout_from_all_iscsi_targets()


@attr(tier=2)
class TestCase5240(TestCase):
    """
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_3_Storage_Manage_Storage_Connections

    **Author**: Katarzyna Jachim
    """
    __test__ = config.STORAGE_TYPE_ISCSI in opts['storages']
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
            conn, success = ll_storageconnections.add_connection(**conn)
            if not success:
                raise exceptions.StorageDomainException(
                    "Adding storage connection failed"
                )
            cls.conns.append(conn)

    @polarion("RHEVM3-5240")
    def test_change_multiple_connections(self):
        """
        Test steps:
        * Try to switch 2 connections
        * Try to change 10 connections at once
        """
        logger.info("Trying to switch 2 connections")
        with ThreadPoolExecutor(max_workers=config.MAX_WORKERS) as executor:
            result_1 = executor.submit(
                ll_storageconnections.update_connection,
                self.conns[0].id, ** self.con_params[1]
            )
            result_2 = executor.submit(
                ll_storageconnections.update_connection,
                self.conns[1].id, ** self.con_params[0]
            )
        self.assertEqual(
            result_1.result()[1], result_2.result()[1],
            "Updating storage connections failed"
        )

        conn_1 = ll_storageconnections.get_storage_connection_object(
            self.conns[0].id, 'id'
        )
        conn_2 = ll_storageconnections.get_storage_connection_object(
            self.conns[1].id, 'id'
        )

        self.assertFalse(
            _compare_connections(conn_1, conn_2),
            "Connections were expected to be different"
        )

        logger.info("Trying to change 10 connections at once")
        results = []
        with ThreadPoolExecutor(max_workers=config.MAX_WORKERS) as executor:
            for conn in self.conns:
                results.append(
                    executor.submit(
                        ll_storageconnections.update_connection,
                        conn.id,
                        lun_target="aaa" + conn.target,
                        type=config.STORAGE_TYPE_ISCSI
                    )
                )
        for result in results:
            self.assertTrue(result.result(), "Connection failed")

    @classmethod
    def teardown_class(cls):
        for conn in cls.conns:
            ll_storageconnections.remove_storage_connection(conn.id)


@attr(tier=2)
class TestCase5242(TestCase):
    """
    Verify the GET call works for various storage connection/storage domains
    combinations
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_3_Storage_Manage_Storage_Connections

    **Author**: Katarzyna Jachim
    """
    __test__ = config.STORAGE_TYPE_ISCSI in opts['storages']
    polarion_test_case = '5242'

    def setUp(self):
        self.disks = []
        self.storage_domains = []
        self.storage_connections = []
        self.original_conn = (
            ll_storageconnections.get_all_storage_connections()
        )

    @polarion("RHEVM3-5242")
    def test_verify_one_orphaned_connection(self):
        """
        Verifying GET for one orphaned connection
        """
        logger.info("Verifying get for one orphaned connection")
        conn_1 = dict(config.CONNECTIONS[0]).copy()
        conn_1['type'] = config.STORAGE_TYPE_ISCSI
        self.conn, success = ll_storageconnections.add_connection(**conn_1)
        self.assertTrue(success, "Error adding storage connection %s" % conn_1)
        self.storage_connections.append(self.conn.id)
        new_conn = self.get_all_new_connections()
        self.assertEqual(
            len(new_conn), 1, "The number of new connections was expected to "
                              "be 1"
        )
        ll_storageconnections.remove_storage_connection(self.conn.id)
        self.storage_connections.remove(self.conn.id)

    @polarion("RHEVM3-5242")
    def test_verify_one_storage_domain(self):
        """
        Verifying GET for one storage domain
        """
        logger.info("Verifying get for one orphaned connection")
        sd_name = "sd_1_%s" % self.polarion_test_case
        self.assertTrue(
            ll_sd.addStorageDomain(
                True, host=config.HOST_FOR_MOUNT, name=sd_name,
                type=config.TYPE_DATA, storage_type=config.STORAGE_TYPE_ISCSI,
                override_luns=True, lun=config.CONNECTIONS[0]['luns'][0],
                **(config.CONNECTIONS[0])
            ), "Failed to create storage domain %s" % sd_name
        )
        self.storage_domains.append(sd_name)
        new_conn = self.get_all_new_connections()
        conn_for_sd = ll_sd.getConnectionsForStorageDomain(sd_name)
        self.assertEqual(
            len(new_conn), 1, "The number of storage connections was "
                              "expected to be 1"
        )
        self.assertEqual(
            len(conn_for_sd), 1, "The number of storage connections for the "
                                 "storage domain was expected to be 1"
        )
        self.assertTrue(
            _compare_connections(new_conn[0], conn_for_sd[0]),
            "The storage connection and the connection for the storage "
            "domain do not match"
        )
        self.assertTrue(
            ll_sd.removeStorageDomain(
                True, sd_name, config.HOST_FOR_MOUNT, 'true'
            ), "Failed to remove storage domain '%s'" % sd_name
        )
        self.storage_domains.remove(sd_name)
        new_conn = self.get_all_new_connections()
        self.assertEqual(
            len(new_conn), 0, "New connections was expected to be 0"
        )

    @polarion("RHEVM3-5242")
    def test_verify_storage_domain_with_two_connections(self):
        """
        Verifying GET for one storage domain using multiple
        storage connections
        """
        logger.info("Verifying get for one storage domain")
        sd_name = "sd_2_%s" % self.polarion_test_case
        self.assertTrue(
            ll_sd.addStorageDomain(
                True, host=config.HOST_FOR_MOUNT, name=sd_name,
                type=config.TYPE_DATA, storage_type=config.STORAGE_TYPE_ISCSI,
                override_luns=True, lun=config.CONNECTIONS[0]['luns'][0],
                **(config.CONNECTIONS[0])
            ), "Failed to create storage domain '%s'" % sd_name
        )
        self.storage_domains.append(sd_name)
        self.assertTrue(
            ll_sd.attachStorageDomain(
                True, config.DATACENTER_ISCSI_CONNECTIONS, sd_name
            ), "Failed to attach storage domain '%s'" % sd_name
        )
        self.storage_domains.remove(sd_name)
        self.assertTrue(
            ll_sd.waitForStorageDomainStatus(
                True, config.DATACENTER_ISCSI_CONNECTIONS, sd_name,
                config.SD_ACTIVE
            ), "Storage domain '%s' failed to become active" % sd_name
        )
        new_sd_connections = self.get_all_new_connections()
        logger.info(
            "The number of new connections created when storage domain '%s' "
            "was added is '%s'", sd_name, len(new_sd_connections)
        )
        hl_sd._ISCSIdiscoverAndLogin(
            config.HOST_FOR_MOUNT, config.CONNECTIONS[1]['lun_address'],
            config.CONNECTIONS[1]['lun_target']
        )
        self.assertTrue(
            ll_sd.extendStorageDomain(
                True, sd_name, storage_type=config.STORAGE_TYPE_ISCSI,
                host=config.HOST_FOR_MOUNT, override_luns=True,
                lun=config.CONNECTIONS[1]['luns'][1], **(config.CONNECTIONS[1])
            ), "Failed to extend storage domain '%s'" % sd_name
        )
        connections_for_sd = ll_sd.getConnectionsForStorageDomain(sd_name)
        extend_sd_connections = self.get_all_new_connections()
        logger.info(
            "The number of new connections is: '%s'",
            len(extend_sd_connections)
        )
        self.assertEqual(
            len(connections_for_sd), 2, "2 storage connection are expected "
                                        "for storage domain '%s'" % sd_name
        )
        self.assertEqual(
            len(extend_sd_connections), len(new_sd_connections) + 1,
            "1 additional connection was expected after extending storage "
            "domain '%s'" % sd_name
        )

    @polarion("RHEVM3-5242")
    def test_verify_two_storage_domains_with_the_same_connection(self):
        """
        Verifying get for a storage domain with 2 connections
        """
        logger.info("Verifying get for a storage domain with 2 connections")
        sd_name_1 = "sd_3_%s" % self.polarion_test_case
        ll_sd.addStorageDomain(
            True, host=config.HOST_FOR_MOUNT, name=sd_name_1,
            type=config.TYPE_DATA, storage_type=config.STORAGE_TYPE_ISCSI,
            override_luns=True, lun=config.CONNECTIONS[0]['luns'][0],
            **(config.CONNECTIONS[0])
        )
        self.storage_domains.append(sd_name_1)
        sd_name_2 = "sd_4_%s" % self.polarion_test_case
        ll_sd.addStorageDomain(
            True, host=config.HOST_FOR_MOUNT, name=sd_name_2,
            type=config.TYPE_DATA, storage_type=config.STORAGE_TYPE_ISCSI,
            override_luns=True, lun=config.CONNECTIONS[0]['luns'][1],
            **(config.CONNECTIONS[0])
        )
        self.storage_domains.append(sd_name_2)

        conn_sd_1 = ll_sd.getConnectionsForStorageDomain(sd_name_1)
        conn_sd_2 = ll_sd.getConnectionsForStorageDomain(sd_name_2)
        self.assertEqual(
            len(conn_sd_1), len(conn_sd_2),
            "The number of storage connections for storage domain '%s' and "
            "'%s' does not match" % (sd_name_1, sd_name_2)
        )
        self.assertTrue(
            _compare_connections(conn_sd_1[0], conn_sd_2[0]),
            "The connections for storage domains '%s' and '%s' do not match" %
            (sd_name_1, sd_name_2)
        )
        self.assertTrue(
            ll_sd.removeStorageDomain(
                True, sd_name_1, config.HOST_FOR_MOUNT, 'true'
            ), "Failed to remove storage domain '%s'" % sd_name_1
        )
        self.storage_domains.remove(sd_name_1)
        self.assertTrue(
            ll_sd.removeStorageDomain(
                True, sd_name_2, config.HOST_FOR_MOUNT, 'true'
            ), "Failed to remove storage domain '%s'" % sd_name_2
        )
        self.storage_domains.remove(sd_name_2)
        new_conn = self.get_all_new_connections()
        self.assertFalse(new_conn, "No new connections were expected")

    @polarion("RHEVM3-5242")
    def test_verify_one_direct_lun(self):
        """
        Verifying get for direct LUN
        """
        logger.info("Verifying get for direct LUN")
        alias = "disk_1_%s" % self.polarion_test_case
        ll_disks.addDisk(
            True, alias=alias, interface=config.DISK_INTERFACE_VIRTIO,
            format=config.DISK_FORMAT_COW, type_=config.STORAGE_TYPE_ISCSI,
            lun_id=config.CONNECTIONS[0]['luns'][0],
            lun_address=config.CONNECTIONS[0]['lun_address'],
            lun_target=config.CONNECTIONS[0]['lun_target']
        )

        self.disks.append(alias)
        new_conn = self.get_all_new_connections()
        self.assertEqual(
            len(new_conn), 1, "1 new storage connection was expected"
        )
        # TODO: When the API allows it, check the storage connection of
        # a direct lun, something like:
        # conn_disk = ll_disks.getConnectionsForDisk(alias)
        # self.assertTrue(_compare_connections(all_conn, conn_disk),"Text")
        # https://bugzilla.redhat.com/show_bug.cgi?id=1227322
        self.assertTrue(
            ll_disks.deleteDisk(True, alias),
            "Deleting disk '%s' failed" % alias
        )
        self.disks.remove(alias)

    def tearDown(self):
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
        _restore_empty_dc()
        helpers.logout_from_all_iscsi_targets()


@attr(tier=2)
class TestCase5245(TestCase):
    """
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_3_Storage_Manage_Storage_Connections

    **Author**: Katarzyna Jachim
    """
    __test__ = config.STORAGE_TYPE_ISCSI in opts['storages']
    polarion_test_case = '5245'
    conn = None
    sd_name_1 = "sd_%s_1" % polarion_test_case
    sd_name_2 = "sd_%s_2" % polarion_test_case

    def setUp(self):
        """
        Add and attach two storage domains
        """
        if not ll_sd.addStorageDomain(
            True, host=config.HOST_FOR_MOUNT, name=self.sd_name_1,
            type=config.TYPE_DATA, storage_type=config.STORAGE_TYPE_ISCSI,
            override_luns=True, lun=config.CONNECTIONS[0]['luns'][0],
            **(config.CONNECTIONS[0])
        ):
            raise exceptions.StorageDomainException(
                "Failed to create storage domain '%s'" % self.sd_name_1
            )
        if not ll_sd.addStorageDomain(
            True, host=config.HOST_FOR_MOUNT, name=self.sd_name_2,
            type=config.TYPE_DATA, storage_type=config.STORAGE_TYPE_ISCSI,
            override_luns=True, lun=config.CONNECTIONS[0]['luns'][1],
            **(config.CONNECTIONS[0])
        ):
            raise exceptions.StorageDomainException(
                "Failed to create storage domain '%s'" % self.sd_name_2
            )
        if not ll_sd.attachStorageDomain(
            True, config.DATACENTER_ISCSI_CONNECTIONS, self.sd_name_1
        ):
            raise exceptions.StorageDomainException(
                "Failed to attach storage domain '%s' into Data center '%s'" %
                (self.sd_name_1, config.DATACENTER_ISCSI_CONNECTIONS)
            )
        if not ll_sd.attachStorageDomain(
            True, config.DATACENTER_ISCSI_CONNECTIONS, self.sd_name_2
        ):
            raise exceptions.StorageDomainException(
                "Failed to attach storage domain '%s' into Data center '%s'" %
                (self.sd_name_1, config.DATACENTER_ISCSI_CONNECTIONS)
            )
        ll_sd.waitForStorageDomainStatus(
            True, config.DATACENTER_ISCSI_CONNECTIONS, self.sd_name_1,
            config.SD_ACTIVE
        )
        ll_sd.waitForStorageDomainStatus(
            True, config.DATACENTER_ISCSI_CONNECTIONS, self.sd_name_2,
            config.SD_ACTIVE
        )

    def _try_to_change_connection(self, conn_id, should_pass):
        """
        Try to update connection conn_id, should succeed if should_pass is True
        """
        for parameter in ['lun_address', 'lun_target', 'lun_port']:
            fail_action = 'Unable' if should_pass else 'Able'
            self.assertEqual(
                should_pass, ll_storageconnections.update_connection(
                    conn_id, type=config.STORAGE_TYPE_ISCSI,
                    **{parameter: config.CONNECTIONS[1][parameter]}
                )[1],
                "{0} to update the storage connection {1}".format(
                    fail_action, conn_id
                )
            )

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
        logger.info("Trying to change the connection - should fail")
        self._try_to_change_connection(conn.id, False)
        logger.info("Waiting for tasks before deactivating the storage domain")
        test_utils.wait_for_tasks(
            config.VDC, config.VDC_PASSWORD,
            config.DATACENTER_ISCSI_CONNECTIONS
        )

        logger.info("Deactivating one of the storage domains")
        self.assertTrue(
            ll_sd.deactivateStorageDomain(
                True, config.DATACENTER_ISCSI_CONNECTIONS, self.sd_name_2
            ), "Failed to deactivate storage domain '%s'" % self.sd_name_2
        )
        logger.info("Trying to change the connection - should fail")
        self._try_to_change_connection(conn.id, False)
        logger.info("Waiting for tasks before deactivating the storage domain")
        test_utils.wait_for_tasks(
            config.VDC, config.VDC_PASSWORD,
            config.DATACENTER_ISCSI_CONNECTIONS
        )

        logger.info("Deactivating both storage domains")
        self.assertTrue(
            ll_sd.deactivateStorageDomain(
                True, config.DATACENTER_ISCSI_CONNECTIONS, self.sd_name_1
            ), "Failed to deactivate storage domain '%s'" % self.sd_name_1
        )
        logger.info("Trying to change the connection - should succeed")
        self._try_to_change_connection(conn.id, True)
        self.assertTrue(
            ll_sd.activateStorageDomain(
                True, config.DATACENTER_ISCSI_CONNECTIONS, self.sd_name_1
            ), "Failed to activate storage domain '%s'" % self.sd_name_1
        )
        self.assertTrue(
            ll_sd.activateStorageDomain(
                True, config.DATACENTER_ISCSI_CONNECTIONS, self.sd_name_2
            ), "Failed to activate storage domain '%s'" % self.sd_name_2
        )

    def tearDown(self):
        """
        Remove added storage domains
        """
        _restore_empty_dc()
        helpers.logout_from_all_iscsi_targets()


@attr(tier=2)
class TestCase5244(TestCase):
    """
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_3_Storage_Manage_Storage_Connections
    """
    __test__ = config.STORAGE_TYPE_ISCSI in opts['storages']
    polarion_test_case = '5244'
    conn = None
    sd_name_1 = "sd_%s_1" % polarion_test_case
    sd_name_2 = "sd_%s_2" % polarion_test_case

    def setUp(self):
        """
        Add two storage domains sharing the same storage connection
        Add a new storage connection
        """
        if not ll_sd.addStorageDomain(
            True, host=config.HOST_FOR_MOUNT, name=self.sd_name_1,
            type=config.TYPE_DATA, storage_type=config.STORAGE_TYPE_ISCSI,
            override_luns=True, lun=config.CONNECTIONS[0]['luns'][0],
            **(config.CONNECTIONS[0])
        ):
            raise exceptions.StorageDomainException(
                "Failed to create storage domain '%s'" % self.sd_name_1
            )
        if not ll_sd.addStorageDomain(
            True, host=config.HOST_FOR_MOUNT, name=self.sd_name_2,
            type=config.TYPE_DATA, storage_type=config.STORAGE_TYPE_ISCSI,
            override_luns=True, lun=config.CONNECTIONS[0]['luns'][1],
            **(config.CONNECTIONS[0])
        ):
            raise exceptions.StorageDomainException(
                "Failed to create storage domain '%s'" % self.sd_name_2
            )
        if not ll_sd.attachStorageDomain(
            True, config.DATACENTER_ISCSI_CONNECTIONS, self.sd_name_1
        ):
            raise exceptions.StorageDomainException(
                "Failed to attach storage domain '%s' into Data center '%s'" %
                (self.sd_name_1, config.DATACENTER_ISCSI_CONNECTIONS)
            )
        if not ll_sd.attachStorageDomain(
            True, config.DATACENTER_ISCSI_CONNECTIONS, self.sd_name_2
        ):
            raise exceptions.StorageDomainException(
                "Failed to attach storage domain '%s' into Data center '%s'" %
                (self.sd_name_2, config.DATACENTER_ISCSI_CONNECTIONS)
            )
        if not ll_sd.waitForStorageDomainStatus(
            True, config.DATACENTER_ISCSI_CONNECTIONS, self.sd_name_1,
            config.SD_ACTIVE
        ):
            raise exceptions.StorageDomainException(
                "Storage domain '%s' did not reach OK status" % self.sd_name_1
            )
        if not ll_sd.waitForStorageDomainStatus(
            True, config.DATACENTER_ISCSI_CONNECTIONS, self.sd_name_2,
            config.SD_ACTIVE
        ):
            raise exceptions.StorageDomainException(
                "Storage domain '%s' did not reach OK status" % self.sd_name_2
            )
        conn = dict(config.CONNECTIONS[1]).copy()
        conn['type'] = config.STORAGE_TYPE_ISCSI
        self.conn, success = ll_storageconnections.add_connection(**conn)
        if not success:
            raise exceptions.StorageDomainException(
                "Failed to add storage connection '%s'" % conn
            )

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
        self.assertFalse(
            ll_sd.addConnectionToStorageDomain(
                self.sd_name_1, self.conn.id
            ), "Added storage connection to active domain '%s'" %
               self.sd_name_1
        )
        logger.info("Waiting for tasks before deactivating the storage domain")
        test_utils.wait_for_tasks(
            config.VDC, config.VDC_PASSWORD,
            config.DATACENTER_ISCSI_CONNECTIONS
        )
        self.assertTrue(
            ll_sd.deactivateStorageDomain(
                True, config.DATACENTER_ISCSI_CONNECTIONS, self.sd_name_1
            ), "Failed to deactivate storage domain '%s'" % self.sd_name_1
        )
        self.assertTrue(
            ll_sd.addConnectionToStorageDomain(self.sd_name_1, self.conn.id),
            "Failed to add storage connection to domain '%s'" % self.sd_name_1
        )
        self.assertTrue(
            ll_sd.activateStorageDomain(
                True, config.DATACENTER_ISCSI_CONNECTIONS, self.sd_name_1
            ), "Failed to activate storage domain '%s'" % self.sd_name_1
        )
        logger.info("Waiting for tasks before deactivating the storage domain")
        test_utils.wait_for_tasks(
            config.VDC, config.VDC_PASSWORD,
            config.DATACENTER_ISCSI_CONNECTIONS
        )
        self.assertTrue(
            ll_sd.deactivateStorageDomain(
                True, config.DATACENTER_ISCSI_CONNECTIONS, self.sd_name_2
            ), "Failed to deactivate storage domain '%s'" % self.sd_name_2
        )
        self.assertTrue(
            ll_sd.addConnectionToStorageDomain(self.sd_name_2, self.conn.id),
            "Failed to add storage connection to domain '%s'" % self.sd_name_2
        )
        self.assertFalse(
            ll_sd.addConnectionToStorageDomain(self.sd_name_2, self.conn.id),
            "Succeeded to add a duplicate connection to storage domain '%s'" %
            self.sd_name_2
        )
        self.assertTrue(
            ll_sd.activateStorageDomain(
                True, config.DATACENTER_ISCSI_CONNECTIONS, self.sd_name_2
            ), "Failed to activate storage domain '%s'" % self.sd_name_2
        )

    def tearDown(self):
        _restore_empty_dc()
        helpers.logout_from_all_iscsi_targets()


@attr(tier=2)
class TestCase5241(TestCase):
    """
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_3_Storage_Manage_Storage_Connections
    """
    __test__ = config.STORAGE_TYPE_ISCSI in opts['storages']
    polarion_test_case = '5241'
    conn = None
    vm_name_1 = "vm_%s_1" % polarion_test_case
    vm_name_2 = "vm_%s_2" % polarion_test_case
    disk_1 = "disk_%s_1" % polarion_test_case
    sd_name = "sd_%s" % polarion_test_case
    disk_2 = "disk_%s_2" % polarion_test_case

    def setUp(self):
        if not ll_sd.addStorageDomain(
            True, host=config.HOST_FOR_MOUNT, name=self.sd_name,
            type=config.TYPE_DATA, storage_type=config.STORAGE_TYPE_NFS,
            address=config.UNUSED_DATA_DOMAIN_ADDRESSES[0],
            path=config.UNUSED_DATA_DOMAIN_PATHS[0]
        ):
            raise exceptions.StorageDomainException(
                "Failed to create storage domain '%s'" % self.sd_name
            )
        if not ll_sd.attachStorageDomain(
            True, config.DATACENTER_ISCSI_CONNECTIONS, self.sd_name
        ):
            raise exceptions.StorageDomainException(
                "Failed to attach storage domain '%s' into Data center '%s'" %
                (self.sd_name, config.DATACENTER_ISCSI_CONNECTIONS)
            )
        ll_sd.waitForStorageDomainStatus(
            True, config.DATACENTER_ISCSI_CONNECTIONS, self.sd_name,
            config.SD_ACTIVE
        )
        for vm_name in (self.vm_name_1, self.vm_name_2):
            vm_args_copy = config.create_vm_args.copy()
            vm_args_copy['cluster'] = config.CLUSTER_ISCSI_CONNECTIONS
            vm_args_copy['installation'] = False
            vm_args_copy['provisioned_size'] = config.GB
            vm_args_copy['storageDomainName'] = self.sd_name
            vm_args_copy['vmName'] = vm_name
            vm_args_copy['vmDescription'] = vm_name
            if not storage_helpers.create_vm_or_clone(**vm_args_copy):
                raise errors.VMException(
                    'Unable to create vm %s for test' % vm_name
                )
            logger.info('Shutting down VM %s', vm_name)
            ll_vms.stop_vms_safely([vm_name])

        if not ll_disks.addDisk(
            True, alias=self.disk_1,
            interface=config.VIRTIO,
            format=config.DISK_FORMAT_COW,
            lun_id=config.CONNECTIONS[0]['luns'][1],
            lun_address=config.CONNECTIONS[0]['lun_address'],
            lun_target=config.CONNECTIONS[0]['lun_target'],
            type_=config.STORAGE_TYPE_ISCSI
        ):
            raise exceptions.DiskException(
                "Failed to create disk '%s'" % self.disk_1
            )
        if not ll_disks.addDisk(
            True, alias=self.disk_2,
            interface=config.VIRTIO,
            format=config.DISK_FORMAT_COW,
            lun_id=config.CONNECTIONS[0]['luns'][2],
            lun_address=config.CONNECTIONS[0]['lun_address'],
            lun_target=config.CONNECTIONS[0]['lun_target'],
            type_=config.STORAGE_TYPE_ISCSI
        ):
            raise exceptions.DiskException(
                "Failed to create disk '%s'" % self.disk_2
            )
        if not ll_disks.attachDisk(True, self.disk_1, self.vm_name_1):
            raise exceptions.DiskException(
                "Failed to attach disk '%s' to VM '%s'" % (
                    self.disk_1, self.vm_name_1
                )
            )
        if not ll_disks.attachDisk(True, self.disk_2, self.vm_name_2):
            raise exceptions.DiskException(
                "Failed to attach disk '%s' to VM '%s'" % (
                    self.disk_2, self.vm_name_2
                )
            )
        if not ll_vms.startVms([self.vm_name_1, self.vm_name_2], config.VM_UP):
            raise exceptions.VMException(
                "Failed to power on vms %s" %
                ', '.join([self.vm_name_1, self.vm_name_2])
            )

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

        self.assertTrue(
            lun_conn,
            "The connection target does not match the configured target"
        )

        self.assertFalse(
            ll_storageconnections.update_connection(
                lun_conn.id, lun_address=config.CONNECTIONS[1]['lun_address'],
                type=config.STORAGE_TYPE_ISCSI
            )[1], "Succeeded to update connection in use"
        )

        self.assertTrue(
            ll_vms.stopVm(True, self.vm_name_1),
            "Failed to power off VM '%s'" % self.vm_name_1
        )
        self.assertTrue(
            ll_vms.waitForVMState(
                self.vm_name_1, config.VM_DOWN
            ), "VM '%s' failed to reach powered off state" % self.vm_name_1
        )

        self.assertFalse(
            ll_storageconnections.update_connection(
                lun_conn.id, lun_address=config.CONNECTIONS[1]['lun_address'],
                type=config.STORAGE_TYPE_ISCSI
            )[1], "Succeeded to update a connection that is in use"
        )

        self.assertTrue(
            ll_vms.stopVm(True, self.vm_name_2),
            "Failed to power off VM '%s'" % self.vm_name_2
        )
        self.assertTrue(
            ll_vms.waitForVMState(
                self.vm_name_2, config.VM_DOWN
            ), "VM '%s' failed to reach powered off state" % self.vm_name_2
        )

        self.assertTrue(
            ll_storageconnections.update_connection(
                lun_conn.id, type=config.STORAGE_TYPE_ISCSI,
                **(config.CONNECTIONS[1])
            )[1], "Failed to update storage connection"
        )

        self.assertTrue(
            ll_vms.startVm(True, self.vm_name_1),
            "Failed to power on VM '%s'" % self.vm_name_1
        )
        self.assertTrue(
            ll_vms.startVm(True, self.vm_name_2),
            "Failed to power on VM '%s'" % self.vm_name_2
        )

    def tearDown(self):
        """
        Remove vms and added storage domains
        """
        if not ll_vms.safely_remove_vms([self.vm_name_1, self.vm_name_2]):
            logger.error(
                "Failed to power off and remove vms %s",
                ', '.join([self.vm_name_1, self.vm_name_2])
            )
            TestCase.test_failed = True
        _restore_empty_dc()
        helpers.logout_from_all_iscsi_targets()
        TestCase.teardown_exception()


@attr(tier=2)
class TestCase5249(TestCase):
    """
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_3_Storage_Manage_Storage_Connections
    """
    __test__ = config.STORAGE_TYPE_ISCSI in opts['storages']
    polarion_test_case = '5249'
    conn = None

    def setUp(self):
        self.storage_domains = []
        conn = dict(config.CONNECTIONS[0]).copy()
        conn['type'] = config.STORAGE_TYPE_ISCSI
        self.conn, success = ll_storageconnections.add_connection(**conn)
        if not success:
            raise exceptions.StorageDomainException(
                "Failed to add storage connection '%s'" % conn
            )
        self.original_conn = (
            ll_storageconnections.get_all_storage_connections()
        )

    @polarion("RHEVM3-5249")
    def test_adding_storage_domains(self):
        """
        Test steps:
        * a storage domain using a new connection (old flow)
        * a storage domain with all params specified (old flow), but
          the connection params are the same of an existing connection
          In the last case, new connection should not be added.
        """
        logger.info("Adding a new storage domain with a new connection")
        sd_name_2 = "sd_%s_2" % self.polarion_test_case

        self.assertTrue(
            ll_sd.addStorageDomain(
                True, name=sd_name_2, host=config.HOST_FOR_MOUNT,
                type=config.TYPE_DATA,
                storage_type=config.STORAGE_TYPE_ISCSI,
                override_luns=True, lun=config.CONNECTIONS[1]['luns'][0],
                **(config.CONNECTIONS[1])
            ), "Failed to create storage domain '%s'" % sd_name_2
        )
        self.storage_domains.append(sd_name_2)

        sd_name_2_conn = ll_sd.getConnectionsForStorageDomain(sd_name_2)
        logger.info(
            "Connection of storage domain %s is: %s",
            sd_name_2, sd_name_2_conn[0].id
        )
        self.assertEqual(
            len(sd_name_2_conn), 1,
            "The expected number of storage connections was 1"
        )
        self.assertTrue(
            ll_sd.removeStorageDomain(
                True, sd_name_2, config.HOST_FOR_MOUNT, 'true'
            ), "Failed to remove storage domain '%s'" % sd_name_2
        )
        self.storage_domains.remove(sd_name_2)

        logger.info(
            "Adding a new domain specifying the parameters but using the "
            "existing connection"
        )
        sd_name_3 = "sd_%s_3" % self.polarion_test_case
        self.assertTrue(
            ll_sd.addStorageDomain(
                True, name=sd_name_3, host=config.HOST_FOR_MOUNT,
                type=config.TYPE_DATA,
                storage_type=config.STORAGE_TYPE_ISCSI,
                override_luns=True, lun=config.CONNECTIONS[0]['luns'][1],
                **(config.CONNECTIONS[0])
            ), "Failed to create storage domain '%s'" % sd_name_3
        )
        sd_name_3_conn = ll_sd.getConnectionsForStorageDomain(sd_name_3)
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
            ll_sd.removeStorageDomain(
                True, storage_domain, config.HOST_FOR_MOUNT, 'true'
            )
        if self.conn.id in [
            connection.id for connection in
            ll_storageconnections.get_all_storage_connections()
        ]:
            ll_storageconnections.remove_storage_connection(self.conn.id)
        helpers.logout_from_all_iscsi_targets()
