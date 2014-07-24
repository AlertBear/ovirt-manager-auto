#!/usr/bin/env python

__test__ = True

import logging
from rhevmtests.system.user_roles_tests import config
import roles
import art.test_handler.exceptions as errors
from art.test_handler.tools import bz  # pylint: disable=E0611
from nose.tools import istest
from art.unittest_lib import attr
from functools import wraps
from time import sleep
from art.core_api.apis_exceptions import EntityNotFound
from art.unittest_lib import CoreSystemTest as TestCase
from art.rhevm_api.tests_lib.low_level import storagedomains, disks,\
    users, vms, vmpools, templates, mla, datacenters, hosts, networks, clusters
from art.rhevm_api.tests_lib.high_level import storagedomains as h_sd

LOGGER = logging.getLogger(__name__)
GB = config.GB
STRING = 'adsad1ds'
VM_NAME = 'user_actions__vm'
VM_NAME2 = 'user_actions__vm2'
VM_NAME3 = 'user_actions__vm3'
NIC_NAME = 'nic_name1'
NIC_NAME2 = 'nic_name2'
SNAPSHOT_NAME = 'user_actions__snapshot'
SNAPSHOT_NAME2 = 'user_actions__snapshot2'
SNAPSHOT_NAME3 = 'user_actions__snapshot3'
ISO_NAME = 'user_actions__iso'
TEMPLATE_NAME = 'user_actions__template'
VMPOOL_NAME = 'user_actions__vmpool'
VMPOOL_NAME2 = 'user_actions__vmpool2'
DC_NETWORK_NAME = 'dc_net_name'
DC_NETWORK_NAME2 = 'dc_net_name2'
USER_ROLE = 'user_role'
USER_ROLE2 = 'user_role2'
ALT_CLUSTER_NAME = 'alt_cluster_name'
CV = 'compatibility_version'
NEW_CPU = 'Intel Conroe Family'
DETACH_TIMEOUT = 10
MY_HOSTS = [config.MAIN_HOST_NAME, config.ALT1_HOST_ADDRESS]


def setup_module():
    """ Prepare testing setup """
    reload(config)
    global ISO_NAME
    users.addUser(True, user_name=config.USER_NAME, domain=config.USER_DOMAIN)
    h_sd.addNFSDomain(
        config.MAIN_HOST_NAME, config.EXPORT_NAME, config.MAIN_DC_NAME,
        config.EXPORT_ADDRESS, config.EXPORT_PATH, sd_type='export')

    # Import ISO domain
    sdStorage = storagedomains.Storage(type_=mla.ENUMS['storage_type_nfs'],
                                       address=config.ISO_ADDRESS,
                                       path=config.ISO_PATH)
    h = storagedomains.Host(name=config.MAIN_HOST_NAME)

    sd = storagedomains.StorageDomain(type_=mla.ENUMS['storage_dom_type_iso'],
                                      host=h, storage=sdStorage)
    sd, status = storagedomains.util.create(sd, True)
    if status:
        ISO_NAME = sd.get_name()
    storagedomains.attachStorageDomain(True, config.MAIN_DC_NAME, ISO_NAME)
    storagedomains.activateStorageDomain(True, config.MAIN_DC_NAME, ISO_NAME)
    hosts.addHost(True, config.ALT1_HOST_ADDRESS,
                  cluster=config.MAIN_CLUSTER_NAME,
                  root_password=config.ALT1_HOST_ROOT_PASSWORD,
                  address=config.ALT1_HOST_ADDRESS)
    h_sd.addNFSDomain(
        config.MAIN_HOST_NAME, config.ALT1_STORAGE_NAME, config.MAIN_DC_NAME,
        config.ALT1_STORAGE_ADDRESS, config.ALT1_STORAGE_PATH)


def teardown_module():
    users.removeUser(True, config.USER_NAME)


def loginAsUser(filter_=True):
    users.loginAsUser(config.USER_NAME, config.USER_DOMAIN,
                      config.USER_PASSWORD, filter=filter_)


def loginAsAdmin():
    users.loginAsUser(config.VDC_ADMIN_USER, config.VDC_ADMIN_DOMAIN,
                      config.VDC_PASSWORD, filter=False)


def my_ie(method, *args, **kwargs):
    """ Ignore all exceptions """
    try:
        method(*args, **kwargs)
    except:
        pass


def ie(method, *args, **kwargs):
    """
    Try to call method, if method fails, then check if DC is up if everything
    is OK, then try to do call method once again(could be some timeout issue)
    """
    try:
        method(*args, **kwargs)
    except Exception as e:
        LOGGER.warn(e)
        sd_act = storagedomains.is_storage_domain_active(
            config.MAIN_DC_NAME, config.MAIN_STORAGE_NAME)
        if not sd_act:
            LOGGER.info("DC is down, get it up. And try once again.")
            my_ie(storagedomains.deactivateStorageDomain(
                True, config.MAIN_DC_NAME, config.MAIN_STORAGE_NAME))
            my_ie(storagedomains.activateStorageDomain(
                True, config.MAIN_DC_NAME, config.MAIN_STORAGE_NAME))

            # In future, if more hosts there are active, need rewrite to
            # if not hosts.checkHostSpmStatus(
            #     True,
            #     hosts.getSPMHost(MY_HOSTS)
            # ):
            if not hosts.checkHostSpmStatus(True, config.MAIN_HOST_NAME):
                hosts.reactivateHost(True, config.MAIN_HOST_NAME)
            datacenters.waitForDataCenterState(config.MAIN_DC_NAME)
            method(*args, **kwargs)  # Call it once again


def logMe(func):
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        LOGGER.info("%s action group %s",
                    ("POSITIVE" if self.positive else "NEGATIVE"),
                    func.__name__)
        try:
            loginAsUser(self.filter_)
            return func(self, *args, **kwargs)
        finally:
            loginAsAdmin()
    return wrapper


class BaseTest(TestCase):
    __test__ = False
    role = None
    positive = None
    perms = None
    filter_ = None

    @classmethod
    def setUpClass(self):
        users.addRoleToUser(True, config.USER_NAME, self.role)

    @classmethod
    def tearDownClass(self):
        users.removeUser(True, config.USER_NAME)
        users.addUser(True, user_name=config.USER_NAME,
                      domain=config.USER_DOMAIN)


@attr(tier=2)
class Case_vm_basic_operations(BaseTest):
    __test__ = True

    def setUp(self):
        vms.createVm(True, VM_NAME, '',
                     cluster=config.MAIN_CLUSTER_NAME, size=config.GB,
                     storageDomainName=config.MAIN_STORAGE_NAME,
                     network=config.MGMT_BRIDGE)
        vms.createVm(True, VM_NAME2, '',
                     cluster=config.MAIN_CLUSTER_NAME, size=config.GB,
                     storageDomainName=config.MAIN_STORAGE_NAME,
                     network=config.MGMT_BRIDGE)
        mla.addVMPermissionsToUser(True, config.USER_NAME, VM_NAME,
                                   role=self.role)
        mla.addVMPermissionsToUser(True, config.USER_NAME, VM_NAME2,
                                   role=self.role)
        vms.startVm(True, VM_NAME)
        mla.addVMPermissionsToUser(True, config.USER_NAME, VM_NAME,
                                   role=self.role)

    def tearDown(self):
        ie(vms.removeVm, True, VM_NAME, stopVM='true')
        ie(vms.removeVm, True, VM_NAME2, stopVM='true')

    @istest
    @logMe
    def vm_basic_operations(self):
        """ vm_basic_operations """
        self.assertTrue(vms.startVm(self.positive, VM_NAME2))
        self.assertTrue(vms.shutdownVm(self.positive, VM_NAME2))
        self.assertTrue(vms.stopVm(self.positive, VM_NAME))


@attr(tier=2)
class Case_edit_storage_pool_configuration(BaseTest):
    __test__ = True

    def setUp(self):
        datacenters.addDataCenter(True, name=config.DC_NAME_B,
                                  storage_type=config.MAIN_STORAGE_TYPE,
                                  version=config.COMP_VERSION)
        mla.addPermissionsForDataCenter(True, config.USER_NAME,
                                        config.DC_NAME_B, role=self.role)

    def tearDown(self):
        ie(datacenters.removeDataCenter, True, config.DC_NAME_B)
        ie(datacenters.removeDataCenter, True, STRING)

    @istest
    @logMe
    def edit_storage_pool_configuration(self):
        """ edit_storage_pool_configuration """
        self.assertTrue(
            datacenters.updateDataCenter(self.positive, config.DC_NAME_B,
                                         name=STRING, description=STRING))


@attr(tier=2)
class Case_delete_storage_pool(BaseTest):
    __test__ = True

    def setUp(self):
        datacenters.addDataCenter(True, name=config.DC_NAME_B,
                                  storage_type=config.MAIN_STORAGE_TYPE,
                                  version=config.COMP_VERSION)
        mla.addPermissionsForDataCenter(True, config.USER_NAME,
                                        config.DC_NAME_B, role=self.role)

    def tearDown(self):
        ie(datacenters.removeDataCenter, True, config.DC_NAME_B)

    @istest
    @logMe
    def delete_storage_pool(self):
        """ delete_storage_pool """
        self.assertTrue(
            datacenters.removeDataCenter(self.positive, config.DC_NAME_B))


@attr(tier=2)
class Case_connect_to_vm(BaseTest):
    __test__ = True

    def setUp(self):
        vms.createVm(True, VM_NAME, '',
                     cluster=config.MAIN_CLUSTER_NAME, size=config.GB,
                     storageDomainName=config.MAIN_STORAGE_NAME,
                     network=config.MGMT_BRIDGE)
        mla.addVMPermissionsToUser(True, config.USER_NAME, VM_NAME,
                                   role=self.role)
        vms.startVm(True, VM_NAME)
        mla.addVMPermissionsToUser(True, config.USER_NAME, VM_NAME,
                                   role=self.role)

    def tearDown(self):
        ie(vms.removeVm, True, VM_NAME, stopVM='true')

    @istest
    @logMe
    def connect_to_vm(self):
        """ connect_to_vm """
        self.assertTrue(vms.ticketVm(self.positive, VM_NAME, '120'))


@attr(tier=2)
class Case_create_storage_pool(BaseTest):
    __test__ = True

    def tearDown(self):
        ie(datacenters.removeDataCenter, True, config.DC_NAME_B)

    @istest
    @logMe
    def create_storage_pool(self):
        """ create_storage_pool """
        self.assertTrue(
            datacenters.addDataCenter(self.positive, name=config.DC_NAME_B,
                                      storage_type=config.MAIN_STORAGE_TYPE,
                                      version=config.COMP_VERSION))


@attr(tier=2)
class Case_change_vm_custom_properties(BaseTest):
    __test__ = True

    def setUp(self):
        vms.createVm(True, VM_NAME, '',
                     cluster=config.MAIN_CLUSTER_NAME, size=config.GB,
                     storageDomainName=config.MAIN_STORAGE_NAME,
                     network=config.MGMT_BRIDGE)
        mla.addVMPermissionsToUser(True, config.USER_NAME, VM_NAME,
                                   role=self.role)

    def tearDown(self):
        ie(vms.removeVm, True, VM_NAME)

    @istest
    @logMe
    @bz(1091688)
    def change_vm_custom_properties(self):
        """ change_vm_custom_properties """
        self.assertTrue(vms.updateVm(self.positive, VM_NAME,
                                     custom_properties='sndbuf=111'))


@attr(tier=2)
class Case_create_vm(BaseTest):
    __test__ = True

    def tearDown(self):
        ie(vms.removeVm, True, VM_NAME)

    @istest
    @logMe
    def create_vm(self):
        """ create_vm """
        self.assertTrue(vms.createVm(self.positive, VM_NAME, '',
                                     cluster=config.MAIN_CLUSTER_NAME,
                                     network=config.MGMT_BRIDGE))


@attr(tier=2)
class Case_delete_vm(BaseTest):
    __test__ = True

    # FIXME: https://projects.engineering.redhat.com/browse/RHEVM-1727
    apis = BaseTest.apis - set(['cli'])

    def setUp(self):
        vms.createVm(True, VM_NAME, '', cluster=config.MAIN_CLUSTER_NAME,
                     network=config.MGMT_BRIDGE)
        mla.addVMPermissionsToUser(True, config.USER_NAME, VM_NAME,
                                   role=self.role)

    def tearDown(self):
        ie(vms.removeVm, True, VM_NAME)

    @istest
    @logMe
    def delete_vm(self):
        """ delete_vm """
        self.assertTrue(vms.removeVm(self.positive, VM_NAME))


@attr(tier=2)
class Case_edit_vm_properties(BaseTest):
    __test__ = True

    def setUp(self):
        vms.createVm(True, VM_NAME, '', cluster=config.MAIN_CLUSTER_NAME,
                     network=config.MGMT_BRIDGE)
        mla.addVMPermissionsToUser(True, config.USER_NAME, VM_NAME,
                                   role=self.role)

    def tearDown(self):
        ie(vms.removeVm, True, VM_NAME)

    @istest
    @logMe
    @bz(1091688)
    def edit_vm_properties(self):
        """ edit_vm_properties """
        self.assertTrue(vms.updateVm(self.positive, VM_NAME,
                                     memory=3*GB, display_type='vnc',
                                     description=STRING))


@attr(tier=2)
class Case_change_vm_cd(BaseTest):
    __test__ = True

    def setUp(self):
        vms.createVm(True, VM_NAME, '',
                     cluster=config.MAIN_CLUSTER_NAME, size=config.GB,
                     storageDomainName=config.MAIN_STORAGE_NAME,
                     network=config.MGMT_BRIDGE)
        vms.startVm(True, VM_NAME)
        mla.addVMPermissionsToUser(True, config.USER_NAME, VM_NAME,
                                   role=self.role)

    def tearDown(self):
        ie(vms.removeVm, True, VM_NAME, stopVM='true')

    @istest
    @logMe
    def change_vm_cd(self):
        """ change_vm_cd """
        self.assertEqual(vms.changeCDWhileRunning(VM_NAME, config.ISO_FILE),
                         self.positive)


@attr(tier=2)
class Case_import_export_vm(BaseTest):
    __test__ = True

    def setUp(self):
        vms.createVm(True, VM_NAME, '', cluster=config.MAIN_CLUSTER_NAME,
                     network=config.MGMT_BRIDGE)
        vms.exportVm(True, VM_NAME, config.EXPORT_NAME)
        vms.removeVm(True, VM_NAME)
        vms.createVm(True, VM_NAME2, '', cluster=config.MAIN_CLUSTER_NAME,
                     network=config.MGMT_BRIDGE)
        mla.addVMPermissionsToUser(True, config.USER_NAME, VM_NAME2,
                                   role=self.role)

    def tearDown(self):
        ie(vms.removeVm, True, VM_NAME2)
        ie(vms.removeVmFromExportDomain, True, VM_NAME,
           config.MAIN_DC_NAME, config.EXPORT_NAME)
        ie(vms.removeVmFromExportDomain, True, VM_NAME2,
           config.MAIN_DC_NAME, config.EXPORT_NAME)
        ie(vms.removeVm, self.positive, VM_NAME)

    @istest
    @bz(1072773)
    @logMe
    def import_export_vm(self):
        """ import_export_vm """
        self.assertTrue(vms.exportVm(self.positive, VM_NAME2,
                                     config.EXPORT_NAME))
        try:
            self.assertTrue(
                vms.importVm(self.positive, VM_NAME, config.EXPORT_NAME,
                             config.MAIN_STORAGE_NAME,
                             config.MAIN_CLUSTER_NAME))
        except EntityNotFound as e:
            if self.positive:
                raise e


@attr(tier=2)
class Case_configure_vm_network(BaseTest):
    __test__ = True

    def setUp(self):
        vms.createVm(True, VM_NAME, '', cluster=config.MAIN_CLUSTER_NAME,
                     network=config.MGMT_BRIDGE)
        vms.addNic(True, VM_NAME, name=NIC_NAME2,
                   network=config.NETWORK_NAME,
                   interface='virtio')
        mla.addVMPermissionsToUser(True, config.USER_NAME, VM_NAME,
                                   role=self.role)

    def tearDown(self):
        ie(vms.removeVm, True, VM_NAME)

    @istest
    @logMe
    def configure_vm_network(self):
        """ configure_vm_network """
        self.assertTrue(vms.addNic(self.positive, VM_NAME, name=NIC_NAME,
                                   network=config.NETWORK_NAME,
                                   interface='virtio'))
        self.assertTrue(vms.updateNic(self.positive, VM_NAME, NIC_NAME2,
                                      interface='e1000'))
        self.assertTrue(vms.removeNic(self.positive, VM_NAME, NIC_NAME2))


class Case_configure_vm_storage(BaseTest):
    __test__ = True

    def setUp(self):
        vms.createVm(True, VM_NAME, '', cluster=config.MAIN_CLUSTER_NAME,
                     network=config.MGMT_BRIDGE)
        mla.addVMPermissionsToUser(True, config.USER_NAME, VM_NAME,
                                   role=self.role)

    def tearDown(self):
        ie(disks.waitForDisksState, '%s_Disk1' % VM_NAME)
        ie(vms.removeVm, True, VM_NAME)

    @istest
    @logMe
    def configure_vm_storage(self):
        """ configure_vm_storage """
        msg = "configure_vm_storage can't be tested, user has not create_disk"
        if self.positive and 'create_disk' not in self.perms:
            LOGGER.warning(msg)
            return

        self.assertTrue(vms.addDisk(self.positive, VM_NAME, GB,
                                    storagedomain=config.MAIN_STORAGE_NAME))


@attr(tier=2)
class Case_manipulate_vm_snapshots(BaseTest):
    __test__ = True

    def setUp(self):
        for my_vm in [VM_NAME, VM_NAME2, VM_NAME3]:
            vms.createVm(True, my_vm, '',
                         cluster=config.MAIN_CLUSTER_NAME, size=config.GB,
                         storageDomainName=config.MAIN_STORAGE_NAME,
                         network=config.MGMT_BRIDGE)
            vms.addSnapshot(True, my_vm, SNAPSHOT_NAME)
            mla.addVMPermissionsToUser(True, config.USER_NAME, my_vm,
                                       role=self.role)
            vms.waitForDisksStat(my_vm)

    def tearDown(self):
        for my_vm in [VM_NAME, VM_NAME2, VM_NAME3]:
            ie(vms.waitForDisksStat, my_vm)
            ie(vms.removeVm, True, my_vm)

    @istest
    @bz(1002549)
    @logMe
    def manipulate_vm_snapshots(self):
        """ manipulate_vm_snapshots """
        self.assertTrue(vms.addSnapshot(self.positive, VM_NAME,
                                        SNAPSHOT_NAME2))
        self.assertTrue(vms.removeSnapshot(self.positive, VM_NAME2,
                                           SNAPSHOT_NAME))
        self.assertTrue(vms.restoreSnapshot(self.positive, VM_NAME3,
                                            SNAPSHOT_NAME))


@attr(tier=2)
class Case_copy_template(BaseTest):
    __test__ = True

    def setUp(self):
        vms.createVm(True, VM_NAME, '',
                     cluster=config.MAIN_CLUSTER_NAME, size=config.GB,
                     storageDomainName=config.MAIN_STORAGE_NAME,
                     network=config.MGMT_BRIDGE)
        templates.createTemplate(True, vm=VM_NAME,
                                 name=TEMPLATE_NAME)
        vms.removeVm(True, VM_NAME)
        mla.addPermissionsForTemplate(True, config.USER_NAME, TEMPLATE_NAME,
                                      role=self.role)
        h_sd.addNFSDomain(config.MAIN_HOST_NAME, config.ALT1_STORAGE_NAME,
                          config.MAIN_DC_NAME, config.ALT1_STORAGE_ADDRESS,
                          config.ALT1_STORAGE_PATH)
        mla.addStoragePermissionsToUser(True, config.USER_NAME,
                                        config.ALT1_STORAGE_NAME,
                                        role=self.role)
        sleep(15)

    def tearDown(self):
        ie(templates.removeTemplate, True, TEMPLATE_NAME)
        ie(h_sd.remove_storage_domain, config.ALT1_STORAGE_NAME,
           config.MAIN_DC_NAME, config.MAIN_HOST_NAME)

    # @istest
    @logMe
    def copy_template(self):
        """ copy_template """
        LOGGER.warning("Copy_template is deprecated, so user can copy template"
                       " when he has configure_disk_storage permissions.")
        self.positive = self.positive and \
            'configure_disk_storage' in self.perms
        try:
            templates.copyTemplateDisk(TEMPLATE_NAME, '%s_Disk1' % VM_NAME,
                                       config.ALT1_STORAGE_NAME)
        except errors.DiskException as e:
            if self.positive:
                raise e


@attr(tier=2)
class Case_create_template(BaseTest):
    __test__ = True

    def setUp(self):
        vms.createVm(True, VM_NAME, '', config.MAIN_CLUSTER_NAME,
                     network=config.MGMT_BRIDGE)
        mla.addVMPermissionsToUser(True, config.USER_NAME, VM_NAME,
                                   role=roles.role.UserRole)

    def tearDown(self):
        ie(vms.removeVm, True, VM_NAME)
        ie(templates.removeTemplate, True, TEMPLATE_NAME)

    @istest
    @logMe
    def create_template(self):
        """ create_template """
        self.assertTrue(templates.createTemplate(self.positive, vm=VM_NAME,
                                                 name=TEMPLATE_NAME))


@attr(tier=2)
class Case_edit_template_properties(BaseTest):
    __test__ = True

    def setUp(self):
        vms.createVm(True, VM_NAME, '', config.MAIN_CLUSTER_NAME,
                     network=config.MGMT_BRIDGE)
        templates.createTemplate(True, vm=VM_NAME, name=TEMPLATE_NAME)
        mla.addPermissionsForTemplate(True, config.USER_NAME, TEMPLATE_NAME,
                                      role=self.role)

    def tearDown(self):
        ie(vms.removeVm, True, VM_NAME)
        ie(templates.removeTemplate, True, TEMPLATE_NAME)

    @istest
    @logMe
    def edit_template_properties(self):
        """ edit_template_properties """
        self.assertTrue(templates.updateTemplate(self.positive, TEMPLATE_NAME,
                                                 description=STRING,
                                                 memory=3*GB))


@attr(tier=2)
class Case_configure_template_network(BaseTest):
    __test__ = True

    def setUp(self):
        vms.createVm(True, VM_NAME, '', config.MAIN_CLUSTER_NAME,
                     network=config.MGMT_BRIDGE)
        templates.createTemplate(True, vm=VM_NAME, name=TEMPLATE_NAME)
        templates.addTemplateNic(True, TEMPLATE_NAME, name=NIC_NAME2,
                                 network=config.NETWORK_NAME,
                                 interface='virtio')
        mla.addPermissionsForTemplate(True, config.USER_NAME, TEMPLATE_NAME,
                                      role=self.role)

    def tearDown(self):
        ie(vms.removeVm, True, VM_NAME)
        ie(templates.removeTemplate, True, TEMPLATE_NAME)

    @istest
    @logMe
    def configure_template_network(self):
        """ configure_template_network """
        self.assertTrue(templates.addTemplateNic(self.positive, TEMPLATE_NAME,
                                                 name=NIC_NAME,
                                                 network=config.NETWORK_NAME,
                                                 interface='virtio'))
        self.assertTrue(templates.updateTemplateNic(self.positive,
                                                    TEMPLATE_NAME,
                                                    NIC_NAME2,
                                                    interface='e1000'))
        self.assertTrue(templates.removeTemplateNic(self.positive,
                                                    TEMPLATE_NAME,
                                                    NIC_NAME2))


@attr(tier=2)
class Case_create_vm_pool(BaseTest):
    __test__ = True

    def setUp(self):
        vms.createVm(True, VM_NAME, '', config.MAIN_CLUSTER_NAME,
                     network=config.MGMT_BRIDGE)
        templates.createTemplate(True, vm=VM_NAME, name=TEMPLATE_NAME)
        mla.addPermissionsForTemplate(True, config.USER_NAME, TEMPLATE_NAME,
                                      role=self.role)

    def tearDown(self):
        ie(vms.removeVm, True, VM_NAME)
        ie(vmpools.detachVms, True, VMPOOL_NAME)
        sleep(DETACH_TIMEOUT)
        ie(vmpools.removePooledVms, True, VMPOOL_NAME, 1)
        ie(vmpools.removeVmPool, True, VMPOOL_NAME)
        ie(templates.removeTemplate, True, TEMPLATE_NAME)

    @istest
    @logMe
    def create_vm_pool(self):
        """ create_vm_pool """
        self.assertTrue(vmpools.addVmPool(self.positive, name=VMPOOL_NAME,
                                          cluster=config.MAIN_CLUSTER_NAME,
                                          template=TEMPLATE_NAME, size=1))


@attr(tier=2)
class Case_edit_vm_pool_configuration(BaseTest):
    __test__ = True

    def setUp(self):
        vms.createVm(True, VM_NAME, '', config.MAIN_CLUSTER_NAME,
                     os_type='rhel6x64', network=config.MGMT_BRIDGE)
        templates.createTemplate(True, vm=VM_NAME, name=TEMPLATE_NAME)
        vmpools.addVmPool(True, name=VMPOOL_NAME, template=TEMPLATE_NAME,
                          cluster=config.MAIN_CLUSTER_NAME, size=1)
        sleep(DETACH_TIMEOUT)
        vms.waitForVMState('%s%s' % (VMPOOL_NAME, '-1'), 'down')
        mla.addVmPoolPermissionToUser(True, config.USER_NAME,
                                      VMPOOL_NAME, self.role)
        mla.addPermissionsForTemplate(True, config.USER_NAME, TEMPLATE_NAME,
                                      role=self.role)
        mla.addClusterPermissionsToUser(True, config.USER_NAME,
                                        config.MAIN_CLUSTER_NAME,
                                        role=self.role)

    def tearDown(self):
        ie(vms.removeVm, True, VM_NAME)
        ie(vmpools.detachVms, True, VMPOOL_NAME)
        sleep(DETACH_TIMEOUT)
        ie(vmpools.removePooledVms, True, VMPOOL_NAME, 2)
        ie(vmpools.removeVmPool, True, VMPOOL_NAME)
        ie(templates.removeTemplate, True, TEMPLATE_NAME)

    @istest
    @logMe
    @bz(1006884)
    def edit_vm_pool_configuration(self):
        """ edit_vm_pool_configuration """
        try:
            self.assertTrue(
                vmpools.updateVmPool(self.positive, VMPOOL_NAME, size=2))
        except AttributeError:
            if self.positive:
                raise


@attr(tier=2)
class Case_vm_pool_basic_operations(BaseTest):
    __test__ = True

    def setUp(self):
        vms.createVm(True, VM_NAME, '', config.MAIN_CLUSTER_NAME, size=GB,
                     storageDomainName=config.MAIN_STORAGE_NAME,
                     network=config.MGMT_BRIDGE)
        templates.createTemplate(True, vm=VM_NAME, name=TEMPLATE_NAME)
        vmpools.addVmPool(True, name=VMPOOL_NAME, template=TEMPLATE_NAME,
                          cluster=config.MAIN_CLUSTER_NAME, size=1)
        mla.addVmPoolPermissionToUser(True, config.USER_NAME,
                                      VMPOOL_NAME, self.role)
        sleep(DETACH_TIMEOUT)

    def tearDown(self):
        if self.positive:
            ie(vms.waitForVMState, '%s%s' % (VMPOOL_NAME, '-1'), 'powering_up')
        ie(vms.removeVm, True, VM_NAME)
        ie(vmpools.stopVmPool, self.positive, VMPOOL_NAME)
        ie(vmpools.detachVms, True, VMPOOL_NAME)
        sleep(DETACH_TIMEOUT)
        ie(vmpools.removePooledVms, True, VMPOOL_NAME, 1)
        ie(vmpools.removeVmPool, True, VMPOOL_NAME)
        ie(templates.removeTemplate, True, TEMPLATE_NAME)

    @istest
    @logMe
    def vm_pool_basic_operations(self):
        """ vm_pool_basic_operations """
        self.assertTrue(vmpools.allocateVmFromPool(self.positive, VMPOOL_NAME))


@attr(tier=2)
class Case_delete_vm_pool(BaseTest):
    __test__ = True

    def setUp(self):
        vms.createVm(True, VM_NAME, '', config.MAIN_CLUSTER_NAME, size=GB,
                     storageDomainName=config.MAIN_STORAGE_NAME,
                     network=config.MGMT_BRIDGE)
        templates.createTemplate(True, vm=VM_NAME, name=TEMPLATE_NAME)
        vmpools.addVmPool(True, name=VMPOOL_NAME, template=TEMPLATE_NAME,
                          cluster=config.MAIN_CLUSTER_NAME, size=1)
        sleep(DETACH_TIMEOUT)
        vms.waitForVMState('%s%s' % (VMPOOL_NAME, '-1'), 'down')
        vmpools.detachVms(True, VMPOOL_NAME)
        sleep(DETACH_TIMEOUT)
        vmpools.removePooledVms(True, VMPOOL_NAME, 1)
        mla.addVmPoolPermissionToUser(True, config.USER_NAME,
                                      VMPOOL_NAME, self.role)
        vms.removeVm(True, VM_NAME)

    def tearDown(self):
        ie(vmpools.removeVmPool, True, VMPOOL_NAME)
        ie(templates.removeTemplate, True, TEMPLATE_NAME)

    @istest
    @logMe
    def delete_vm_pool(self):
        """ delete_vm_pool """
        try:
            self.assertTrue(vmpools.removeVmPool(self.positive, VMPOOL_NAME))
        except EntityNotFound as e:
            if self.positive:
                raise e


@attr(tier=2)
class Case_delete_template(BaseTest):
    __test__ = True

    def setUp(self):
        vms.createVm(True, VM_NAME, '', config.MAIN_CLUSTER_NAME,
                     network=config.MGMT_BRIDGE)
        templates.createTemplate(True, vm=VM_NAME, name=TEMPLATE_NAME)
        mla.addPermissionsForTemplate(True, config.USER_NAME, TEMPLATE_NAME,
                                      role=self.role)

    def tearDown(self):
        ie(vms.removeVm, True, VM_NAME)
        ie(templates.removeTemplate, True, TEMPLATE_NAME)

    @istest
    @logMe
    def delete_template(self):
        """ delete_template """
        self.assertTrue(templates.removeTemplate(self.positive, TEMPLATE_NAME))


@attr(tier=2)
class Case_manipulate_permissions(BaseTest):
    __test__ = True

    def setUp(self):
        vms.createVm(True, VM_NAME, '', config.MAIN_CLUSTER_NAME,
                     network=config.MGMT_BRIDGE)
        mla.addVMPermissionsToUser(True, config.USER_NAME, VM_NAME,
                                   role=self.role)
        mla.addVMPermissionsToUser(True, config.USER_NAME, VM_NAME,
                                   role=roles.role.UserRole)

    def tearDown(self):
        ie(vms.removeVm, True, VM_NAME)

    @istest
    @logMe
    def manipulate_permissions(self):
        """ manipulate_permissions """
        try:
            self.assertTrue(
                mla.removeUserRoleFromVm(self.positive, VM_NAME, config.USER1,
                                         roles.role.UserRole))
            self.assertTrue(
                mla.addVMPermissionsToUser(self.positive, config.USER_NAME,
                                           VM_NAME, role=roles.role.UserRole))
        except EntityNotFound as e:
            if self.positive:
                raise e


@attr(tier=2)
class Case_create_host(BaseTest):
    __test__ = True

    def setUp(self):
        ie(hosts.deactivateHost, True, config.ALT1_HOST_ADDRESS)
        ie(hosts.removeHost, True, config.ALT1_HOST_ADDRESS)

    def tearDown(self):
        ie(hosts.addHost, True, config.ALT1_HOST_ADDRESS,
           cluster=config.MAIN_CLUSTER_NAME,
           root_password=config.ALT1_HOST_ROOT_PASSWORD,
           address=config.ALT1_HOST_ADDRESS)

    @istest
    @logMe
    def create_host(self):
        """ create_host """
        self.assertTrue(
            hosts.addHost(self.positive, config.ALT1_HOST_ADDRESS,
                          cluster=config.MAIN_CLUSTER_NAME,
                          root_password=config.ALT1_HOST_ROOT_PASSWORD,
                          address=config.ALT1_HOST_ADDRESS))


@attr(tier=2)
class Case_edit_host_configuration(BaseTest):
    __test__ = True

    def setUp(self):
        hosts.deactivateHost(True, config.ALT1_HOST_ADDRESS)

    def tearDown(self):
        ie(hosts.updateHost, True, config.ALT1_HOST_ADDRESS,
           storage_manager_priority='3')
        ie(hosts.activateHost, True, config.ALT1_HOST_ADDRESS)

    @istest
    @logMe
    def edit_host_configuration(self):
        """ edit_host_configuration """
        try:
            self.assertTrue(
                hosts.updateHost(self.positive, config.ALT1_HOST_ADDRESS,
                                 storage_manager_priority='5'))
        except EntityNotFound as e:
            if not self.filter_:
                raise e


@attr(tier=2)
class Case_configure_host_network(BaseTest):
    __test__ = True

    def isMgmtNet(self, nic):
        if nic.get_network() is None:
            return False
        net_id = nic.get_network().get_id()
        if net_id:
            net = networks.NET_API.find(net_id, attribute='id')
        else:
            net = nic.get_network()
        return net.get_name() == networks.MGMT_NETWORK

    def setUp(self):
        self.nic = None
        ie(hosts.deactivateHost(True, config.ALT1_HOST_ADDRESS))
        for nic in hosts.getHostNicsList(config.ALT1_HOST_ADDRESS):
            if nic.get_status().get_state() == 'up' and self.isMgmtNet(nic):
                self.nic = nic.get_name()
                break

    def tearDown(self):
        ie(hosts.updateHostNic, True, config.ALT1_HOST_ADDRESS, self.nic,
           boot_protocol='dhcp', network=networks.MGMT_NETWORK)
        ie(hosts.activateHost, True, config.ALT1_HOST_ADDRESS)

    @istest
    @logMe
    def configure_host_network(self):
        """ configure_host_network """
        try:
            if self.nic is None:
                LOGGER.warning("No active nic on host.")
                return
            self.assertTrue(
                hosts.updateHostNic(self.positive, config.ALT1_HOST_ADDRESS,
                                    self.nic, boot_protocol='static',
                                    network=networks.MGMT_NETWORK))
        except EntityNotFound as e:
            if not self.filter_:
                raise e


@attr(tier=2)
class Case_manipulate_host(BaseTest):
    __test__ = True

    def tearDown(self):
        ie(hosts.activateHost, True, config.ALT1_HOST_ADDRESS)

    @istest
    @logMe
    def manipulate_host(self):
        """ manipulate_host """
        try:
            self.assertTrue(hosts.deactivateHost(self.positive,
                                                 config.ALT1_HOST_ADDRESS))
        except EntityNotFound as e:
            if not self.filter_:
                raise e


@attr(tier=2)
class Case_delete_host(BaseTest):
    __test__ = True

    def setUp(self):
        hosts.deactivateHost(True, config.ALT1_HOST_ADDRESS)

    def tearDown(self):
        ie(hosts.addHost, True, config.ALT1_HOST_ADDRESS,
           cluster=config.MAIN_CLUSTER_NAME,
           root_password=config.ALT1_HOST_ROOT_PASSWORD,
           address=config.ALT1_HOST_ADDRESS)

    @istest
    @logMe
    def delete_host(self):
        """ delete_host """
        try:
            self.assertTrue(
                hosts.removeHost(self.positive, config.ALT1_HOST_ADDRESS))
        except EntityNotFound as e:
            if not self.filter_:
                raise e


@attr(tier=2)
class Case_create_disk(BaseTest):
    __test__ = True

    def tearDown(self):
        ie(disks.waitForDisksState, config.DISK_NAME)
        ie(disks.deleteDisk, True, config.DISK_NAME)
        ie(disks.waitForDisksGone, True, config.DISK_NAME)

    @istest
    @logMe
    def create_disk(self):
        """ create_disk """
        self.assertTrue(
            disks.addDisk(self.positive, alias=config.DISK_NAME,
                          interface='virtio', format='cow',
                          provisioned_size=config.GB,
                          storagedomain=config.MAIN_STORAGE_NAME))


@attr(tier=2)
class Case_attach_disk(BaseTest):
    __test__ = True

    def setUp(self):
        disks.addDisk(True, alias=config.DISK_NAME, interface='virtio',
                      format='cow', provisioned_size=config.GB,
                      storagedomain=config.MAIN_STORAGE_NAME)
        disks.waitForDisksState(config.DISK_NAME)
        vms.createVm(True, VM_NAME, '', cluster=config.MAIN_CLUSTER_NAME,
                     network=config.MGMT_BRIDGE)
        mla.addPermissionsForDisk(True, config.USER_NAME, config.DISK_NAME,
                                  role=self.role)
        mla.addVMPermissionsToUser(True, config.USER_NAME, VM_NAME,
                                   role=self.role)

    def tearDown(self):
        ie(disks.deleteDisk, True, config.DISK_NAME)
        ie(disks.waitForDisksGone, True, config.DISK_NAME)
        ie(vms.removeVm, True, VM_NAME)

    @istest
    @logMe
    def attach_disk(self):
        """ attach_disk """
        self.positive = self.positive and 'configure_vm_storage' in self.perms
        self.assertTrue(
            disks.attachDisk(self.positive, config.DISK_NAME, VM_NAME))


@attr(tier=2)
class Case_edit_disk_properties(BaseTest):
    __test__ = True

    def setUp(self):
        vms.createVm(True, VM_NAME, '',
                     cluster=config.MAIN_CLUSTER_NAME, size=config.GB,
                     storageDomainName=config.MAIN_STORAGE_NAME,
                     network=config.MGMT_BRIDGE)
        mla.addVMPermissionsToUser(True, config.USER_NAME, VM_NAME,
                                   role=self.role)

    def tearDown(self):
        ie(vms.removeVm, True, VM_NAME)

    @istest
    @logMe
    def edit_disk_properties(self):
        """ edit_disk_properties """
        disk_name = '%s_Disk1' % VM_NAME
        self.assertTrue(vms.updateVmDisk(self.positive, VM_NAME, disk_name,
                                         interface='ide'))


@attr(tier=2)
class Case_delete_disk(BaseTest):
    __test__ = True

    def setUp(self):
        disks.addDisk(True, alias=config.DISK_NAME, interface='virtio',
                      format='cow', provisioned_size=config.GB,
                      storagedomain=config.MAIN_STORAGE_NAME)
        disks.waitForDisksState(config.DISK_NAME)
        mla.addPermissionsForDisk(True, config.USER_NAME, config.DISK_NAME,
                                  role=self.role)

    def tearDown(self):
        ie(disks.deleteDisk, True, config.DISK_NAME)
        ie(disks.waitForDisksGone, True, config.DISK_NAME)

    @istest
    @logMe
    def delete_disk(self):
        """ delete_disk """
        self.assertTrue(disks.deleteDisk(self.positive, config.DISK_NAME))


@attr(tier=2)
class Case_create_cluster(BaseTest):
    __test__ = True

    def tearDown(self):
        ie(clusters.removeCluster, True, ALT_CLUSTER_NAME)

    @istest
    @logMe
    def create_cluster(self):
        """ create_cluster """
        self.assertTrue(
            clusters.addCluster(self.positive, name=ALT_CLUSTER_NAME,
                                cpu=config.PARAMETERS.get('cpu_name'),
                                data_center=config.MAIN_DC_NAME,
                                version=config.PARAMETERS.get(CV)))


@attr(tier=2)
class Case_edit_cluster_configuration(BaseTest):
    __test__ = True

    def setUp(self):
        clusters.addCluster(True, name=ALT_CLUSTER_NAME,
                            cpu=config.PARAMETERS.get('cpu_name'),
                            data_center=config.MAIN_DC_NAME,
                            version=config.PARAMETERS.get(CV))

    def tearDown(self):
        ie(clusters.removeCluster, True, ALT_CLUSTER_NAME)

    @istest
    @logMe
    def edit_cluster_configuration(self):
        """ edit_cluster_configuration """
        self.assertTrue(clusters.updateCluster(self.positive, ALT_CLUSTER_NAME,
                                               cpu=NEW_CPU))


@attr(tier=2)
class Case_assign_cluster_network(BaseTest):
    __test__ = True

    def setUp(self):
        clusters.addCluster(True, name=ALT_CLUSTER_NAME,
                            cpu=config.PARAMETERS.get('cpu_name'),
                            data_center=config.MAIN_DC_NAME,
                            version=config.PARAMETERS.get(CV))
        networks.addNetwork(True, name=DC_NETWORK_NAME,
                            data_center=config.MAIN_DC_NAME)
        mla.addPermissionsForVnicProfile(True, config.USER_NAME,
                                         DC_NETWORK_NAME, DC_NETWORK_NAME,
                                         config.MAIN_DC_NAME, role=self.role)
        mla.addClusterPermissionsToUser(True, config.USER_NAME,
                                        config.MAIN_CLUSTER_NAME,
                                        role=self.role)

    def tearDown(self):
        ie(clusters.removeCluster, True, ALT_CLUSTER_NAME)
        ie(networks.removeNetwork, True, DC_NETWORK_NAME,
           data_center=config.MAIN_DC_NAME)

    @istest
    @logMe
    def assign_cluster_network(self):
        """ assign_cluster_network """
        self.assertTrue(
            networks.addNetworkToCluster(self.positive, DC_NETWORK_NAME,
                                         ALT_CLUSTER_NAME))


@attr(tier=2)
class Case_delete_cluster(BaseTest):
    __test__ = True

    def setUp(self):
        clusters.addCluster(True, name=ALT_CLUSTER_NAME,
                            cpu=config.PARAMETERS.get('cpu_name'),
                            data_center=config.MAIN_DC_NAME,
                            version=config.PARAMETERS.get(CV))

    def tearDown(self):
        ie(clusters.removeCluster, True, ALT_CLUSTER_NAME)

    @istest
    @logMe
    def delete_cluster(self):
        """ delete_cluster """
        self.assertTrue(clusters.removeCluster(self.positive,
                                               ALT_CLUSTER_NAME))


@attr(tier=2)
class Case_manipulate_roles(BaseTest):
    __test__ = True

    def setUp(self):
        mla.addRole(True, name=USER_ROLE, permits='login')

    def tearDown(self):
        ie(mla.removeRole, True, USER_ROLE)
        ie(mla.removeRole, True, USER_ROLE2)

    @istest
    @logMe
    def manipulate_roles(self):
        """ manipulate_roles """
        self.assertTrue(mla.addRole(self.positive, name=USER_ROLE2,
                                    permits='login'))
        self.assertTrue(mla.updateRole(self.positive, USER_ROLE,
                                       description=USER_ROLE))
        self.assertTrue(mla.removeRole(self.positive, USER_ROLE))


@attr(tier=2)
class Case_manipulate_users(BaseTest):
    __test__ = True

    def setUp(self):
        users.addUser(True, user_name=config.USER_NAME2,
                      domain=config.USER_DOMAIN)

    def tearDown(self):
        ie(users.removeUser, True, config.USER_NAME2)
        ie(users.removeUser, True, config.USER_NAME3)

    @istest
    @logMe
    def manipulate_users(self):
        """ manipulate_users """
        try:
            users.addUser(self.positive, user_name=config.USER_NAME3,
                          domain=config.USER_DOMAIN)
            users.removeUser(self.positive, config.USER_NAME2)
        except EntityNotFound as e:
            if self.positive:
                raise e


@attr(tier=2)
class Case_create_storage_domain(BaseTest):
    __test__ = True

    def tearDown(self):
        ie(storagedomains.removeStorageDomain, True, config.ALT2_STORAGE_NAME,
           config.MAIN_HOST_NAME, format='true')

    @istest
    @logMe
    def create_storage_domain(self):
        """ create_storage_domain """
        try:
            self.assertTrue(
                storagedomains.addStorageDomain(
                    self.positive, name=config.ALT2_STORAGE_NAME,
                    type=mla.ENUMS['storage_dom_type_data'],
                    storage_type=mla.ENUMS['storage_type_nfs'],
                    host=config.MAIN_HOST_NAME, path=config.ALT2_STORAGE_PATH,
                    address=config.ALT2_STORAGE_ADDRESS))
        except EntityNotFound as e:
            if not self.filter_:
                raise e


@attr(tier=2)
class Case_edit_storage_domain_configuration(BaseTest):
    __test__ = True

    def setUp(self):
        mla.addStoragePermissionsToUser(True, config.USER_NAME,
                                        config.ALT1_STORAGE_NAME,
                                        role=self.role)

    def tearDown(self):
        ie(storagedomains.updateStorageDomain, True, STRING,
            name=config.ALT1_STORAGE_NAME)
        ie(mla.removeUserPermissionsFromSD, True, config.ALT1_STORAGE_NAME,
           config.USER1)

    @istest
    @logMe
    def edit_storage_domain_configuration(self):
        """ edit_storage_domain_configuration """
        self.assertTrue(
            storagedomains.updateStorageDomain(self.positive,
                                               config.ALT1_STORAGE_NAME,
                                               name=STRING))


@attr(tier=2)
class Case_manipulate_storage_domain(BaseTest):
    __test__ = True

    def setUp(self):
        mla.addStoragePermissionsToUser(True, config.USER_NAME,
                                        config.ALT1_STORAGE_NAME,
                                        role=self.role)

    def tearDown(self):
        ie(storagedomains.activateStorageDomain, True, config.MAIN_DC_NAME,
           config.ALT1_STORAGE_NAME)
        ie(mla.removeUserPermissionsFromSD, True, config.ALT1_STORAGE_NAME,
           config.USER1)

    @istest
    @logMe
    def manipulate_storage_domain(self):
        """ manipulate_storage_domain """
        self.assertTrue(
            storagedomains.deactivateStorageDomain(self.positive,
                                                   config.MAIN_DC_NAME,
                                                   config.ALT1_STORAGE_NAME))
        self.assertTrue(
            storagedomains.activateStorageDomain(self.positive,
                                                 config.MAIN_DC_NAME,
                                                 config.ALT1_STORAGE_NAME))


@attr(tier=2)
class Case_delete_storage_domain(BaseTest):
    __test__ = True

    def setUp(self):
        storagedomains.addStorageDomain(
            True, name=config.ALT2_STORAGE_NAME,
            type=mla.ENUMS['storage_dom_type_data'],
            storage_type=mla.ENUMS['storage_type_nfs'],
            host=config.MAIN_HOST_NAME, address=config.ALT2_STORAGE_ADDRESS,
            path=config.ALT2_STORAGE_PATH)
        mla.addStoragePermissionsToUser(True, config.USER_NAME,
                                        config.ALT2_STORAGE_NAME,
                                        role=self.role)

    def tearDown(self):
        ie(storagedomains.removeStorageDomain, True, config.ALT2_STORAGE_NAME,
           config.MAIN_HOST_NAME, format='true')

    @istest
    @logMe
    def delete_storage_domain(self):
        """ delete_storage_domain """
        try:
            self.assertTrue(
                storagedomains.removeStorageDomain(self.positive,
                                                   config.ALT2_STORAGE_NAME,
                                                   config.MAIN_HOST_NAME,
                                                   format='true'))
        except EntityNotFound as e:
            if not self.filter_:
                raise e


@attr(tier=2)
class Case_migrate_vm(BaseTest):
    __test__ = True
    to_host = config.MAIN_HOST_NAME

    def setUp(self):
        vms.createVm(True, VM_NAME, '',
                     cluster=config.MAIN_CLUSTER_NAME, size=config.GB,
                     storageDomainName=config.MAIN_STORAGE_NAME,
                     network=config.MGMT_BRIDGE)
        vms.startVm(True, VM_NAME)
        mla.addVMPermissionsToUser(True, config.USER_NAME, VM_NAME,
                                   role=self.role)
        h_name = vms.getVmHost(VM_NAME)[1]['vmHoster']
        if h_name == config.MAIN_HOST_NAME:
            self.to_host = config.ALT1_HOST_ADDRESS

    def tearDown(self):
        ie(vms.removeVm, True, VM_NAME, stopVM='true')

    @istest
    @logMe
    def migrate_vm(self):
        """ migrate_vm """
        if not self.positive:
            self.assertFalse(vms.migrateVm(True, VM_NAME,
                                           self.to_host))
        else:
            self.assertTrue(vms.migrateVm(True, VM_NAME,
                                          self.to_host))


@attr(tier=2)
class Case_configure_storage_pool_network(BaseTest):
    __test__ = True

    def setUp(self):
        networks.addNetwork(True, name=DC_NETWORK_NAME,
                            data_center=config.MAIN_DC_NAME)
        mla.addPermissionsForVnicProfile(True, config.USER_NAME,
                                         DC_NETWORK_NAME, DC_NETWORK_NAME,
                                         config.MAIN_DC_NAME, role=self.role)

    def tearDown(self):
        ie(networks.removeNetwork, True, DC_NETWORK_NAME,
           data_center=config.MAIN_DC_NAME)
        ie(networks.removeNetwork, True, DC_NETWORK_NAME2,
           data_center=config.MAIN_DC_NAME)

    @istest
    @logMe
    def configure_storage_pool_network(self):
        """ configure_storage_pool_network """
        self.assertTrue(
            networks.addNetwork(self.positive, name=DC_NETWORK_NAME2,
                                data_center=config.MAIN_DC_NAME))
        self.assertTrue(
            networks.removeNetwork(self.positive, DC_NETWORK_NAME,
                                   data_center=config.MAIN_DC_NAME))
