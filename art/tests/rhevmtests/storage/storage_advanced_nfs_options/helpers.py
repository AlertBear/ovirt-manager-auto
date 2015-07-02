"""
Helper functions for advanced NFS options test suite
"""

import logging
import ConfigParser
import io
import time
import tempfile
import os

from art.unittest_lib import StorageTest as TestCase

from art.rhevm_api.utils import test_utils
from art.core_api import apis_exceptions
from art.test_handler import exceptions
from utilities import sshConnection

from art.rhevm_api.tests_lib.high_level import datacenters as hl_dc
from art.rhevm_api.tests_lib.high_level import storagedomains as hl_st
from art.rhevm_api.tests_lib.low_level import datacenters as ll_dc
from art.rhevm_api.tests_lib.low_level import clusters as ll_cl
from art.rhevm_api.tests_lib.low_level import storagedomains as ll_st
from art.rhevm_api.tests_lib.low_level import vms as ll_vms
from art.rhevm_api.tests_lib.low_level import templates as ll_templ
from art.rhevm_api.tests_lib.low_level import disks as ll_disks
from art.rhevm_api.tests_lib.low_level import hosts as ll_hosts
from art.rhevm_api.tests_lib.low_level.jobs import wait_for_jobs

import config

logger = logging.getLogger(__name__)
ENUMS = config.ENUMS
VDSM_CONFIG_FILE = '/etc/vdsm/vdsm.conf'
STORAGE_DOMAIN_API = test_utils.get_api('storage_domain', 'storagedomains')
VERSION_30 = '3.0'
VERSION_31 = '3.1'
DEFAULT_NFS_RETRANS = 6
DEFAULT_NFS_TIMEOUT = 600
DEFAULT_DC_TIMEOUT = 1500
NFS = config.STORAGE_TYPE_NFS


def _verify_one_option(real, expected):
    """ helper function for verification of one option
    """
    return expected is None or expected == real


def verify_nfs_options(
        expected_timeout, expected_retrans, expected_nfsvers,
        real_timeo, real_retrans, real_nfsvers):
    """
    Verifies that the real nfs options are as expected.

    **Author**: Katarzyna Jachim

    **Parameters**:
        * *expected_timeout*: expected NFS timeout
        * *expected_retrans*: expected # of retransmissions
        * *expected_nfsvers*: expected NFS protocol version
        * *real_timeo*: NFS timeout returned by 'mount' command
        * *real_retrans*: # of retransmissions returned by 'mount' command
        * *real_nfsvers*: NFS protocol version returned by 'mount' command

    **Returns**: None in case of success or tuple (param_name, expected, real)
    """
    if not _verify_one_option(real_timeo, expected_timeout):
        return ("timeo", expected_timeout, real_timeo)
    if not _verify_one_option(real_retrans, expected_retrans):
        return ("retrans", expected_retrans, real_retrans)
    if not _verify_one_option(real_nfsvers, expected_nfsvers):
        return ("nfsvers", expected_nfsvers, real_nfsvers)


def _run_ssh_command(host, password, cmd, exc):
    host_ip = ll_hosts.getHostIP(host)
    ssh_session = sshConnection.SSHSession(
        hostname=host_ip, username='root', password=password)
    rc, out, err = ssh_session.runCmd(cmd)
    if rc:
        raise exceptions.HostException("%s %s" % (exc, err))
    return out


def _read_vdsm_config(host, password):
    cmd = 'cat %s' % VDSM_CONFIG_FILE
    exc = "Reading vdsm.conf on %s failed with" % host
    return _run_ssh_command(host, password, cmd, exc)


def _parse_config(text):
    parser = ConfigParser.RawConfigParser()
    parser.readfp(io.BytesIO(text))
    return parser


def _write_vdsm_config(host, password, text):
    fd, name = tempfile.mkstemp()
    try:
        os.write(fd, text)
        os.close(fd)
        ssh_session = sshConnection.SSHSession(
            hostname=host, username='root', password=password)
        ssh_session.getFileHandler().copyTo(name, VDSM_CONFIG_FILE)
    finally:
        os.remove(name)


def _create_config_copy(host, password, copy_file):
    cmd = 'cp %s %s' % (VDSM_CONFIG_FILE, copy_file)
    logger.info("cmd: %s", cmd)
    exc = 'Cannot create a copy of vdsm.conf on %s:' % host
    _run_ssh_command(host, password, cmd, exc)


def change_vdsm_config(host, password, params):
    """ Changes vdsm.conf on given host

    **Author**: Katarzyna Jachim

    **Parameters**:
        * *host*: host with vdsm.conf
        * *password*: root password for the above host
        * *params*: dict {section -> {param -> value}}

    **Returns**: path to the file with copy of old vdsm.conf
    """
    vdsm_config_parser = _parse_config(_read_vdsm_config(host, password))
    for section, options in params.iteritems():
        if not vdsm_config_parser.has_section(section):
            vdsm_config_parser.add_section(section)
        for option, value in options.iteritems():
            vdsm_config_parser.set(section, option, value)

    str_buffer = io.BytesIO()
    vdsm_config_parser.write(str_buffer)
    new_config = str_buffer.getvalue()
    str_buffer.close()

    logger.info("New vdsm config: %s", new_config)

    copy_file = 'vdsm_conf_copy_%s.conf' % time.strftime('%y_%m_%d_%H_%M')
    _create_config_copy(host, password, copy_file)

    _write_vdsm_config(host, password, new_config)

    return copy_file


def restore_vdsm_config(host, password, copy_file):
    """ Restores old vdsm.conf on given host

    **Author**: Katarzyna Jachim

    **Parameters**:
        * *host*: host with vdsm.conf
        * *password*: root password for the above host
        * *copy_file*: path to the copy of the old vdsm.conf

    **Returns**: path to the file with copy of old vdsm.conf
    """
    cmd = 'cp %s %s && rm %s' % (copy_file, VDSM_CONFIG_FILE, copy_file)
    exc = 'Cannot restore a copy of vdsm.conf on %s:' % host
    _run_ssh_command(host, password, cmd, exc)


class NFSStorage(object):
    """ Helper class - one object represents one NFS storage domain.

    **Attributes**:
        * *name*: name of the storage domain in RHEV-M
        * *address*: address of the NFS server
        * *path*: path to the NFS resource on the NFS server
        * *timeout_to_set*: value of the NFS timeout which should be passed to
                        RHEV-M when storage domain is created
        * *retrans_to_set*: # of retransmissions as above
        * *vers_to_set*: NFS protocol version as above
        * *expected_timeout*: value of the NFS timeout which should be used by
                          RHEV-M when NFS resource is mounted on the host
        * *expected_retrans*: # of retransmissions as above
        * *expected_vers*: NFS protocol version as above
        * *sd_type*: one of ENUMS['storage_dom_type_data'],
             ENUMS['storage_dom_type_iso'], ENUMS['storage_dom_type_export']

        Actually, the X_to_set and expected_X values are different only when
        X_to_set is None, which means that the default value should be used.
    """
    __allowed = ("name", "address", "path", "sd_type",
                 "timeout_to_set", "retrans_to_set", "vers_to_set",
                 "expected_timeout", "expected_retrans", "expected_vers")

    def __init__(self, **kwargs):
        self.sd_type = ENUMS['storage_dom_type_data']
        for k, v in kwargs.iteritems():
            assert (k in self.__allowed)
            setattr(self, k, v)


class TestCaseNFSOptions(TestCase):
    """
    Base class for all NFS tests, the common teardown and the most common
    operation (create storage domain with specific NFS options, then check
    if they are really as expected)

    **Author**: Katarzyna Jachim
    """
    __test__ = False
    dc_name = None
    host = None
    password = None
    cl_name = None
    host_for_dc = None
    storages = set([NFS])

    @classmethod
    def setup_class(cls):
        cls.sds_for_cleanup = []
        cls.host = ll_hosts.getSPMHost(config.HOSTS)
        cls.host_ip = ll_hosts.getHostIP(cls.host)
        cls.password = config.HOSTS_PW

    @classmethod
    def teardown_class(cls):
        """
        Remove the storage domains created during the test
        """
        logger.info("Cleanup - removing storage domains")
        for storage_domain in cls.sds_for_cleanup:
            logger.info("Removing storage domain %s", storage_domain)
            if ll_st.checkIfStorageDomainExist(True, storage_domain):
                try:
                    test_utils.wait_for_tasks(
                        config.VDC, config.VDC_PASSWORD,
                        config.DATA_CENTER_NAME
                    )
                    hl_st.remove_storage_domain(
                        storage_domain, config.DATA_CENTER_NAME,
                        cls.host, True
                    )
                except exceptions.StorageDomainException:
                    logger.error("Unable to remove storage domain %s",
                                 storage_domain)
            # TODO: mount and remove all the content just in case

    def create_nfs_domain_and_verify_options(self, domain_list, host=None,
                                             password=None, datacenter=None):
        """
        Creates NFS domains with specified options, if datacenter is not
        None - attaches them to this datacenter, then check that the specified
        NFS resources are mounted on given host with required options.

        **Author**: Katarzyna Jachim

        **Parameters**:
         * *domain_list*: list of objects of class NFSStorage, each of them
                          describes one storage domain
         * *host*: name of host on which storage domain should be mounted
         * *password*: root password on the host
         * *datacenter*: if not None - datacenter to which NFS storage domain
                         should be attached

        **Returns**: nothing, fails the test in case of any error
        """
        if host is None:
            host = self.host

        host_ip = ll_hosts.getHostIP(host)

        if password is None:
            password = config.HOSTS_PW

        if datacenter is None:
            datacenter = config.DATA_CENTER_NAME

        for domain in domain_list:
            logger.info("Creating nfs domain %s", domain.name)
            hl_st.create_nfs_domain_with_options(
                domain.name, domain.sd_type, host, domain.address,
                domain.path, retrans=domain.retrans_to_set,
                version=domain.vers_to_set, timeo=domain.timeout_to_set,
                datacenter=datacenter)

        logger.info("Getting info about mounted resources")
        mounted_resources = ll_st.get_mounted_nfs_resources(host_ip, password)

        logger.info("verifying nfs options")
        for domain in domain_list:
            nfs_timeo, nfs_retrans, nfs_vers, nfs_sync = mounted_resources[
                (domain.address, domain.path)]
            result = verify_nfs_options(
                domain.expected_timeout, domain.expected_retrans,
                domain.expected_vers, nfs_timeo, nfs_retrans, nfs_vers)
            if result is not None:
                self.fail(
                    "Wrong NFS options! Expected %s: %s, real: %s" % result)

    def create_dc(self, version):
        """ Creates datacenter of given version and adds cluster & host
        according to self params.
        Uses self.dc_name, self.cl_name, self.host, self.password
        """
        logger.info("Creating %s datacenter", version)
        if not ll_dc.addDataCenter(
                True, name=self.dc_name, storage_type=NFS,
                version=version
        ):
            self.fail("Adding %s datacenter failed" % self.dc_name)
        logger.info("Datacenter %s was created successfully", self.dc_name)

        logger.info("Adding cluster to the datacenter")
        if not ll_cl.addCluster(
                True, name=self.cl_name, version=config.COMP_VERSION,
                cpu=config.CPU_NAME, data_center=self.dc_name
        ):
            self.fail("Adding cluster to datacenter %s failed" % self.dc_name)
        logger.info("Cluster was created successfully")

        logger.info("Adding host to dc %s", self.dc_name)
        self.assertTrue(ll_hosts.addHost(
            True, name=self.host_for_dc, root_password=self.password,
            cluster=self.cl_name, reboot=True,
            ), "Unable to add host %s to cluster %s" % (
            self.host_for_dc, self.cl_name)
        )
        logger.info("Datacenter %s prepared successfully", version)


def clean_dc(dc_name, host, cl_name, sd_name=None):
    """ Removes given datacenter, host & cluster, if sd_name is not None,
    removes also given storage domain
    """
    if ll_st.getDCStorages(dc_name, False):  # the easy part
        logger.info("Tear down - removing data center")
        hl_dc.clean_datacenter(True, dc_name)
    else:
        if sd_name is not None:
            logger.info("Tear down - removing storage domain")
            ll_st.removeStorageDomain(True, sd_name, host, 'true')
        logger.info("Tear down - removing data center")
        ll_dc.removeDataCenter(True, dc_name)
        logger.info("Tear down - deactivating host")
        ll_hosts.deactivateHost(True, host)
        logger.info("Tear down - removing host")
        ll_hosts.removeHost(True, host)
        logger.info("Tear down - removing cluster")
        ll_cl.removeCluster(True, cl_name)


class TestCaseStandardOperations(TestCaseNFSOptions):
    """ Base class for tests performing 'standard operations' (see docstring
    of perform_standard_operations for particulars).
    """
    sd_1 = None
    sd_2 = None
    sd_exp = None
    disk_1 = None
    disk_2 = None
    vm_1 = None
    vm_2 = None
    template = None
    host_for_dc = None
    master_domain = None

    @classmethod
    def setup_class(cls):
        """Getting the master domain"""
        logger.info("Getting master storage domain")
        found, master_domain = ll_st.findMasterStorageDomain(
            True, config.DATA_CENTER_NAME,
        )
        if not found:
            cls.fail("Master storage domain not found")
        cls.master_domain = master_domain['masterDomain']
        super(TestCaseStandardOperations, cls).setup_class()

    def setUp(self):
        """ Prepares environment - creates storage domains with different
        NFS options, vms, a template etc.

        Don't change to setup_class, as in case setup_class fails,
        teardown_class won't be called (and all later tests will fail)!
        """
        sd_type = ENUMS['storage_dom_type_data']
        datacenter = config.DATA_CENTER_NAME

        hl_st.create_nfs_domain_with_options(
            self.sd_1, sd_type, self.host, config.NFS_ADDRESSES[0],
            config.NFS_PATHS[0], version='v3', retrans=7, timeo=700,
            datacenter=datacenter)
        self.assertTrue(
            ll_st.activateStorageDomain(True, datacenter, self.sd_1))

        hl_st.create_nfs_domain_with_options(
            self.sd_2, sd_type, self.host, config.NFS_ADDRESSES[1],
            config.NFS_PATHS[1], version='v3', retrans=8, timeo=800,
            datacenter=datacenter)
        self.assertTrue(
            ll_st.activateStorageDomain(True, datacenter, self.sd_2))

        hl_st.create_nfs_domain_with_options(
            self.sd_exp, ENUMS['storage_dom_type_export'], self.host,
            config.NFS_ADDRESSES[2], config.NFS_PATHS[2],
            datacenter=datacenter)
        self.assertTrue(
            ll_st.activateStorageDomain(True, datacenter, self.sd_exp))

        self.assertTrue(ll_disks.addDisk(
            True, alias=self.disk_1, size=config.DISK_SIZE,
            storagedomain=self.sd_1, format=ENUMS['format_raw'],
            interface=config.INTERFACE_VIRTIO, bootable=True))

        self.assertTrue(ll_disks.addDisk(
            True, alias=self.disk_2, size=config.DISK_SIZE,
            storagedomain=self.sd_1, format=ENUMS['format_raw'],
            interface=config.INTERFACE_VIRTIO, bootable=True))

        self.assertTrue(ll_vms.addVm(
            True, name=self.vm_1, storagedomain=self.sd_1,
            cluster=config.CLUSTER_NAME))
        self.assertTrue(ll_vms.addVm(
            True, name=self.vm_2, storagedomain=self.sd_1,
            cluster=config.CLUSTER_NAME))

        self.assertTrue(ll_disks.wait_for_disks_status(
            [self.disk_1, self.disk_2], timeout=600)
        )

        self.assertTrue(ll_disks.attachDisk(True, self.disk_1, self.vm_1))
        self.assertTrue(ll_disks.attachDisk(True, self.disk_2, self.vm_2))

        self.assertTrue(ll_templ.createTemplate(
            True, vm=self.vm_1, name=self.template,
            cluster=config.CLUSTER_NAME))

        self.assertTrue(ll_hosts.addHost(
            True, name=self.host_for_dc, root_password=self.password,
            cluster=config.CLUSTER_NAME,
            ), "Unable to add host %s to cluster %s" % (
            self.host_for_dc, config.CLUSTER_NAME)
        )

    def perform_standard_operations(self, vm, vm_with_disk, disk, another_std,
                                    template, export_std, datacenter):
        """
        Performs standard operations:
            * moves disk of a vm to another storage domain
            * moves vm to another storage domain
            * migrates vm to another host
            * exports template
            * changes SPM host
            * rebuilds master storage domain

        **Author**: Katarzyna Jachim

        **Parameters**:
         * *vm*: vm which will be moved and migrated
         * *vm_with_disk*: vm which disk will be moved
         * *disk*: disk which should be moved
         * *another_std*: storage domain to which we will move vm/disk
         * *template*: template which will be exported
         * *export_std*: export storage domain
         * *datacenter*: datacenter on which we will perform operations

        **Returns**: nothing, fails the test in case of any error
        """
        self.master_domain = None
        logger.info("Moving disk %s to %s", disk, another_std)
        ll_vms.move_vm_disk(vm_with_disk, disk, another_std)

        logger.info("Moving vm %s to sd %s", vm, another_std)
        if not ll_vms.moveVm(True, vm, another_std):
            self.fail(
                "Cannot move vm %s to storage domain %s", vm, another_std)

        logger.info("Migrating vm %s", vm)
        logger.info("Starting vm %s", vm)
        ll_vms.startVm(True, vm)
        status, host_with_vm = ll_vms.getVmHost(vm)
        host_with_vm = host_with_vm['vmHoster']
        logger.info("Current host: %s", host_with_vm)
        if not status:
            self.fail("Cannot get host with vm")

        hosts = config.HOSTS + [self.host_for_dc]
        host_2 = filter(lambda w: w != host_with_vm, hosts)[0]
        if not ll_vms.migrateVm(True, vm, host_2):
            self.fail("Cannot migrate vm %s to %s" % (vm, host_2))
        logger.info("Exporting template")
        if not ll_templ.exportTemplate(True, template, export_std, wait=True):
            self.fail(
                "Exporting template %s on %s failed" % (template, export_std))

        logger.info("Changing SPM host")
        old_spm_host = ll_hosts.getSPMHost(hosts)
        wait_for_jobs()
        if not ll_hosts.deactivateHost(True, old_spm_host):
            logger.error("Cannot deactivate host %s", old_spm_host)
            self.fail("Cannot deactivate host %s" % old_spm_host)
        ll_hosts.waitForSPM(config.DATA_CENTER_NAME, 600, 30)
        new_spm_host = ll_hosts.getSPMHost(hosts)
        logger.info("New SPM host: %s", new_spm_host)

        logger.info("Getting master storage domain")
        found, master_domain = ll_st.findMasterStorageDomain(
            True, config.DATA_CENTER_NAME)
        if not found:
            self.fail("Master storage domain not found")
        self.master_domain = master_domain['masterDomain']
        logger.info(
            "Deactivating master storage domain %s", self.master_domain,
        )
        if not ll_st.deactivateStorageDomain(
            True, datacenter, self.master_domain
        ):
            self.fail("Cannot deactivate master storage domain")
        found, new_master = ll_st.findMasterStorageDomain(
            True, config.DATA_CENTER_NAME)
        if not found:
            self.fail("New master not found!")
        logger.info("New master: %s", new_master['masterDomain'])

    @classmethod
    def teardown_class(cls):
        """ Clears everything which won't be cleaned with basic tear down
        Don't add asserts, in case of errors in the test some of the commands
        may fail and it is OK.
        """
        wait_for_jobs()
        try:
            ll_vms.stop_vms_safely([cls.vm_1])
        except apis_exceptions.EntityNotFound:
            pass
        if not ll_hosts.isHostUp(True, cls.host):
            ll_hosts.activateHost(True, cls.host)
        try:
            ll_templ.removeTemplate(True, cls.template)
        except apis_exceptions.EntityNotFound:
            pass
        try:
            ll_vms.removeVm(True, vm=cls.vm_1)
        except apis_exceptions.EntityNotFound:
            pass
        try:
            ll_vms.removeVm(True, vm=cls.vm_2)
        except apis_exceptions.EntityNotFound:
            pass
        ll_vms.waitForVmsGone(True, ",".join([cls.vm_1, cls.vm_2]))

        if cls.master_domain:
            ll_st.activateStorageDomain(
                True, config.DATA_CENTER_NAME, cls.master_domain,
            )
            ll_st.waitForStorageDomainStatus(
                True, config.DATA_CENTER_NAME, cls.master_domain,
                config.SD_ACTIVE, timeOut=DEFAULT_DC_TIMEOUT)

        wait_for_jobs()
        for sd_remove in [cls.sd_1, cls.sd_2, cls.sd_exp]:
            if ll_st.checkIfStorageDomainExist(True, sd_remove):
                cls.sds_for_cleanup.append(sd_remove)
                ll_st.deactivateStorageDomain(
                    True, config.DATA_CENTER_NAME, sd_remove)
        try:
            logger.info("Removing host %s", cls.host_for_dc)
            if ll_hosts.getHostState(cls.host_for_dc) == config.HOST_UP:
                ll_hosts.deactivateHost(True, cls.host_for_dc)
            ll_hosts.waitForSPM(config.DATA_CENTER_NAME, 600, 30)
            ll_hosts.removeHost(True, cls.host_for_dc)
        except apis_exceptions.EntityNotFound:
            pass
        super(TestCaseStandardOperations, cls).teardown_class()
