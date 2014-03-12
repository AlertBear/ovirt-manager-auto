from art.unittest_lib import BaseTestCase as TestCase
import logging
from concurrent.futures import ThreadPoolExecutor
import time

from art.test_handler.tools import tcms, bz

from art.rhevm_api.utils import test_utils
from art.rhevm_api.tests_lib.low_level import storagedomains
from art.rhevm_api.tests_lib.low_level import storageconnections
from art.rhevm_api.tests_lib.low_level import disks
from art.rhevm_api.tests_lib.low_level import hosts
from art.rhevm_api.tests_lib.low_level import vms
from art.rhevm_api.tests_lib.low_level import clusters
from art.rhevm_api.tests_lib.low_level import datacenters as ll_dc
from art.rhevm_api.tests_lib.high_level import storagedomains as hl_sd
from art.rhevm_api.tests_lib.high_level import datacenters
from art.rhevm_api.tests_lib.high_level import datastructures

import config

LOGGER = logging.getLogger(__name__)

api = test_utils.get_api('storage_connection', 'storageconnections')
sd_api = test_utils.get_api('storage_domain', 'storagedomains')
dc_api = test_utils.get_api('data_center', 'datacenters')

GB = 1024 ** 3


def _compare_connections(conn_1, conn_2):
    return conn_1.__dict__ == conn_2.__dict__


def _restore_empty_dc():
    found_master, master_sd = storagedomains.findMasterStorageDomain(
        True, config.DATA_CENTER_NAME)
    if found_master:
        non_master_sds = storagedomains.findNonMasterStorageDomains(
            True, config.DATA_CENTER_NAME)[1]['nonMasterDomains']
        if non_master_sds:
            for sd in non_master_sds:
                hl_sd.detach_and_deactivate_domain(config.DATA_CENTER_NAME, sd)
        master_sd = master_sd['masterDomain']
        test_utils.wait_for_tasks(
            vdc=config.VDC, vdc_password=config.VDC_PASSWORD,
            datacenter=config.DATA_CENTER_NAME)
        assert storagedomains.deactivateStorageDomain(
            True, config.DATA_CENTER_NAME, master_sd)
        dcObj = dc_api.find(config.DATA_CENTER_NAME)
        cluster = dc_api.getElemFromLink(
            dcObj, link_name='clusters', attr='cluster',
            get_href=False)[0].name
        assert ll_dc.removeDataCenter(True, config.DATA_CENTER_NAME)
        assert storagedomains.removeStorageDomain(
            True, master_sd, config.HOSTS[0])
        assert ll_dc.addDataCenter(
            True, storage_type=config.DATA_CENTER_TYPE,
            name=config.DATA_CENTER_NAME,
            version=config.PARAMETERS['compatibility_version'])
        assert hosts.deactivateHost(True, config.HOSTS[0])
        assert clusters.connectClusterToDataCenter(
            True, cluster, config.DATA_CENTER_NAME)
        assert hosts.activateHost(True, config.HOSTS[0])
        assert hosts.waitForHostsStates(True, config.HOSTS[0])
    unattached_sds = sd_api.get(absLink=False)
    for sd in unattached_sds:
        assert storagedomains.removeStorageDomain(
            True, sd.name, config.HOSTS[0])
    assert storageconnections.remove_all_storage_connections()


class TestCase288967(TestCase):
    """
    https://tcms.engineering.redhat.com/case/288967/?from_plan=9985

    **Author**: Katarzyna Jachim
    """
    __test__ = True
    tcms_plan_id = '9985'
    tcms_test_case = '288967'
    conn = None
    sd_name = None

    @tcms(tcms_plan_id, tcms_test_case)
    def test_adding_storage_connections(self):
        """ test adding a storage connection to a dc without storage domains
            and to a dc with a storage domain
        """
        # add a connection to an empty dc
        conn = dict(config.CONNECTIONS[0])
        conn['type'] = config.DATA_CENTER_TYPE
        self.conn, success = storageconnections.add_connection(**conn)
        assert success

        storageconnections.remove_storage_connection(self.conn.id)
        self.conn = None
        self.sd_name = 'sd_%s' % self.tcms_test_case
        storagedomains.addStorageDomain(
            True, host=config.HOSTS[0], name=self.sd_name,
            type=config.ENUMS['storage_dom_type_data'],
            storage_type=config.DATA_CENTER_TYPE,
            lun=config.CONNECTIONS[1]['luns'][0], **(config.CONNECTIONS[1]))
        old_conns_for_sd = storagedomains.getConnectionsForStorageDomain(
            self.sd_name)
        assert len(old_conns_for_sd) == 1
        old_conn = old_conns_for_sd[0]

        # add the same connection to a dc with a storage domain
        self.conn, success = storageconnections.add_connection(**conn)
        assert success
        conns_for_sd = storagedomains.getConnectionsForStorageDomain(
            self.sd_name)
        assert len(conns_for_sd) == 1
        new_conn = conns_for_sd[0]
        assert _compare_connections(old_conn, new_conn)

    def tearDown(self):
        _restore_empty_dc()


class TestCase288985(TestCase):
    """
    https://tcms.engineering.redhat.com/case/288985/?from_plan=9985

    **Author**: Katarzyna Jachim
    """
    __test__ = True
    tcms_plan_id = '9985'
    tcms_test_case = '288985'
    conn = None
    sd_name = None

    def add_connection_without_sth(self, param, value=None):
        conn = dict(config.CONNECTIONS[0])
        conn['type'] = config.DATA_CENTER_TYPE
        conn[param] = value
        self.conn, success = storageconnections.add_connection(**conn)
        if not success:
            self.conn = None
        assert (not success)

    def add_connection_with_empty_sth(self, param):
        conn = dict(config.CONNECTIONS[0])
        conn['type'] = config.DATA_CENTER_TYPE
        conn[param] = ''
        self.conn, success = storageconnections.add_connection(**conn)
        if not success:
            self.conn = None
        assert (not success)

    @tcms(tcms_plan_id, tcms_test_case)
    def test_adding_storage_connection_without_ip(self):
        """ try to add an iscsi storage connection without LUN address
        """
        self.add_connection_without_sth('lun_address')
        self.add_connection_with_empty_sth('lun_address')

    @tcms(tcms_plan_id, tcms_test_case)
    @bz(1006449)
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

    @tcms(tcms_plan_id, tcms_test_case)
    def test_adding_storage_connection_without_target(self):
        """ try to add an iscsi storage connection without LUN target
        """
        self.add_connection_without_sth('lun_target')
        self.add_connection_with_empty_sth('lun_target')

    @tcms(tcms_plan_id, tcms_test_case)
    def test_adding_storage_connection_with_string_as_port(self):
        """ try to add an iscsi storage connection with a string as a port
        """
        old_conn = storageconnections.StorageConnection
        storageconnections.StorageConnection = datastructures.StorageConnection
        try:
            self.add_connection_without_sth('lun_port', 'aaa')
        finally:
            storageconnections.StorageConnection = old_conn

    @tcms(tcms_plan_id, tcms_test_case)
    def test_add_the_same_connection_twice(self):
        """ try to add an iscsi storage connection twice
            and add it after it was removed
        """
        conn = dict(config.CONNECTIONS[0])
        conn['type'] = config.DATA_CENTER_TYPE
        self.conn, success = storageconnections.add_connection(**conn)
        assert success
        _, success = storageconnections.add_connection(**conn)
        assert (not success)
        assert storageconnections.remove_storage_connection(self.conn.id)
        self.conn, success = storageconnections.add_connection(**conn)
        assert success

    def tearDown(self):
        storageconnections.remove_all_storage_connections()


class TestCase288986(TestCase):
    """
    https://tcms.engineering.redhat.com/case/288986/?from_plan=9985

    **Author**: Katarzyna Jachim
    """
    __test__ = True
    tcms_plan_id = '9985'
    tcms_test_case = '288986'
    conn_1 = None
    conn_2 = None
    sd_name = None

    @classmethod
    def setup_class(cls):
        conn = dict(config.CONNECTIONS[0])
        conn['type'] = config.DATA_CENTER_TYPE
        cls.conn_1, success = storageconnections.add_connection(**conn)
        assert success

        conn = dict(config.CONNECTIONS[1])
        conn['type'] = config.DATA_CENTER_TYPE
        cls.conn_2_params = conn
        cls.conn_2, success = storageconnections.add_connection(**conn)
        assert success

    def change_connection_without_sth(self, conn, param):
        conn_params = {}
        conn_params[param] = ''
        conn_params['type'] = config.DATA_CENTER_TYPE
        _, success = storageconnections.update_connection(
            conn.id, **conn_params)
        assert (not success)

    @tcms(tcms_plan_id, tcms_test_case)
    def test_changing_storage_connection_without_ip(self):
        """ try to change an iscsi connection and set LUN address to nothing
        """
        self.change_connection_without_sth(self.conn_1, 'lun_address')

    @tcms(tcms_plan_id, tcms_test_case)
    @bz(1006449)
    def test_changing_storage_connection_without_port(self):
        """ try to change an iscsi connection and set LUN port to nothing
        """
        old_conn = storageconnections.StorageConnection
        storageconnections.StorageConnection = datastructures.StorageConnection
        try:
            self.change_connection_without_sth(self.conn_1, 'lun_port')
        finally:
            storageconnections.StorageConnection = old_conn

    @tcms(tcms_plan_id, tcms_test_case)
    @bz(1005284)
    def test_changing_storage_connection_without_target(self):
        """ try to change an iscsi connection and set LUN target to nothing
        """
        self.change_connection_without_sth(self.conn_1, 'lun_target')

    @tcms(tcms_plan_id, tcms_test_case)
    def test_changing_storage_connection_to_existing_one(self):
        """ try to change an iscsi connection and set all values as in another
        """
        _, success = storageconnections.update_connection(
            self.conn_1.id, **self.conn_2_params)
        assert not success

    @classmethod
    def teardown_class(cls):
        _restore_empty_dc()


class TestCase288983(TestCase):
    """
    https://tcms.engineering.redhat.com/case/288983/?from_plan=9985

    **Author**: Katarzyna Jachim
    """
    __test__ = True
    tcms_plan_id = '9985'
    tcms_test_case = '288983'
    sd_name_1 = "sd_%s_1" % tcms_test_case
    sd_name_2 = "sd_%s_2" % tcms_test_case
    master_sd = "master_%s" % tcms_test_case

    def setUp(self):
        assert storagedomains.addStorageDomain(
            True, host=config.HOSTS[0], name=self.master_sd,
            type=config.ENUMS['storage_dom_type_data'],
            storage_type=config.DATA_CENTER_TYPE,
            lun=config.CONNECTIONS[1]['luns'][0], **(config.CONNECTIONS[1]))

        assert storagedomains.attachStorageDomain(
            True, config.DATA_CENTER_NAME, self.master_sd)

        assert storagedomains.addStorageDomain(
            True, host=config.HOSTS[0], name=self.sd_name_1,
            type=config.ENUMS['storage_dom_type_data'],
            storage_type=config.DATA_CENTER_TYPE,
            lun=config.CONNECTIONS[0]['luns'][0], **(config.CONNECTIONS[0]))

        assert storagedomains.attachStorageDomain(
            True, config.DATA_CENTER_NAME, self.sd_name_1)

        assert storagedomains.addStorageDomain(
            True, host=config.HOSTS[0], name=self.sd_name_2,
            type=config.ENUMS['storage_dom_type_data'],
            storage_type=config.DATA_CENTER_TYPE,
            lun=config.CONNECTIONS[0]['luns'][1], **(config.CONNECTIONS[0]))

        assert storagedomains.attachStorageDomain(
            True, config.DATA_CENTER_NAME, self.sd_name_2)

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
        conns = storagedomains.getConnectionsForStorageDomain(self.sd_name_1)
        conn_id = conns[0].id
        host = config.HOSTS[0]
        assert not storageconnections.remove_storage_connection(conn_id, host)
        assert storagedomains.deactivateStorageDomain(
            True, config.DATA_CENTER_NAME, self.sd_name_1)
        assert not storageconnections.remove_storage_connection(conn_id, host)
        assert storagedomains.detachConnectionFromStorageDomain(
            self.sd_name_1, conn_id)
        assert not storageconnections.remove_storage_connection(conn_id, host)
        assert storagedomains.deactivateStorageDomain(
            True, config.DATA_CENTER_NAME, self.sd_name_2)
        assert not storageconnections.remove_storage_connection(conn_id, host)
        assert storagedomains.detachConnectionFromStorageDomain(
            self.sd_name_2, conn_id)
        assert storageconnections.remove_storage_connection(conn_id, host)

    def tearDown(self):
        # try to clean it as clearly as possible
        if self.sd_name_1 is not None and self.sd_name_2 is not None:
            conn = dict(config.CONNECTIONS[0])
            conn['type'] = config.DATA_CENTER_TYPE
            conn_1, _ = storageconnections.add_connection(**conn)
            storagedomains.addConnectionToStorageDomain(
                self.sd_name_1, conn_1.id)
            storagedomains.addConnectionToStorageDomain(
                self.sd_name_2, conn_1.id)
        _restore_empty_dc()


class TestCase295262(TestCase):
    """
    https://tcms.engineering.redhat.com/case/295262/?from_plan=9985

    **Author**: Katarzyna Jachim
    """
    __test__ = True
    tcms_plan_id = '9985'
    tcms_test_case = '295262'
    conns = []
    no_of_conn = 10
    con_params = []

    @classmethod
    def setup_class(cls):
        # put sth random to iqn, we are not going to use the connection anyhow
        for i in range(cls.no_of_conn):
            conn = dict(config.CONNECTIONS[0])
            conn['lun_target'] = 'sth%d.%s' % (i, conn['lun_target'])
            conn['type'] = config.DATA_CENTER_TYPE
            cls.con_params.append(conn)
            conn, success = storageconnections.add_connection(**conn)
            assert success
            cls.conns.append(conn)

    @tcms(tcms_plan_id, tcms_test_case)
    def test_change_multiple_connections(self):
        """
            Test steps:
            * try to switch 2 connections
            * try to change 10 connections at once
        """
        LOGGER.info("Trying to switch 2 connections")
        with ThreadPoolExecutor(max_workers=config.MAX_WORKERS) as executor:
            result_1 = executor.submit(
                storageconnections.update_connection,
                self.conns[0].id, ** self.con_params[1])
            result_2 = executor.submit(
                storageconnections.update_connection,
                self.conns[1].id, ** self.con_params[0])
        assert result_1.result()[1] == result_2.result()[1]

        conn_1 = api.find(self.conns[0].id, 'id')
        conn_2 = api.find(self.conns[1].id, 'id')

        assert not _compare_connections(conn_1, conn_2)

        LOGGER.info("Trying to change 10 connections at once")
        results = []
        with ThreadPoolExecutor(max_workers=config.MAX_WORKERS) as executor:
            for conn in self.conns:
                results.append(
                    executor.submit(
                        storageconnections.update_connection,
                        conn.id,
                        lun_target="aaa" + conn.target,
                        type=config.DATA_CENTER_TYPE))
        for result in results:
            assert result.result()

    @classmethod
    def teardown_class(cls):
        _restore_empty_dc()


def _get_all_connections():
    return api.get(absLink=False)


def _add_disk(conn_params, alias):
    return disks.addDisk(
        True, alias=alias, interface=config.ENUMS["interface_virtio"],
        format=config.ENUMS["format_cow"],
        type_=config.ENUMS['storage_type_iscsi'],
        lun_id=conn_params['luns'][0],
        lun_address=conn_params['lun_address'],
        lun_target=conn_params['lun_target'])


class TestCase288963(TestCase):
    """
    https://tcms.engineering.redhat.com/case/288963/?from_plan=9985

    **Author**: Katarzyna Jachim
    """
    __test__ = True
    tcms_plan_id = '9985'
    tcms_test_case = '288963'
    disks = []

    def verify_one_orphaned_connection(self):
        conn_1 = dict(config.CONNECTIONS[0])
        conn_1['type'] = config.DATA_CENTER_TYPE
        storageconnections.add_connection(**conn_1)
        assert len(_get_all_connections()) == 1
        storageconnections.remove_all_storage_connections()

    def verify_one_storage_domain(self):
        sd_name = "sd_1_%s" % self.tcms_test_case
        storagedomains.addStorageDomain(
            True, host=config.HOSTS[0], name=sd_name,
            type=config.ENUMS['storage_dom_type_data'],
            storage_type=config.DATA_CENTER_TYPE,
            lun=config.CONNECTIONS[0]['luns'][0], **(config.CONNECTIONS[0]))
        all_conn = _get_all_connections()
        conn_for_sd = storagedomains.getConnectionsForStorageDomain(sd_name)
        assert len(all_conn) == 1
        assert len(conn_for_sd) == 1
        assert _compare_connections(all_conn[0], conn_for_sd[0])
        storagedomains.removeStorageDomain(True, sd_name, config.HOSTS[0])
        storageconnections.remove_all_storage_connections()
        assert not _get_all_connections()

    def verify_no_connections(self):
        sds = storagedomains.getDCStorages(config.DATA_CENTER_NAME, False)
        assert not sds
        assert not _get_all_connections()

    def verify_storage_domain_with_two_connections(self):
        sd_name = "sd_2_%s" % self.tcms_test_case
        assert storagedomains.addStorageDomain(
            True, host=config.HOSTS[0], name=sd_name,
            type=config.ENUMS['storage_dom_type_data'],
            storage_type=config.DATA_CENTER_TYPE,
            lun=config.CONNECTIONS[0]['luns'][0], **(config.CONNECTIONS[0]))
        assert storagedomains.attachStorageDomain(
            True, config.DATA_CENTER_NAME, sd_name)
        assert storagedomains.waitForStorageDomainStatus(
            True, config.DATA_CENTER_NAME, sd_name,
            config.ENUMS['storage_domain_state_active'])
        assert storagedomains.extendStorageDomain(
            True, sd_name, storage_type=config.DATA_CENTER_TYPE,
            host=config.HOSTS[0], lun=config.CONNECTIONS[1]['luns'][0],
            **(config.CONNECTIONS[1]))

        all_conn = _get_all_connections()
        conn_for_sd = storagedomains.getConnectionsForStorageDomain(sd_name)
        assert len(all_conn) == 2
        assert len(conn_for_sd) == 2
        _restore_empty_dc()

    def verify_two_storage_domains_with_the_same_connection(self):
        sd_name_1 = "sd_3_%s" % self.tcms_test_case
        storagedomains.addStorageDomain(
            True, host=config.HOSTS[0], name=sd_name_1,
            type=config.ENUMS['storage_dom_type_data'],
            storage_type=config.DATA_CENTER_TYPE,
            lun=config.CONNECTIONS[0]['luns'][0], **(config.CONNECTIONS[0]))
        sd_name_2 = "sd_4_%s" % self.tcms_test_case
        storagedomains.addStorageDomain(
            True, host=config.HOSTS[0], name=sd_name_2,
            type=config.ENUMS['storage_dom_type_data'],
            storage_type=config.DATA_CENTER_TYPE,
            lun=config.CONNECTIONS[0]['luns'][1], **(config.CONNECTIONS[0]))

        all_conn = _get_all_connections()
        conn_sd_1 = storagedomains.getConnectionsForStorageDomain(sd_name_1)
        conn_sd_2 = storagedomains.getConnectionsForStorageDomain(sd_name_2)
        assert len(all_conn) == 1
        assert len(conn_sd_1) == 1
        assert len(conn_sd_2) == 1
        assert _compare_connections(conn_sd_1[0], conn_sd_2[0])
        storagedomains.removeStorageDomain(True, sd_name_1, config.HOSTS[0])
        storagedomains.removeStorageDomain(True, sd_name_2, config.HOSTS[0])
        storageconnections.remove_all_storage_connections()
        assert not _get_all_connections()

    def verify_one_direct_lun(self):
        assert not _get_all_connections()
        alias = "disk_1_%s" % self.tcms_test_case
        _add_disk(config.CONNECTIONS[0], alias)
        self.disks.append(alias)
        all_conn = _get_all_connections()
        # uncomment following lines when the call
        # /disks/<id>/storageconnections is done
#        conn_disk = disks.getConnectionsForDisk(alias)
        assert len(all_conn) == 1
#        assert len(conn_disk) == 1
#        assert _compare_connections(all_conn, conn_disk)
        disks.deleteDisk(True, alias)

    @tcms(tcms_plan_id, tcms_test_case)
    @bz(1012944)
    def test_get_storage_connections(self):
        """ Verify that GET call works for various connection/storage domains
        combinations
        """
        LOGGER.info("Verifying get for no connections")
        self.verify_no_connections()

        LOGGER.info("Verifying get for one orphaned connection")
        self.verify_one_orphaned_connection()

        LOGGER.info("Verifying get for one storage domain")
        self.verify_one_storage_domain()

        LOGGER.info("Verifying get for a storage domain with 2 connections")
        self.verify_storage_domain_with_two_connections()

        LOGGER.info("Verifying get for 2 domains with same connection")
        self.verify_two_storage_domains_with_the_same_connection()

        LOGGER.info("Verifying get for direct LUN")
        self.verify_one_direct_lun()

    @classmethod
    def teardown_class(cls):
        LOGGER.info("Tear down")
        for alias in cls.disks:
            LOGGER.info("Deleting disk %s" % alias)
            disks.deleteDisk(True, alias)

        _restore_empty_dc()


class TestCase288975(TestCase):
    """
    https://tcms.engineering.redhat.com/case/288975/?from_plan=9985

    **Author**: Katarzyna Jachim
    """
    __test__ = True
    tcms_plan_id = '9985'
    tcms_test_case = '288975'
    conn = None
    sd_name_1 = "sd_%s_1" % tcms_test_case
    sd_name_2 = "sd_%s_2" % tcms_test_case

    def setUp(self):
        assert storagedomains.addStorageDomain(
            True, host=config.HOSTS[0], name=self.sd_name_1,
            type=config.ENUMS['storage_dom_type_data'],
            storage_type=config.DATA_CENTER_TYPE,
            lun=config.CONNECTIONS[0]['luns'][0], **(config.CONNECTIONS[0]))

        assert storagedomains.addStorageDomain(
            True, host=config.HOSTS[0], name=self.sd_name_2,
            type=config.ENUMS['storage_dom_type_data'],
            storage_type=config.DATA_CENTER_TYPE,
            lun=config.CONNECTIONS[0]['luns'][1], **(config.CONNECTIONS[0]))

        assert storagedomains.attachStorageDomain(
            True, config.DATA_CENTER_NAME, self.sd_name_1)
        assert storagedomains.attachStorageDomain(
            True, config.DATA_CENTER_NAME, self.sd_name_2)
        storagedomains.waitForStorageDomainStatus(
            True, config.DATA_CENTER_NAME, self.sd_name_1,
            config.ENUMS['storage_domain_state_active'])
        storagedomains.waitForStorageDomainStatus(
            True, config.DATA_CENTER_NAME, self.sd_name_2,
            config.ENUMS['storage_domain_state_active'])

    def _try_to_change_connection(self, conn_id, should_pass):
        assert should_pass is storageconnections.update_connection(
            conn_id, lun_address=config.CONNECTIONS[1]['lun_address'],
            type=config.DATA_CENTER_TYPE)[1]
        assert should_pass is storageconnections.update_connection(
            conn_id, lun_target=config.CONNECTIONS[1]['lun_target'],
            type=config.DATA_CENTER_TYPE)[1]
        assert should_pass is storageconnections.update_connection(
            conn_id, lun_port=config.CONNECTIONS[1]['lun_port'],
            type=config.DATA_CENTER_TYPE)[1]

    @tcms(tcms_plan_id, tcms_test_case)
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
        self._try_to_change_connection(conn.id, False)
        assert storagedomains.deactivateStorageDomain(
            True, config.DATA_CENTER_NAME, self.sd_name_2)
        self._try_to_change_connection(conn.id, False)
        assert storagedomains.deactivateStorageDomain(
            True, config.DATA_CENTER_NAME, self.sd_name_1)
        self._try_to_change_connection(conn.id, True)
        assert storagedomains.activateStorageDomain(
            True, config.DATA_CENTER_NAME, self.sd_name_1)
        assert storagedomains.activateStorageDomain(
            True, config.DATA_CENTER_NAME, self.sd_name_2)

    @classmethod
    def teardown_class(cls):
        _restore_empty_dc()


class TestCase288968(TestCase):
    """
    https://tcms.engineering.redhat.com/case/288968/?from_plan=9985

    **Author**: Katarzyna Jachim
    """
    __test__ = True
    tcms_plan_id = '9985'
    tcms_test_case = '288968'
    conn = None
    sd_name_1 = "sd_%s_1" % tcms_test_case
    sd_name_2 = "sd_%s_2" % tcms_test_case

    def setUp(self):
        assert storagedomains.addStorageDomain(
            True, host=config.HOSTS[0], name=self.sd_name_1,
            type=config.ENUMS['storage_dom_type_data'],
            storage_type=config.DATA_CENTER_TYPE,
            lun=config.CONNECTIONS[0]['luns'][0], **(config.CONNECTIONS[0]))

        assert storagedomains.addStorageDomain(
            True, host=config.HOSTS[0], name=self.sd_name_2,
            type=config.ENUMS['storage_dom_type_data'],
            storage_type=config.DATA_CENTER_TYPE,
            lun=config.CONNECTIONS[0]['luns'][1], **(config.CONNECTIONS[0]))

        assert storagedomains.attachStorageDomain(
            True, config.DATA_CENTER_NAME, self.sd_name_1)
        assert storagedomains.attachStorageDomain(
            True, config.DATA_CENTER_NAME, self.sd_name_2)

        conn = dict(config.CONNECTIONS[1])
        conn['type'] = config.DATA_CENTER_TYPE
        self.conn, success = storageconnections.add_connection(**conn)
        assert success

    @tcms(tcms_plan_id, tcms_test_case)
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
        assert storagedomains.deactivateStorageDomain(
            True, config.DATA_CENTER_NAME, self.sd_name_1)
        assert storagedomains.addConnectionToStorageDomain(
            self.sd_name_1, self.conn.id)
        assert storagedomains.activateStorageDomain(
            True, config.DATA_CENTER_NAME, self.sd_name_1)

        assert storagedomains.deactivateStorageDomain(
            True, config.DATA_CENTER_NAME, self.sd_name_2)
        assert storagedomains.addConnectionToStorageDomain(
            self.sd_name_2, self.conn.id)
        assert not storagedomains.addConnectionToStorageDomain(
            self.sd_name_2, self.conn.id)
        assert storagedomains.activateStorageDomain(
            True, config.DATA_CENTER_NAME, self.sd_name_2)

    @classmethod
    def teardown_class(cls):
        _restore_empty_dc()


class TestCase289552(TestCase):
    """
    https://tcms.engineering.redhat.com/case/289552/?from_plan=9985

    **Author**: Katarzyna Jachim
    """
    __test__ = True
    tcms_plan_id = '9985'
    tcms_test_case = '289552'
    conn = None
    vm_name_1 = "vm_%s_1" % tcms_test_case
    vm_name_2 = "vm_%s_2" % tcms_test_case
    disk_1 = "disk_%s_1" % tcms_test_case
    sd_name = "sd_%s" % tcms_test_case
    disk_2 = "disk_%s_2" % tcms_test_case

    def setUp(self):
        assert storagedomains.addStorageDomain(
            True, host=config.HOSTS[0], name=self.sd_name,
            type=config.ENUMS['storage_dom_type_data'],
            storage_type=config.DATA_CENTER_TYPE,
            lun=config.CONNECTIONS[1]['luns'][0], **(config.CONNECTIONS[1]))

        assert storagedomains.attachStorageDomain(
            True, config.DATA_CENTER_NAME, self.sd_name)

        assert storagedomains.waitForStorageDomainStatus(
            True, config.DATA_CENTER_NAME, self.sd_name,
            config.ENUMS['storage_domain_state_active'])

        assert vms.createVm(
            True, self.vm_name_1, self.vm_name_1, cluster=config.CLUSTER_NAME,
            storageDomainName=self.sd_name,
            nic=config.HOST_NICS[0], size=config.DISK_SIZE,
            diskType=config.DISK_TYPE_SYSTEM, volumeType=True,
            volumeFormat=config.ENUMS['format_cow'], memory=GB,
            diskInterface=config.INTERFACE_VIRTIO,
            cpu_socket=config.CPU_SOCKET,
            cpu_cores=config.CPU_CORES, nicType=config.NIC_TYPE_VIRTIO,
            display_type=config.DISPLAY_TYPE, os_type=config.OS_TYPE,
            user=config.VM_LINUX_USER, password=config.VM_LINUX_PASSWORD,
            type=config.VM_TYPE_DESKTOP, installation=True, slim=True,
            image=config.COBBLER_PROFILE, network=config.MGMT_BRIDGE)

        assert vms.createVm(
            True, self.vm_name_2, self.vm_name_2, cluster=config.CLUSTER_NAME,
            storageDomainName=self.sd_name,
            nic=config.HOST_NICS[0], size=config.DISK_SIZE,
            diskType=config.DISK_TYPE_SYSTEM, volumeType=True,
            volumeFormat=config.ENUMS['format_cow'], memory=GB,
            diskInterface=config.INTERFACE_VIRTIO,
            cpu_socket=config.CPU_SOCKET,
            cpu_cores=config.CPU_CORES, nicType=config.NIC_TYPE_VIRTIO,
            display_type=config.DISPLAY_TYPE, os_type=config.OS_TYPE,
            user=config.VM_LINUX_USER, password=config.VM_LINUX_PASSWORD,
            type=config.VM_TYPE_DESKTOP, installation=True, slim=True,
            image=config.COBBLER_PROFILE, network=config.MGMT_BRIDGE)

        assert vms.stopVm(True, self.vm_name_1)
        assert vms.stopVm(True, self.vm_name_2)

        assert disks.addDisk(
            True, alias=self.disk_1,
            interface=config.ENUMS["interface_virtio"],
            format=config.ENUMS["format_cow"],
            lun_id=config.CONNECTIONS[0]['luns'][0],
            lun_address=config.CONNECTIONS[0]['lun_address'],
            lun_target=config.CONNECTIONS[0]['lun_target'],
            type_=config.ENUMS['storage_type_iscsi'])

        assert disks.addDisk(
            True, alias=self.disk_2,
            interface=config.ENUMS["interface_virtio"],
            format=config.ENUMS["format_cow"],
            lun_id=config.CONNECTIONS[0]['luns'][1],
            lun_address=config.CONNECTIONS[0]['lun_address'],
            lun_target=config.CONNECTIONS[0]['lun_target'],
            type_=config.ENUMS['storage_type_iscsi'])

        assert disks.attachDisk(True, self.disk_1, self.vm_name_1)
        assert disks.attachDisk(True, self.disk_2, self.vm_name_2)

        assert vms.startVm(True, self.vm_name_1)
        assert vms.startVm(True, self.vm_name_2)

    @tcms(tcms_plan_id, tcms_test_case)
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

        # find connection - we cannot just call /disk/<id>/connections
        # as the call is postponed :/
        connections = api.get(absLink=False)
        lun_conn = None
        for conn in connections:
            if conn.target == config.CONNECTIONS[0]['lun_target']:
                lun_conn = conn
                break

        assert lun_conn

        assert not storageconnections.update_connection(
            lun_conn.id, lun_address=config.CONNECTIONS[1]['lun_address'],
            type=config.DATA_CENTER_TYPE)[1]

        assert vms.stopVm(True, self.vm_name_1)
        assert vms.waitForVMState(
            self.vm_name_1, config.ENUMS['vm_state_down'])

        assert not storageconnections.update_connection(
            lun_conn.id, lun_address=config.CONNECTIONS[1]['lun_address'],
            type=config.DATA_CENTER_TYPE)[1]

        assert vms.stopVm(True, self.vm_name_2)
        assert vms.waitForVMState(
            self.vm_name_2, config.ENUMS['vm_state_down'])

        assert storageconnections.update_connection(
            lun_conn.id, type=config.DATA_CENTER_TYPE,
            **(config.CONNECTIONS[1]))[1]

        assert vms.startVm(True, self.vm_name_1)
        assert vms.startVm(True, self.vm_name_2)

    @classmethod
    def teardown_class(cls):
        storagedomains.cleanDataCenter(
            True, config.DATA_CENTER_NAME, vdc=config.VDC,
            vdc_password=config.VDC_PASSWORD)
        storageconnections.remove_all_storage_connections()
        datacenters.build_setup(
            config.PARAMETERS, config.PARAMETERS, config.DATA_CENTER_TYPE,
            basename=config.BASENAME)


class TestCase288988(TestCase):
    """
    https://tcms.engineering.redhat.com/case/288988/?from_plan=9985

    **Author**: Katarzyna Jachim
    """
    __test__ = True
    tcms_plan_id = '9985'
    tcms_test_case = '288988'
    conn = None
    sds = []

    @classmethod
    def setup_class(cls):
        conn = dict(config.CONNECTIONS[0])
        conn['type'] = config.DATA_CENTER_TYPE
        cls.conn, success = storageconnections.add_connection(**conn)
        assert success

    @tcms(tcms_plan_id, tcms_test_case)
    def test_adding_storage_domains(self):
        """ Adds:
            * a storage domain using a new connection (old flow)
            * a storage domain with all params specified (old flow), but
              the connection params are the same of an existing connection
            In the last case, new connection should not be added.
        """
        sd_name_2 = "sd_%s_2" % self.tcms_test_case
        sd_name_3 = "sd_%s_3" % self.tcms_test_case

        assert storagedomains.addStorageDomain(
            True, name=sd_name_2, host=config.HOSTS[0],
            type=config.ENUMS['storage_dom_type_data'],
            storage_type=config.DATA_CENTER_TYPE,
            lun=config.CONNECTIONS[1]['luns'][0], **(config.CONNECTIONS[1]))
        self.sds.append(sd_name_2)

        assert storagedomains.addStorageDomain(
            True, name=sd_name_3, host=config.HOSTS[0],
            type=config.ENUMS['storage_dom_type_data'],
            storage_type=config.DATA_CENTER_TYPE,
            lun=config.CONNECTIONS[0]['luns'][1],
            **(config.CONNECTIONS[0]))
        self.sds.append(sd_name_3)

        assert len(_get_all_connections()) == 2

    @classmethod
    def teardown_class(cls):
        _restore_empty_dc()
