from nose.tools import istest
import logging

from art.test_handler import exceptions
from art.rhevm_api.tests_lib.low_level import datacenters as ll_dc
from art.rhevm_api.tests_lib.low_level import clusters as ll_cl
from art.rhevm_api.tests_lib.high_level import hosts as hl_hosts
from art.rhevm_api.tests_lib.low_level import storagedomains as ll_st
from art.rhevm_api.tests_lib.high_level import storagedomains as hl_st
from art.test_handler.tools import tcms, bz
from art.unittest_lib import attr

import helpers
import config

LOGGER = logging.getLogger(__name__)
ENUMS = helpers.ENUMS


@attr(tier=1)
class TestCase166613(helpers.TestCaseStandardOperations):
    """
    Creates NFS storage domain in 3.1 data center. Then changes settings
    in vdsm.conf and checks that data center functionality works correctly

    https://tcms.engineering.redhat.com/case/166615/?from_plan=5849

    **Author**: Katarzyna Jachim
    """
    __test__ = True
    tcms_plan_id = '5849'
    tcms_test_case = '166613'
    dc_v30_name = 'dc_v30_%s' % tcms_test_case
    cluster_name = 'cluster_%s' % tcms_test_case
    sd_1 = 'test_%s_1' % tcms_test_case
    sd_2 = 'test_%s_2' % tcms_test_case
    sd_exp = 'test_%s_exp' % tcms_test_case
    host = config.HOSTS[0]
    password = config.PASSWORDS[0]
    disk_1 = 'test_%s_disk_1' % tcms_test_case
    disk_2 = 'test_%s_disk_2' % tcms_test_case
    vm_1 = 'vm_%s_1' % tcms_test_case
    vm_2 = 'vm_%s_2' % tcms_test_case
    host_2 = config.HOSTS[1]
    template = 'templ_%s' % tcms_test_case

    def setUp(self):
        """ Creates storage domains with custom advanced NFS options
        """
        self.vdsm_copy_file = None
        super(TestCase166613, self).setUp()

    @istest
    @tcms(tcms_plan_id, tcms_test_case)
    def test_change_vdsm_conf_and_perform_standard_operations(self):
        """ Changes vdsm.conf and checks that datacenter works correctly
        afterwards.
        """
        LOGGER.info("Changing vdsm config")
        changes = {'irs': {'nfs_mount_options': 'soft,nosharecache,retrans=9'}}
        self.vdsm_copy_file = helpers.change_vdsm_config(
            self.host, self.password, changes)
        LOGGER.info("Performing standard operations")
        self.perform_standard_operations(
            self.vm_1, self.vm_2, self.disk_2, self.sd_2, self.template,
            self.sd_exp, config.DATA_CENTER_NAME)

    def tearDown(self):
        """ Restores old vdsm.conf - cleanup of datacenter etc. will be done by
        teardown_class from base class (helpers.TestCaseStandardOperations)
        """
        if self.vdsm_copy_file is not None:
            LOGGER.info("Restoring vdsm config")
            helpers.restore_vdsm_config(
                self.host, self.password, self.vdsm_copy_file)


@attr(tier=1)
class TestCase148672(helpers.TestCaseStandardOperations):
    """
    Tests if data center with NFS storage domains with custom NFS options works
    correctly. Performed operations:
     * moving vm to another storage domain
     * moving vm disk to another storage domain
     * migrating vm to another host
     * exporting template
     * switching SPM
     * reconstruction of master storage domain

    https://tcms.engineering.redhat.com/case/148672/?from_plan=5849

    **Author**: Katarzyna Jachim
    """
    __test__ = True
    tcms_plan_id = '5849'
    tcms_test_case = '148672'
    sd_1 = 'test_%s_1' % tcms_test_case
    sd_2 = 'test_%s_2' % tcms_test_case
    sd_exp = 'test_%s_exp' % tcms_test_case
    host = config.HOSTS[0]
    disk_1 = 'test_%s_disk_1' % tcms_test_case
    disk_2 = 'test_%s_disk_2' % tcms_test_case
    vm_1 = 'vm_%s_1' % tcms_test_case
    vm_2 = 'vm_%s_2' % tcms_test_case
    host_2 = config.HOSTS[1]
    template = 'templ_%s' % tcms_test_case

    @istest
    @tcms(tcms_plan_id, tcms_test_case)
    @bz(996146)
    def test_functionality_with_custom_nfs_options(self):
        """ Tests basic data center functionality with storage domain with
        custom NFS options
        """
        self.perform_standard_operations(
            self.vm_1, self.vm_2, self.disk_2, self.sd_2, self.template,
            self.sd_exp, config.DATA_CENTER_NAME)


@attr(tier=2)
class TestCase166615(helpers.TestCaseNFSOptions):
    """
    Creates NFS storage domain in 3.0 data center. Upgrades data center.
    Checks that after upgrade storage domain is still mounted with default
    options.

    https://tcms.engineering.redhat.com/case/166615/?from_plan=5849

    **Author**: Katarzyna Jachim
    """
    __test__ = True
    tcms_plan_id = '5849'
    tcms_test_case = '166615'
    dc_v30_name = 'dc_v30_%s' % tcms_test_case
    cl_name = 'cluster_%s' % tcms_test_case
    host = config.HOST_FOR_30_DC
    password = config.PASSWORDS[-1]

    @classmethod
    def setup_class(cls):
        """ Creates 3.0 data center, adds cluster & host to it
        """
        LOGGER.info("Creating 3.0 datacenter")
        if not ll_dc.addDataCenter(
                True, name=cls.dc_v30_name, storage_type=helpers.NFS,
                version=helpers.VERSION_30):
            raise exceptions.DataCenterException(
                "Adding 3.0 datacenter failed")
        LOGGER.info("Datacenter 3.0 was created successfully")

        LOGGER.info("Adding cluster to 3.0 datacenter")
        if not ll_cl.addCluster(
                True, name=cls.cl_name, version=helpers.VERSION_30,
                cpu=config.CPU_NAME, data_center=cls.dc_v30_name):
            raise exceptions.ClusterException(
                "Adding cluster to 3.0 datacenter failed")
        LOGGER.info("Cluster was created successfully")

        LOGGER.info("Adding host to 3.0 dc")
        hl_hosts.add_hosts([cls.host], [cls.password], cls.cl_name)

    @istest
    @tcms(tcms_plan_id, tcms_test_case)
    def test_upgrade_datacenter(self):
        """ Creates NFS storage domain in 3.0 data center. Upgrades data center
        to 3.1. Checks that storage domain is still mounted with default
        options.
        """
        address = config.NFS_ADDRESS[0]
        path = config.NFS_PATH[0]
        name = 'test_%s' % self.tcms_test_case

        version = 'v3'  # TODO: fix
        storage = helpers.NFSStorage(
            name=name, address=address, path=path,
            timeout_to_set=None, retrans_to_set=None, vers_to_set=None,
            expected_timeout=helpers.DEFAULT_NFS_TIMEOUT,
            expected_retrans=helpers.DEFAULT_NFS_RETRANS,
            expected_vers=version)

        LOGGER.info("Creating storage domain with options")
        self.create_nfs_domain_and_verify_options(
            [storage], host=self.host, password=self.password,
            datacenter=self.dc_v30_name)

        LOGGER.info("Upgrading cluster")
        if not ll_cl.updateCluster(
                True, self.cl_name, version=helpers.VERSION_31):
            self.fail("Cannot update cluster!")

        LOGGER.info("Upgrading data center")
        if not ll_dc.updateDataCenter(
                True, self.dc_v30_name, version=helpers.VERSION_31):
            self.fail("Upgrading 3.0 datacenter to 3.1 failed!")

        result = ll_st.get_options_of_resource(
            self.host, self.password, address, path)
        if not result:
            self.fail("Resource is not mounted!")
        (timeo, retrans, vers) = result
        result = helpers.verify_nfs_options(
            helpers.DEFAULT_NFS_TIMEOUT, helpers.DEFAULT_NFS_RETRANS, version,
            timeo, retrans, vers)
        if result is not None:
            self.fail("Wrong nfs option %s, expected: %s, real: %s" % result)
        LOGGER.info("Test passed")

    @classmethod
    def teardown_class(cls):
        helpers.clean_dc(cls.dc_v30_name, cls.host, cls.cl_name)
        super(TestCase166615, cls).teardown_class()


@attr(tier=2)
class TestCase148697(helpers.TestCaseNFSOptions):
    """
    Tests checks that
    * storage domain created with custom advanced NFS options cannot be
      attached to 3.0 datacenter
    * storage domain created with custom advanced NFS options after attaching
      to another 3.1+ datacenter preserves its advanced NFS options

    https://tcms.engineering.redhat.com/case/148697/?from_plan=5849

    **Author**: Katarzyna Jachim
    """
    __test__ = True
    tcms_plan_id = '5849'
    tcms_test_case = '148697'
    nfs_retrans = 7
    nfs_timeout = 780
    nfs_version = 'v3'
    sd_name = 'test_%s' % tcms_test_case
    nfs_address = config.NFS_ADDRESS[1]
    nfs_path = config.NFS_PATH[1]

    def setUp(self):
        """ creates storage domain with custom advanced 3.0 options
        """
        LOGGER.info("Creating storage domain with options")
        self.dc_name = None
        self.cl_name = None
        self.host = config.HOST_FOR_30_DC
        self.password = config.PASSWORDS[-1]
        hl_st.create_nfs_domain_with_options(
            self.sd_name, ENUMS['storage_dom_type_data'], config.HOSTS[0],
            self.nfs_address, self.nfs_path, retrans=self.nfs_retrans,
            version=self.nfs_version, timeo=self.nfs_timeout,
            datacenter=config.DATA_CENTER_NAME)

        hl_st.detach_and_deactivate_domain(
            config.DATA_CENTER_NAME, self.sd_name)

    @tcms(tcms_plan_id, tcms_test_case)
    def test_nfs_options_in_30_datacenter(self):
        """ Checks that storage domain with custom NFS options cannot be
        added to 3.0 datacenter
        """
        self.dc_name = "test_%s_30" % self.tcms_test_case
        self.cl_name = "test_%s_30" % self.tcms_test_case
        self.create_dc(helpers.VERSION_30)
        if not ll_st.attachStorageDomain(False, self.dc_name, self.sd_name):
            self.fail("It should be impossible to attach storage domain with "
                      "custom nfs options to 3.0 datacenter")

    @tcms(tcms_plan_id, tcms_test_case)
    def test_nfs_options_in_31_datacenter(self):
        """ Adds storage domain with custom nfs options to 3.1 datacenter
        """
        self.dc_name = "test_%s_31" % self.tcms_test_case
        self.cl_name = "test_%s_31" % self.tcms_test_case
        self.create_dc(helpers.VERSION_31)
        if not ll_st.attachStorageDomain(True, self.dc_name, self.sd_name):
            self.fail("It should be possible to attach storage domain with "
                      "custom nfs options to 3.1 datacenter")
        if not ll_st.waitForStorageDomainStatus(
                True, self.dc_name, self.sd_name, 'active'):
            self.fail("Storage domain is still not active")
        LOGGER.info("Verifying that the NFS options are as expected")
        options = ll_st.get_options_of_resource(
            self.host, self.password, self.nfs_address, self.nfs_path)
        if options is None:
            self.fail("%s:%s is not mounted on %s" % (
                self.nfs_address, self.nfs_path, self.host))
        (timeo, retrans, nfsvers) = options
        result = helpers.verify_nfs_options(
            self.nfs_timeout, self.nfs_retrans, self.nfs_version,
            timeo, retrans, nfsvers)
        if result is not None:
            self.fail(
                "Incorrect NFS option %s, expected: %s, real: %s" % result)
        LOGGER.info("Correct NFS options")

    def tearDown(self):
        """ removes created datacenter
        """
        helpers.clean_dc(self.dc_name, self.host, self.cl_name, self.sd_name)
