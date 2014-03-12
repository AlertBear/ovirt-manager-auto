import logging
from art.unittest_lib import BaseTestCase as TestCase
from art.rhevm_api.tests_lib.high_level import datacenters
from art.rhevm_api.tests_lib.low_level import storagedomains as ll_st_domains
from art.rhevm_api.tests_lib.low_level import vms, templates
from art.rhevm_api.utils.test_utils import restartOvirtEngine, get_api
from art.test_handler.tools import tcms
from utilities.utils import getIpAddressByHostName
import art.test_handler.exceptions as errors
from utilities.machine import Machine

import config


logger = logging.getLogger(__name__)

ENUMS = config.ENUMS
GB = 1024 ** 3


def setup_module():
    """ creates datacenter, adds hosts, clusters, storages according to
        config file
    """
    datacenters.build_setup(
        config=config.PARAMETERS,
        storage=config.PARAMETERS,
        storage_type=config.DATA_CENTER_TYPE,
        basename=config.BASENAME)


def teardown_module():
    """ removes created datacenter, storages etc.
    """
    ll_st_domains.cleanDataCenter(
        True, config.DATA_CENTER_NAME, vdc=config.VDC,
        vdc_password=config.VDC_PASSWORD)


def _create_vm(vm_name, vm_description, disk_interface,
               sparse=True, volume_format=ENUMS['format_cow']):
    """ helper function for creating vm (passes common arguments, mostly taken
    from the configuration file)
    """
    logger.info("Creating VM %s" % vm_name)
    storage_domain_name = ll_st_domains.getDCStorages(
        config.DEFAULT_DATA_CENTER_NAME, False)[0].name
    logger.info("storage domain: %s" % storage_domain_name)
    return vms.createVm(
        True, vm_name, vm_description, cluster=config.CLUSTER_NAME,
        nic=config.HOST_NICS[0], storageDomainName=storage_domain_name,
        size=config.DISK_SIZE, diskType=config.DISK_TYPE_SYSTEM,
        volumeType=sparse, volumeFormat=volume_format,
        diskInterface=disk_interface, memory=GB, cpu_socket=config.CPU_SOCKET,
        cpu_cores=config.CPU_CORES, nicType=config.NIC_TYPE_VIRTIO,
        display_type=config.DISPLAY_TYPE, os_type=config.OS_TYPE,
        user=config.VM_LINUX_USER, password=config.VM_LINUX_PASSWORD,
        type=config.VM_TYPE_DESKTOP, installation=True, slim=True,
        cobblerAddress=config.COBBLER_ADDRESS, cobblerUser=config.COBBLER_USER,
        cobblerPasswd=config.COBBLER_PASSWORD, image=config.COBBLER_PROFILE,
        network=config.MGMT_BRIDGE, useAgent=config.USE_AGENT,
        attempt=3, interval=20)


class TestCase320223(TestCase):
    """
    bug coverage test, restart engine during template creation
    https://tcms.engineering.redhat.com/case/320223/
    """
    __test__ = True
    tcms_plan_id = '5392'
    tcms_test_case = '320223'

    vm_name = "base_vm"
    vm_desc = "VM for creating template"
    template_name = "template_from_%s" % vm_name
    vm_from_template = "vm_from_template"

    @classmethod
    def setup_class(cls):

        if not _create_vm(cls.vm_name, cls.vm_desc, config.INTERFACE_IDE):
            raise errors.VMException("Failed to create vm %s" % cls.vm_name)
        logger.info("Successfully created VM.")

        if not vms.shutdownVm(True, cls.vm_name, async="false"):
            raise errors.VMException("Cannot shutdown vm %s" % cls.vm_name)
        logger.info("Successfully shutdown VM.")

    def _create_template(self):
        logger.info("Creating new template")
        self.assertTrue(templates.createTemplate(positive=True,
                                                 vm=self.vm_name,
                                                 name=self.template_name,
                                                 wait=False),
                        "Failed to create template from vm %s" % self.vm_name)
        logger.info("Successfully created template")

    @tcms(tcms_plan_id, tcms_test_case)
    def test_restart_engine_while_image_lock(self):
        """ test checks if restarting the engine while creating a new template
            (image lock) works properly
        """
        logger.info("Start creating the template")
        self._create_template()

        # Wait until VM becomes lock
        self.assertTrue(vms.waitForVMState(self.vm_name,
                                           state=config.VM_LOCK_STATE),
                        "image status won't change to lock")

        engine = config.VDC
        engine_ip = getIpAddressByHostName(engine)
        engine_object = Machine(
            host=engine_ip,
            user=config.VM_LINUX_USER,
            password=config.VM_LINUX_PASSWORD).util('linux')

        self.assertTrue(restartOvirtEngine(engine_object, 1, 30, 30),
                        "Failed restarting ovirt-engine")
        logger.info("Successfully restarted ovirt-engine")

        # Wait until VM is down
        self.assertTrue(vms.waitForVMState(self.vm_name,
                                           state=config.VM_DOWN_STATE),
                        "image status won't change to down")

        logger.info("starting vm %s", self.vm_name)
        self.assertTrue(vms.startVm(True, self.vm_name),
                        "Failed to start vm %s" % self.vm_name)
        logger.info("Successfully started VM %s", self.vm_name)

        logger.info("wait for template %s - state to be 'ok'",
                    self.template_name)

        self.assertTrue(templates.waitForTemplatesStates(self.template_name),
                        "template %s state is not ok" % self.template_name)
        logger.info("template %s - state is 'ok'",
                    self.template_name)

        logger.info("adding new vm %s from template %s",
                    self.vm_from_template,  self.template_name)
        self.assertTrue(vms.addVm(positive=True,
                                  name=self.vm_from_template,
                                  vmDescription="Server - copy",
                                  cluster=config.CLUSTER_NAME,
                                  template=self.template_name),
                        "Failed to create vm from template %s" %
                        self.template_name)
        logger.info("Successfully created VM from template")

        logger.info("starting vm %s", self.vm_from_template)
        self.assertTrue(vms.startVm(True, self.vm_from_template),
                        "Can't start vm %s" % self.vm_from_template)
        logger.info("Successfully started VM %s", self.vm_from_template)

    @classmethod
    def teardown_class(cls):
        """
        Remove VM's and template
        """
        for vm in [cls.vm_name, cls.vm_from_template]:
            logger.info("Removing vm %s", vm)
            if not vms.removeVm(positive=True, vm=vm, stopVM='true'):
                raise errors.VMException("Cannot remove vm %s" % vm)
            logger.info("Successfully removed %s.", vm)

        logger.info("Removing template %s", cls.template_name)
        if not templates.removeTemplate(positive=True,
                                        template=cls.template_name):
            raise errors.TemplateException("Failed to remove template %s"
                                           % cls.template_name)
        logger.info("Successfully removed %s." % cls.template_name)
