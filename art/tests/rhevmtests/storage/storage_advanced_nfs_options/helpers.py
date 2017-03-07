"""
Helper functions for advanced NFS options test suite
"""
import ConfigParser
import io
import logging
import os
import tempfile
import time


import config
from art.rhevm_api.tests_lib.high_level import (
    storagedomains as hl_sd,
)
from art.rhevm_api.tests_lib.low_level import (
    clusters as ll_clusters,
    datacenters as ll_dc,
    hosts as ll_hosts,
    storagedomains as ll_sd,
)
from art.rhevm_api.utils import test_utils
from art.test_handler import exceptions
from art.unittest_lib import StorageTest as TestCase
from concurrent.futures import ThreadPoolExecutor
from utilities import sshConnection

logger = logging.getLogger(__name__)
ENUMS = config.ENUMS
VDSM_CONFIG_FILE = '/etc/vdsm/vdsm.conf'
STORAGE_DOMAIN_API = test_utils.get_api('storage_domain', 'storagedomains')
DEFAULT_NFS_RETRANS = 6
DEFAULT_NFS_TIMEOUT = 600
NFS = config.STORAGE_TYPE_NFS


def _verify_one_option(real, expected):
    """ Helper function for verification of one NFS option """
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
    host_ip = ll_hosts.get_host_ip(host)
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
                 "mount_options_to_set", "expected_timeout",
                 "expected_retrans", "expected_vers", "expected_mount_options")

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

        host_ip = ll_hosts.get_host_ip(host)

        if password is None:
            password = config.HOSTS_PW

        if datacenter is None:
            datacenter = config.DATA_CENTER_NAME

        results = list()
        with ThreadPoolExecutor(
            max_workers=len(domain_list)
        ) as executor:
            for domain in domain_list:
                logger.info("Creating nfs domain %s", domain.name)
                results.append(
                    executor.submit(
                        hl_sd.create_nfs_domain_with_options,
                        domain.name, domain.sd_type, host, domain.address,
                        domain.path, retrans=domain.retrans_to_set,
                        version=domain.vers_to_set,
                        timeo=domain.timeout_to_set, datacenter=datacenter
                    )
                )
        for index, result in enumerate(results):
            if result.exception():
                raise result.exception()
            if not result.result:
                raise exceptions.StorageDomainException(
                    "Creation of storage domain %s failed." %
                    domain_list[index]
                )
            logger.info(
                "creation of storage domain %s succeeded", domain_list[index]
            )

        logger.info("Getting info about mounted resources")
        mounted_resources = ll_sd.get_mounted_nfs_resources(host_ip, password)

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
        logger.info("Creating %s data center", version)
        if not ll_dc.addDataCenter(
                True, name=self.dc_name, version=version
        ):
            self.fail("Adding %s data center failed" % self.dc_name)
        logger.info("Datacenter %s was created successfully", self.dc_name)

        logger.info("Adding cluster to the data center")
        if not ll_clusters.addCluster(
                True, name=self.cl_name, version=config.COMP_VERSION,
                cpu=config.CPU_NAME, data_center=self.dc_name
        ):
            self.fail("Adding cluster to data center %s failed" % self.dc_name)
        logger.info("Cluster was created successfully")

        logger.info("Adding host to dc %s", self.dc_name)
        assert ll_hosts.add_host(
            name=self.host_for_dc,
            address=self.host_for_dc,
            root_password=self.password,
            cluster=self.cl_name
        ), "Unable to add host %s to cluster %s" % (
            self.host_for_dc, self.cl_name)
        logger.info("Datacenter %s prepared successfully", version)
