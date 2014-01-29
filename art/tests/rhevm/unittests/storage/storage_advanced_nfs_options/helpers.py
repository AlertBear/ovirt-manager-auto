"""
Helper functions for advanced NFS options test suite
"""

import logging
import ConfigParser
import io
import time
import tempfile
import os
from unittest import TestCase

from art.rhevm_api.utils import test_utils
from art.core_api import apis_exceptions
from art.test_handler import exceptions
from utilities import sshConnection

from art.rhevm_api.tests_lib.low_level import storagedomains as ll_st
from art.rhevm_api.tests_lib.high_level import storagedomains as hl_st
from art.rhevm_api.tests_lib.low_level import datacenters as ll_dc
from art.rhevm_api.tests_lib.low_level import clusters as ll_cl
from art.rhevm_api.tests_lib.high_level import hosts as hl_hosts
from art.rhevm_api.tests_lib.low_level import vms as ll_vms
from art.rhevm_api.tests_lib.low_level import templates as ll_templ
from art.rhevm_api.tests_lib.low_level import disks as ll_disks
from art.rhevm_api.tests_lib.low_level import hosts as ll_hosts

import config

LOGGER = logging.getLogger(__name__)
ENUMS = config.ENUMS
VDSM_CONFIG_FILE = '/etc/vdsm/vdsm.conf'
STORAGE_DOMAIN_API = test_utils.get_api('storage_domain', 'storagedomains')
NFS = ENUMS['storage_type_nfs']
VERSION_30 = '3.0'
VERSION_31 = '3.1'
INTERFACE_VIRTIO = ENUMS['interface_virtio']
DEFAULT_NFS_RETRANS = 6
DEFAULT_NFS_TIMEOUT = 600
DEFAULT_DC_TIMEOUT = 1500


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
    ssh_session = sshConnection.SSHSession(
        hostname=host, username='root', password=password)
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
    LOGGER.info("cmd: %s" % cmd)
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

    LOGGER.info("New vdsm config: %s" % new_config)

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

    @classmethod
    def teardown_class(cls):
        """
        Removes storage domain created in the test. If a test creates anything
        besides storage domains, it should be cleared by the test itself.
        """
        LOGGER.info("Cleanup - removing non-master storage domains")
        datacenter = config.DATA_CENTER_NAME
        storage_domains = STORAGE_DOMAIN_API.get(absLink=False)
        LOGGER.info("All storage domains: %s" %
                    ",".join([x.name for x in storage_domains]))
        non_master_sds = [x for x in storage_domains if not x.get_master()]

        for storage_domain in non_master_sds:
            LOGGER.info("Removing storage domain %s" % storage_domain.name)
            hl_st.remove_storage_domain(
                storage_domain.name, datacenter, config.HOSTS[0], True)

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
            host = config.HOSTS[0]

        if password is None:
            password = config.PASSWORDS[0]

        if datacenter is None:
            datacenter = config.DATA_CENTER_NAME

        for domain in domain_list:
            LOGGER.info("Creating nfs domain %s" % domain.name)
            hl_st.create_nfs_domain_with_options(
                domain.name, domain.sd_type, host, domain.address,
                domain.path, retrans=domain.retrans_to_set,
                version=domain.vers_to_set, timeo=domain.timeout_to_set,
                datacenter=datacenter)

        LOGGER.info("Getting info about mounted resources")
        mounted_resources = ll_st.get_mounted_nfs_resources(host, password)

        LOGGER.info("verifying nfs options")
        for domain in domain_list:
            nfs_timeo, nfs_retrans, nfs_vers = mounted_resources[
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
        LOGGER.info("Creating %s datacenter" % version)
        if not ll_dc.addDataCenter(
                True, name=self.dc_name, storage_type=NFS, version=version):
            self.fail("Adding %s datacenter failed" % self.dc_name)
        LOGGER.info("Datacenter %s was created successfully" % self.dc_name)

        LOGGER.info("Adding cluster to 3.0 datacenter")
        if not ll_cl.addCluster(
                True, name=self.cl_name, version=version, cpu=config.CPU_NAME,
                data_center=self.dc_name):
            self.fail("Adding cluster to datacenter %s failed" % self.dc_name)
        LOGGER.info("Cluster was created successfully")

        LOGGER.info("Adding host to dc %s" % self.dc_name)
        hl_hosts.add_hosts([self.host], [self.password], self.cl_name)
        LOGGER.info("Datacenter %s prepared successfully" % version)


def clean_dc(dc_name, host, cl_name, sd_name=None):
    """ Removes given datacenter, host & cluster, if sd_name is not None,
    removes also given storage domain
    """
    if ll_st.getDCStorages(dc_name, False):  # the easy part
        LOGGER.info("Tear down - removing data center")
        ll_st.cleanDataCenter(True, dc_name)
    else:
        if sd_name is not None:
            LOGGER.info("Tear down - removing storage domain")
            ll_st.removeStorageDomain(True, sd_name, host, 'true')
        LOGGER.info("Tear down - removing data center")
        ll_dc.removeDataCenter(True, dc_name)
        LOGGER.info("Tear down - deactivating host")
        ll_hosts.deactivateHost(True, host)
        LOGGER.info("Tear down - removing host")
        ll_hosts.removeHost(True, host)
        LOGGER.info("Tear down - removing cluster")
        ll_cl.removeCluster(True, cl_name)


class TestCaseStandardOperations(TestCaseNFSOptions):
    """ Base class for tests performing 'standard operations' (see docstring
    of perform_standard_operations for particulars).
    """
    def setUp(self):
        """ Prepares environment - creates storage domains with different
        NFS options, vms, a template etc.

        Don't change to setup_class, as in case setup_class fails,
        teardown_class won't be called (and all later tests will fail)!
        """
        sd_type = ENUMS['storage_dom_type_data']
        datacenter = config.DATA_CENTER_NAME

        hl_st.create_nfs_domain_with_options(
            self.sd_1, sd_type, self.host, config.NFS_ADDRESS[0],
            config.NFS_PATH[0], 'v3', 7, 700, datacenter)
        self.assertTrue(
            ll_st.activateStorageDomain(True, datacenter, self.sd_1))

        hl_st.create_nfs_domain_with_options(
            self.sd_2, sd_type, self.host, config.NFS_ADDRESS[1],
            config.NFS_PATH[1], 'v3', 8, 800, datacenter)
        self.assertTrue(
            ll_st.activateStorageDomain(True, datacenter, self.sd_2))

        hl_st.create_nfs_domain_with_options(
            self.sd_exp, ENUMS['storage_dom_type_export'], self.host,
            config.NFS_ADDRESS[2], config.NFS_PATH[2],
            datacenter=datacenter)
        self.assertTrue(
            ll_st.activateStorageDomain(True, datacenter, self.sd_exp))

        self.assertTrue(ll_disks.addDisk(
            True, alias=self.disk_1, size=config.DISK_SIZE,
            storagedomain=self.sd_1, format=ENUMS['format_raw'],
            interface=INTERFACE_VIRTIO, bootable=True))

        self.assertTrue(ll_disks.addDisk(
            True, alias=self.disk_2, size=config.DISK_SIZE,
            storagedomain=self.sd_1, format=ENUMS['format_raw'],
            interface=INTERFACE_VIRTIO, bootable=True))

        self.assertTrue(ll_vms.addVm(
            True, name=self.vm_1, storagedomain=self.sd_1,
            cluster=config.CLUSTER_NAME))
        self.assertTrue(ll_vms.addVm(
            True, name=self.vm_2, storagedomain=self.sd_1,
            cluster=config.CLUSTER_NAME))

        self.assertTrue(ll_disks.waitForDisksState(
            ",".join([self.disk_1, self.disk_2]), timeout=600))

        self.assertTrue(ll_disks.attachDisk(True, self.disk_1, self.vm_1))
        self.assertTrue(ll_disks.attachDisk(True, self.disk_2, self.vm_2))

        if config.HOST_FOR_30_DC == self.host_2:  # if we don't have more...
            hl_hosts.add_hosts(
                [self.host_2], [config.PASSWORDS[-1]], config.CLUSTER_NAME)

        self.assertTrue(ll_templ.createTemplate(
            True, vm=self.vm_1, name=self.template,
            cluster=config.CLUSTER_NAME))

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
        LOGGER.info("Moving disk %s to %s" % (disk, another_std))
        ll_vms.move_vm_disk(vm_with_disk, disk, another_std)

        LOGGER.info("Moving vm %s to sd %s" % (vm, another_std))
        if not ll_vms.moveVm(True, vm, another_std):
            self.fail(
                "Cannot move vm %s to storage domain %s" % (vm, another_std))

        LOGGER.info("Migrating vm %s" % vm)
        LOGGER.info("Starting vm %s" % vm)
        ll_vms.startVm(True, vm)
        status, host_with_vm = ll_vms.getVmHost(vm)
        host_with_vm = host_with_vm['vmHoster']
        LOGGER.info("Current host: %s" % host_with_vm)
        if not status:
            self.fail("Cannot get host with vm")
        for host in config.HOSTS:
            if host != host_with_vm:
                if not ll_vms.migrateVm(True, vm, host):
                    self.fail("Cannot migrate vm %s to %s" % (vm, host))
                break
        LOGGER.info("Exporting template")
        if not ll_templ.exportTemplate(True, template, export_std, wait=True):
            self.fail(
                "Exporting template %s on %s failed" % (template, export_std))

        LOGGER.info("Changing SPM host")
        old_spm_host = ll_hosts.getSPMHost(config.HOSTS)
        if not ll_hosts.deactivateHost(True, old_spm_host):
            LOGGER.info("Cannot deactivate host %s" % old_spm_host)
        ll_hosts.waitForSPM(config.DATA_CENTER_NAME, 600, 30)
        new_spm_host = ll_hosts.getSPMHost(config.HOSTS)
        LOGGER.info("New SPM host: %s" % new_spm_host)

        LOGGER.info("Getting master storage domain")
        found, master_std = ll_st.findMasterStorageDomain(
            True, config.DATA_CENTER_NAME)
        if not found:
            self.fail("Master storage domain not found")
        master_std = master_std['masterDomain']
        LOGGER.info("Deactivating master storage domain %s" % master_std)
        if not ll_st.deactivateStorageDomain(True, datacenter, master_std):
            self.fail("Cannot deactivate master storage domain")
        found, new_master = ll_st.findMasterStorageDomain(
            True, config.DATA_CENTER_NAME)
        if not found:
            self.fail("New master not found!")
        LOGGER.info("New master: %s" % new_master['masterDomain'])

    @classmethod
    def teardown_class(cls):
        """ Clears everything which won't be cleaned with basic tear down
        Don't add asserts, in case of errors in the test some of the commands
        may fail and it is OK.
        """
        ll_vms.stopVm(True, cls.vm_1)
        ll_vms.waitForVMState(cls.vm_1, 'down')
        ll_hosts.activateHost(True, config.HOSTS[0])
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
        ll_st.activateStorageDomain(True, config.DATA_CENTER_NAME, 'nfs_0')
        ll_st.waitForStorageDomainStatus(
            True, config.DATA_CENTER_NAME, 'nfs_0', 'active',
            timeOut=DEFAULT_DC_TIMEOUT)
        ll_st.deactivateStorageDomain(True, config.DATA_CENTER_NAME, cls.sd_1)
        ll_st.findMasterStorageDomain(True, config.DATA_CENTER_NAME)
        ll_st.deactivateStorageDomain(True, config.DATA_CENTER_NAME, cls.sd_2)
        ll_st.findMasterStorageDomain(True, config.DATA_CENTER_NAME)
        ll_st.deactivateStorageDomain(
            True, config.DATA_CENTER_NAME, cls.sd_exp)
        ll_st.findMasterStorageDomain(True, config.DATA_CENTER_NAME)
        if config.HOST_FOR_30_DC == cls.host_2:  # if we had to use this one...
            ll_hosts.deactivateHost(True, cls.host_2)
            ll_hosts.removeHost(True, cls.host_2)
            # just in case - wait for new SPM host
            ll_hosts.waitForSPM(config.DATA_CENTER_NAME, 600, 30)
        super(TestCaseStandardOperations, cls).teardown_class()
