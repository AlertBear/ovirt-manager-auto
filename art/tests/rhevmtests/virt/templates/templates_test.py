"""
Testing inheritance between VMs and templates.
Prerequisites: 1 DC, 1 host, 2 SD (NFS) and 1 export domain.
Every test case creates new template from a VM of given type (Server/Desktop).
Then new VM from this template is checked, if it matches the template type.
"""

from art.unittest_lib import VirtTest as TestCase
import logging

from art.rhevm_api.tests_lib.low_level import vms
from art.rhevm_api.tests_lib.low_level import mla
from art.rhevm_api.tests_lib.low_level import clusters
from art.rhevm_api.tests_lib.low_level import templates
import art.rhevm_api.tests_lib.low_level.storagedomains as sd_api
import art.rhevm_api.tests_lib.low_level.datacenters as dcs

from art.rhevm_api.utils.test_utils import get_api
import art.test_handler.exceptions as errors
from art.test_handler.settings import opts
from art.test_handler.tools import polarion  # pylint: disable=E0611
from random import choice
from rhevmtests.virt import config
from art.unittest_lib import attr

HOST_API = get_api('host', 'hosts')
VM_API = get_api('vm', 'vms')
TEMP_API = get_api('template', 'templates')
CAP_API = get_api('version', 'capabilities')

logger = logging.getLogger(__name__)

ENUMS = opts['elements_conf']['RHEVM Enums']

GB = 1024 * 1024 * 1024
TEMPLATE_VM = 'template_vm'
SERVER = ENUMS['vm_type_server']
DESKTOP = ENUMS['vm_type_desktop']
BLANK = 'Blank'
UNASSIGNED = ENUMS['unassigned']
RHEL6 = ENUMS['rhel6']
ANY_HOST = ENUMS['placement_host_any_host_in_cluster']
MIGRATABLE = ENUMS['vm_affinity_migratable']
USER_MIGRATABLE = ENUMS['vm_affinity_user_migratable']
PINNED = ENUMS['vm_affinity_pinned']
SPICE = ENUMS['display_type_spice']
VNC = ENUMS['display_type_vnc']
BASIC_PARAMETERS = {'name': TEMPLATE_VM, 'cluster': config.CLUSTER_NAME[0]}

########################################################################


@attr(tier=2)
class BaseTemplateClass(TestCase):
    """
    Base class that create vm and template from it
    """
    __test__ = False
    vm_parameters = BASIC_PARAMETERS.copy()
    template_name = None
    vm_name = vm_parameters.get('name')
    master_domain = None
    non_master_domain = None

    @classmethod
    def setup_class(cls):
        """
        Create a server VM and a template
        """
        cls.master_domain = (
            sd_api.get_master_storage_domain_name(config.DC_NAME[0])
        )
        non_master_domains = (
            sd_api.findNonMasterStorageDomains(
                True, config.DC_NAME[0]
            )[1]
        )
        cls.non_master_domain = non_master_domains['nonMasterDomains'][0]
        if not vms.addVm(True, **cls.vm_parameters):
            raise errors.VMException("Cannot create vm %s" % cls.vm_name)
        logger.info("Successfully created VM.")
        if not templates.createTemplate(
                positive=True, vm=cls.vm_name, name=cls.template_name
        ):
            raise errors.TemplateException(
                "Cannot create template from vm %s" % cls.vm_name
            )
        logger.info("Successfully created template.")

    @classmethod
    def teardown_class(cls):
        """
        Remove VM's and template
        """
        if not vms.removeVm(positive=True, vm=cls.vm_name):
            raise errors.VMException("Cannot remove vm %s" % cls.vm_name)
        logger.info("Successfully removed %s.", cls.vm_name)
        if not templates.removeTemplate(
                positive=True, template=cls.template_name
        ):
            raise errors.TemplateException(
                "Cannot remove template %s" % cls.template_name
            )
        logger.info("Successfully removed %s.", cls.template_name)


class BaseTemplateVMClass(BaseTemplateClass):
    """
    Base class that create vm, template from it and vm from template
    """
    __test__ = False
    copy_vm = None

    @classmethod
    def setup_class(cls):
        """
        Create a server VM and a template
        """
        super(BaseTemplateVMClass, cls).setup_class()
        if not vms.addVm(
                positive=True, name=cls.copy_vm,
                cluster=config.CLUSTER_NAME[0], template=cls.template_name
        ):
            raise errors.VMException(
                "Cannot create vm %s from template" % cls.copy_vm
            )
        logger.info("Successfully created VM from template")

    @classmethod
    def teardown_class(cls):
        """
        Remove VM's and template
        """
        if not vms.removeVm(positive=True, vm=cls.copy_vm):
            raise errors.VMException("Cannot remove vm %s" % cls.copy_vm)
        logger.info("Successfully removed %s.", cls.copy_vm)
        super(BaseTemplateVMClass, cls).teardown_class()


class BaseOsTypeTemplate(BaseTemplateVMClass):
    """
    Create vm and template to check os type inheritance
    """
    __test__ = False
    vm_os_type = None
    vm_parameters = BASIC_PARAMETERS.copy()

    @classmethod
    def _check_type_inheritance_template(cls):
        """
        Check template OS type
        """
        template_obj = TEMP_API.find(cls.template_name)
        if not template_obj.get_type() == cls.vm_parameters['type']:
            return False
        return True

    @classmethod
    def _check_type_inheritance_vm(cls):
        """
        Check cloned VM OS type
        """
        vm_obj = VM_API.find(cls.copy_vm)
        if not vm_obj.get_type() == cls.vm_parameters['type']:
            return False
        return True

########################################################################
#                             Test Cases                               #
########################################################################


class VMTypeServer(BaseOsTypeTemplate):
    """
    VM type inheritance: server
    """
    __test__ = True
    vm_parameters = BASIC_PARAMETERS.copy()
    vm_parameters['type'] = 'server'
    template_name = 'server_template'
    copy_vm = 'server_vm'

    @polarion("RHEVM3-5377")
    def test_check_server_inheritance_template(self):
        """
        Check if template type is 'server'
        """
        self.assertTrue(self._check_type_inheritance_template())

    @polarion("RHEVM3-5379")
    def test_check_server_inheritance_vm(self):
        """
        Check if cloned VM type is 'server'
        """
        self.assertTrue(self._check_type_inheritance_vm())

########################################################################


class VMTypeDesktop(BaseOsTypeTemplate):
    """
    VM type inheritance: desktop
    """
    __test__ = True
    vm_parameters = BASIC_PARAMETERS.copy()
    vm_parameters['type'] = 'desktop'
    template_name = 'desktop_template'
    copy_vm = 'desktop_vm'

    @polarion("RHEVM3-5382")
    def test_check_desktop_inheritance_template(self):
        """
        Check if template type is 'desktop'
        """
        self.assertTrue(self._check_type_inheritance_template())

    @polarion("RHEVM3-5383")
    def test_check_desktop_inheritance_vm(self):
        """
        Check if cloned VM type is 'desktop'
        """
        self.assertTrue(self._check_type_inheritance_vm())

########################################################################


class VMMemory(BaseTemplateVMClass):
    """
    Memory inheritance
    """
    __test__ = True
    template_name = 'template_memory'
    copy_vm = 'memory_copy'
    vm_parameters = BASIC_PARAMETERS.copy()

    @classmethod
    def setup_class(cls):
        """
        Create a VM and a template
        """
        # Calculate default number of cores, and give twice as much
        blank_temp = TEMP_API.find(BLANK)
        if blank_temp is not None:
            cls.vm_parameters['memory'] = 2 * blank_temp.get_memory()
        logger.info(
            "Default number of memory is %d", cls.vm_parameters['memory']
        )
        super(VMMemory, cls).setup_class()

    @polarion("RHEVM3-5385")
    def test_check_memory_inheritance_template(self):
        """
        Check if template's memory matches master VM's memory
        """
        template_obj = TEMP_API.find(self.template_name)
        self.assertTrue(template_obj is not None, "Error finding template!")
        logger.info("Expected value is %d", self.vm_parameters['memory'])
        actual_value = int(template_obj.get_memory())
        logger.info("Actual value is %d", actual_value)
        self.assertEqual(
            actual_value, self.vm_parameters['memory'],
            "Template's memory does not match!"
        )
        logger.info("Template's memory matches original VM's memory.")

    @polarion("RHEVM3-5387")
    def test_check_memory_inheritance_vm(self):
        """
        Check if cloned VM's memory matches master VM's memory
        """
        vm_obj = VM_API.find(self.copy_vm)
        self.assertTrue(vm_obj is not None, "Error finding cloned VM!")
        logger.info("Expected value is %d", self.vm_parameters['memory'])
        actual_value = int(vm_obj.get_memory())
        logger.info("Actual value is %d", actual_value)
        self.assertEqual(
            actual_value, self.vm_parameters['memory'],
            "Cloned VM's memory does not match!"
        )
        logger.info("Cloned VM's memory matches original VM's memory.")


########################################################################


class VMCpuTopology(BaseTemplateVMClass):
    """
    CPU topology inheritance
    """
    __test__ = True
    template_name = 'template_cpu_topology'
    copy_vm = 'cpu_topology_copy'
    vm_parameters = BASIC_PARAMETERS.copy()

    @classmethod
    def setup_class(cls):
        """
        Create a VM and a template
        """
        # Calculate default number of cores, and give twice as much
        blank_temp = TEMP_API.find(BLANK)
        if blank_temp is not None:
            topology = blank_temp.get_cpu().get_topology()
            cls.vm_parameters['cpu_socket'] = 2 * int(topology.get_sockets())
            cls.vm_parameters['cpu_cores'] = 2 * int(topology.get_cores())
        logger.info("Number of sockets is %d", cls.vm_parameters['cpu_socket'])
        logger.info("Number of cores is %d", cls.vm_parameters['cpu_cores'])
        super(VMCpuTopology, cls).setup_class()

    @polarion("RHEVM3-5390")
    def test_check_cpu_topology_inheritance_template(self):
        """
        Check if template's CPU topology matches master VM's CPU topology
        """
        template_obj = TEMP_API.find(self.template_name)
        self.assertTrue(template_obj is not None, "Error finding template!")
        logger.info(
            "Expected number of sockets is %d",
            self.vm_parameters['cpu_socket']
        )
        logger.info(
            "Expected number of cores is %d", self.vm_parameters['cpu_cores']
        )
        template_topology = template_obj.get_cpu().get_topology()
        actual_sockets = int(template_topology.get_sockets())
        actual_cores = int(template_topology.get_cores())
        logger.info("Actual number of sockets is %d", actual_sockets)
        logger.info("Actual number of cores is %d", actual_cores)
        self.assertEqual(
            actual_sockets, self.vm_parameters['cpu_socket'],
            "Template's CPU sockets does not match!"
        )
        self.assertEqual(
            actual_cores, self.vm_parameters['cpu_cores'],
            "Template's CPU cores does not match!"
        )
        logger.info(
            "Template's CPU topology matches original VM's CPU topology."
        )

    @polarion("RHEVM3-5392")
    def test_check_cpu_topology_inheritance_vm(self):
        """
        Check if cloned VM's CPU topology matches master VM's CPU topology
        """
        vm_obj = VM_API.find(self.copy_vm)
        self.assertTrue(vm_obj is not None, "Error finding cloned VM!")
        logger.info(
            "Expected number of sockets is %d",
            self.vm_parameters['cpu_socket']
        )
        logger.info(
            "Expected number of cores is %d",
            self.vm_parameters['cpu_cores']
        )
        vm_topology = vm_obj.get_cpu().get_topology()
        actual_sockets = int(vm_topology.get_sockets())
        actual_cores = int(vm_topology.get_cores())
        logger.info("Actual number of sockets is %d", actual_sockets)
        logger.info("Actual number of cores is %d", actual_cores)
        self.assertEqual(
            actual_sockets, self.vm_parameters['cpu_socket'],
            "Cloned VM's CPU sockets does not match!"
        )
        self.assertEqual(
            actual_cores, self.vm_parameters['cpu_cores'],
            "Cloned VM's CPU cores does not match!"
        )
        logger.info(
            "Cloned VM's CPU topology matches original VM's CPU topology."
        )

########################################################################


class VMOs(BaseTemplateVMClass):
    """
    OS inheritance
    """
    __test__ = True
    template_name = 'template_OS'
    copy_vm = 'OS_copy'
    vm_parameters = BASIC_PARAMETERS.copy()
    default_os = UNASSIGNED
    rhel_os = ENUMS['rhel6x64']

    @classmethod
    def setup_class(cls):
        """
        Create a VM and a template
        """
        # Check default OS type
        blank_temp = TEMP_API.find(BLANK)
        if blank_temp is not None:
            cls.default_os = blank_temp.get_os().get_type().lower()
        logger.info("Default OS type is %s", cls.default_os)
        # Set VM os type to rhel_6X64
        cls.vm_parameters['os_type'] = cls.rhel_os
        logger.info(
            "creating vm with OS type: %s", cls.vm_parameters['os_type']
        )
        super(VMOs, cls).setup_class()

    @polarion("RHEVM3-5393")
    def test_check_os_inheritance_template(self):
        """
        Check if template's OS type matches master VM's OS type
        """
        template_obj = TEMP_API.find(self.template_name)
        self.assertTrue(template_obj is not None, "Error finding template!")
        logger.info("Expected OS type is %s", self.vm_parameters['os_type'])
        os = template_obj.get_os().get_type()
        logger.info("Actual OS type is %s", os)
        self.assertEqual(
            os, self.vm_parameters['os_type'],
            "Template's OS type does not match!"
        )
        logger.info("Template's OS type matches original VM's OS type.")

    @polarion("RHEVM3-5395")
    def test_check_os_inheritance_vm(self):
        """
        Check if cloned VM's OS type matches master VM's OS type
        """
        vm_obj = VM_API.find(self.copy_vm)
        self.assertTrue(vm_obj is not None, "Error finding cloned VM!")
        logger.info("Expected OS type is %s", self.vm_parameters['os_type'])
        os = vm_obj.get_os().get_type()
        logger.info("Actual OS type is %s", os)
        self.assertEqual(
            os, self.vm_parameters['os_type'],
            "Cloned VM's OS type does not match!"
        )
        logger.info("Cloned VM's OS type matches original VM's OS type.")

########################################################################


class VMHa(BaseTemplateVMClass):
    """
    HA inheritance
    """
    __test__ = True
    template_name = 'template_HA'
    copy_vm = 'HA_copy'
    vm_parameters = BASIC_PARAMETERS.copy()
    default_ha = False
    priority_default = 0

    @classmethod
    def setup_class(cls):
        """
        Create a VM and a template
        """
        # Check default HA properties
        blank_temp = TEMP_API.find(BLANK)
        if blank_temp is not None:
            cls.default_ha = blank_temp.get_high_availability().get_enabled()
            priority = blank_temp.get_high_availability().get_priority()
            cls.priority_default = int(priority)
        logger.info("Default HA status is %s", cls.default_ha)
        logger.info("Default HA priority is %d", cls.priority_default)
        cls.vm_parameters['highly_available'] = not cls.default_ha
        cls.vm_parameters['availablity_priority'] = 50\
            if cls.priority_default != 50 else 100
        super(VMHa, cls).setup_class()

    @polarion("RHEVM3-5396")
    def test_check_ha_inheritance_template(self):
        """
        Check if template's HA matches master VM's HA
        """
        template_obj = TEMP_API.find(self.template_name)
        self.assertTrue(template_obj is not None, "Error finding template!")
        logger.info(
            "Expected high availability status is %s",
            self.vm_parameters['highly_available']
        )
        logger.info(
            "Expected high availability priority is %d",
            self.vm_parameters['availablity_priority']
        )
        enabled = template_obj.get_high_availability().get_enabled()
        priority = int(template_obj.get_high_availability().get_priority())
        logger.info("Actual high availability status is %s", enabled)
        logger.info("Actual high availability priority is %d", priority)
        self.assertEqual(
            enabled, self.vm_parameters['highly_available'],
            "Template's HA does not match!"
        )
        self.assertEqual(
            priority, self.vm_parameters['availablity_priority'],
            "Template's HA priority does not match!"
        )
        logger.info("Template's HA matches original VM's HA.")

    @polarion("RHEVM3-5397")
    def test_check_ha_inheritance_vm(self):
        """
        Check if cloned VM's HA matches master VM's HA
        """
        vm_obj = VM_API.find(self.copy_vm)
        self.assertTrue(vm_obj is not None, "Error finding cloned VM!")
        logger.info(
            "Expected high availability status is %s",
            self.vm_parameters['highly_available']
        )
        logger.info(
            "Expected high availability priority is %d",
            self.vm_parameters['availablity_priority']
        )
        enabled = vm_obj.get_high_availability().get_enabled()
        priority = int(vm_obj.get_high_availability().get_priority())
        logger.info("Actual high availability status is %s", enabled)
        logger.info("Actual high availability priority is %d", priority)
        self.assertEqual(
            enabled, self.vm_parameters['highly_available'],
            "Cloned VM's HA does not match!"
        )
        self.assertEqual(
            priority, self.vm_parameters['availablity_priority'],
            "Cloned VM's HA priority does not match!"
        )
        logger.info("Cloned VM's HA matches original VM's HA.")

########################################################################


class VMDisplay(BaseTemplateVMClass):
    """
    Display inheritance
    """
    __test__ = True
    template_name = 'template_display'
    copy_vm = 'display_copy'
    vm_parameters = BASIC_PARAMETERS.copy()
    display_default = SPICE

    @classmethod
    def setup_class(cls):
        """
        Create a VM and a template
        """
        # Check default display properties
        blank_temp = TEMP_API.find(BLANK)
        if blank_temp is not None:
            cls.display_default = blank_temp.get_display().get_type()
        logger.info("Default display type is %s", cls.display_default)
        cls.vm_parameters['display_type'] = VNC\
            if cls.display_default == SPICE else SPICE
        super(VMDisplay, cls).setup_class()

    @polarion("RHEVM3-5398")
    def test_check_display_inheritance_template(self):
        """
        Check if template's display type matches master VM's display type
        """
        template_obj = TEMP_API.find(self.template_name)
        self.assertTrue(template_obj is not None, "Error finding template!")
        logger.info(
            "Expected display type is %s",
            self.vm_parameters['display_type']
        )
        display = template_obj.get_display().get_type()
        logger.info("Actual display type is %s" % display)
        self.assertEqual(
            display, self.vm_parameters['display_type'],
            "Template's display type does not match!"
        )
        logger.info("Template's display type matches original VM's HA.")

    @polarion("RHEVM3-5399")
    def test_check_display_inheritance_vm(self):
        """
        Check if cloned VM's display type matches master VM's display type
        """
        vm_obj = VM_API.find(self.copy_vm)
        self.assertTrue(vm_obj is not None, "Error finding cloned VM!")
        logger.info(
            "Expected display type is %s",
            self.vm_parameters['display_type']
        )
        display = vm_obj.get_display().get_type()
        logger.info("Actual display type is %s" % display)
        self.assertEqual(
            display, self.vm_parameters['display_type'],
            "Cloned VM's display type does not match!"
        )
        logger.info("Cloned VM's display type matches original VM's HA.")

########################################################################


class VMStateless(BaseTemplateVMClass):
    """
    Stateless inheritance
    """
    __test__ = True
    template_name = 'template_stateless'
    copy_vm = 'stateless_copy'
    default_stateless = False
    vm_parameters = BASIC_PARAMETERS.copy()

    @classmethod
    def setup_class(cls):
        """
        Create a VM and a template
        """
        # Check default stateless properties
        blank_temp = TEMP_API.find(BLANK)
        if blank_temp is not None:
            cls.default_stateless = blank_temp.get_stateless()
        logger.info("Default stateless status is %s", cls.default_stateless)
        cls.vm_parameters['stateless'] = not cls.default_stateless
        super(VMStateless, cls).setup_class()

    @polarion("RHEVM3-5405")
    def test_check_stateless_inheritance_template(self):
        """
        Check if template's stateless status matches master VM's
        stateless status
        """
        template_obj = TEMP_API.find(self.template_name)
        self.assertTrue(template_obj is not None, "Error finding template!")
        logger.info(
            "Expected stateless status is %s",
            self.vm_parameters['stateless']
        )
        stateless = template_obj.get_stateless()
        logger.info("Actual stateless status is %s", stateless)
        self.assertEqual(
            stateless, self.vm_parameters['stateless'],
            "Template's stateless status does not match!"
        )
        logger.info(
            "Template's stateless status matches original"
            " VM's stateless status."
        )

    @polarion("RHEVM3-5400")
    def test_check_stateless_inheritance_vm(self):
        """
        Check if cloned VM's stateless status matches master VM's
        stateless status
        """
        vm_obj = VM_API.find(self.copy_vm)
        self.assertTrue(vm_obj is not None, "Error finding cloned VM!")
        logger.info(
            "Expected stateless status is %s",
            self.vm_parameters['stateless']
        )
        stateless = vm_obj.get_stateless()
        logger.info("Actual stateless status is %s", stateless)
        self.assertEqual(
            stateless, self.vm_parameters['stateless'],
            "Cloned VM's stateless status does not match!"
        )
        logger.info(
            "Cloned VM's stateless status matches original VM's"
            " stateless status."
        )

########################################################################


class VMDeleteProtection(BaseTemplateVMClass):
    """
    Delete protection inheritance
    """
    __test__ = True
    template_name = 'template_delete_protection'
    copy_vm = 'delete_protection_copy'
    default_protection = False
    vm_parameters = BASIC_PARAMETERS.copy()

    @classmethod
    def setup_class(cls):
        """
        Create a VM and a template
        """
        # Check default delete protection properties
        blank_temp = TEMP_API.find(BLANK)
        if blank_temp is not None:
            cls.default_protection = blank_temp.get_delete_protected()
        logger.info(
            "Default delete protection status is %s", cls.default_protection
        )
        cls.vm_parameters['protected'] = not cls.default_protection
        super(VMDeleteProtection, cls).setup_class()

    @polarion("RHEVM3-5401")
    def test_check_protection_inheritance_template(self):
        """
        Check if template's delete protection status matches master VM's
        delete protection status
        """
        template_obj = TEMP_API.find(self.template_name)
        self.assertTrue(template_obj is not None, "Error finding template!")
        logger.info(
            "Expected delete protection status is %s",
            self.vm_parameters['protected']
        )
        protection = template_obj.get_delete_protected()
        logger.info("Actual delete protection status is %s", protection)
        self.assertEqual(
            protection, self.vm_parameters['protected'],
            "Template's delete protection status does not match!"
        )
        logger.info(
            "Template's delete protection status matches"
            " original VM's delete protection status."
        )

    @polarion("RHEVM3-5402")
    def test_check_protection_inheritance_vm(self):
        """
        Check if cloned VM's delete protection status matches master VM's
        delete protection status
        """
        vm_obj = VM_API.find(self.copy_vm)
        self.assertTrue(vm_obj is not None, "Error finding cloned VM!")
        logger.info(
            "Expected delete protection status is %s",
            self.vm_parameters['protected']
        )
        protection = vm_obj.get_delete_protected()
        logger.info("Actual delete protection status is %s", protection)
        self.assertEqual(
            protection, self.vm_parameters['protected'],
            "Cloned VM's delete protection status does not match"
        )
        logger.info(
            "Cloned VM's delete protection status matches original "
            "VM's delete protection status."
        )

    @classmethod
    def teardown_class(cls):
        """
        Remove VM's and template
        """
        vm_name = cls.vm_parameters.get('name')
        logger.info(
            "Remove protected flag from template %s", cls.template_name
        )
        if not templates.updateTemplate(
                True, cls.template_name, protected=False
        ):
            raise errors.TemplateException("Cannot update template")
        logger.info("Remove protected flag from vm %s", cls.copy_vm)
        if not vms.updateVm(True,   cls.copy_vm, protected=False):
            raise errors.VMException("Cannot update vm %s" % cls.copy_vm)
        logger.info(
            "Successfully removed delete protection from %s.", cls.copy_vm
        )
        logger.info("Remove protected flag from vm %s", vm_name)
        if not vms.updateVm(True, vm_name, protected=False):
            raise errors.VMException("Cannot update vm %s" % vm_name)
        logger.info(
            "Successfully removed delete protection from %s.", vm_name
        )
        super(VMDeleteProtection, cls).teardown_class()

########################################################################


class VMBoot(BaseTemplateVMClass):
    """
    Boot order inheritance
    """
    __test__ = True
    template_name = 'template_boot'
    copy_vm = 'boot_copy'
    default_boot = 'hd'
    vm_parameters = BASIC_PARAMETERS.copy()

    @classmethod
    def setup_class(cls):
        """
        Create a VM and a template
        """
        # Check default boot device
        blank_temp = TEMP_API.find(BLANK)
        if blank_temp is not None:
            cls.default_boot = blank_temp.get_os().get_boot()[0].get_dev()
        logger.info("Default boot device is %s", cls.default_boot)
        cap = CAP_API.get(absLink=False)
        version = config.COMP_VERSION.split('.')
        version_caps = [v for v in cap if str(v.get_major()) == version[0] and
                        str(v.get_minor()) == version[1]][0]
        boot_types = version_caps.get_boot_devices().get_boot_device()
        boot_types.remove(cls.default_boot)
        # Pick a random boot device - doesn't matter which
        # as long as it's not default boot device
        cls.vm_parameters['boot'] = choice(boot_types)
        super(VMBoot, cls).setup_class()

    @polarion("RHEVM3-5403")
    def test_check_boot_inheritance_template(self):
        """
        Check if template's boot device matches master VM's boot device status
        """
        template_obj = TEMP_API.find(self.template_name)
        self.assertTrue(template_obj is not None, "Error finding template!")
        logger.info("Expected boot device is %s", self.vm_parameters['boot'])
        boot = template_obj.get_os().get_boot()[0].get_dev()
        logger.info("Actual boot device is %s", boot)
        self.assertEqual(
            boot, self.vm_parameters['boot'],
            "Template's boot device does not match!"
        )
        logger.info(
            "Template's boot device matches original VM's boot device."
        )

    @polarion("RHEVM3-5404")
    def test_check_boot_inheritance_vm(self):
        """
        Check if cloned VM's boot device matches master VM's boot device
        """
        vm_obj = VM_API.find(self.copy_vm)
        self.assertTrue(vm_obj is not None, "Error finding cloned VM!")
        logger.info("Expected boot device is %s", self.vm_parameters['boot'])
        boot = vm_obj.get_os().get_boot()[0].get_dev()
        logger.info("Actual boot device is %s", boot)
        self.assertEqual(
            boot, self.vm_parameters['boot'],
            "Cloned VM's boot device status does not match!"
        )
        logger.info(
            "Cloned VM's boot device status matches original "
            "VM's boot device."
        )

########################################################################


class VMDomain(BaseTemplateVMClass):
    """
    Check domain inheritance
    """
    __test__ = True
    template_name = 'template_domain'
    copy_vm = 'domain_copy'
    vm_parameters = BASIC_PARAMETERS.copy()
    vm_parameters['domainName'] = config.VDC_ADMIN_DOMAIN

    @polarion("RHEVM3-12274")
    def test_check_domain_inheritance_template(self):
        """
        Check if template's domain name matches master VM's domain name
        """
        template_obj = TEMP_API.find(self.template_name)
        self.assertTrue(template_obj is not None, "Error finding template!")
        logger.info(
            "Expected domain name %s",
            self.vm_parameters['domainName']
        )
        domain_name = template_obj.get_domain().get_name()
        logger.info("Actual domain name is %s", domain_name)
        self.assertEqual(
            domain_name, self.vm_parameters['domainName'],
            "Template's boot device does not match!"
        )
        logger.info(
            "Template's domain name matches original VM's domain name."
        )

    @polarion("RHEVM3-12275")
    def test_check_domain_inheritance_vm(self):
        """
        Check if cloned VM's domain name matches master VM's domain name
        """
        vm_obj = VM_API.find(self.copy_vm)
        self.assertTrue(vm_obj is not None, "Error finding cloned VM!")
        logger.info(
            "Expected domain name is %s", self.vm_parameters['domainName']
        )
        domain_name = vm_obj.get_domain().get_name()
        logger.info("Actual domain name is %s", domain_name)
        self.assertEqual(
            domain_name, self.vm_parameters['domainName'],
            "Cloned VM's domain name does not match!"
        )
        logger.info(
            "Cloned VM's domain name matches original VM's domain name."
        )

########################################################################


class NegativeTemplateCases(BaseTemplateClass):
    """
    Check different negative cases for adding and updating templates
    """
    __test__ = True
    template_name = 'template_negative'
    vm_parameters = BASIC_PARAMETERS.copy()
    vm_name = vm_parameters.get('name')
    cluster_template = 'cluster_template'
    update_template = 'upgrade_template'
    additional_cluster = 'additional_cluster'
    additional_datacenter = 'additional_datacenter'

    @classmethod
    def setup_class(cls):
        """
        Add additional datacenter and cluster
        """
        logger.info(
            "Create additional datacenter %s", cls.additional_datacenter
        )
        if not dcs.addDataCenter(
                True, name=cls.additional_datacenter, local=False,
                version=config.COMP_VERSION
        ):
            raise errors.DataCenterException("Datacenter creation failed")
        logger.info("Add cluster to datacenter %s", cls.additional_cluster)
        if not clusters.addCluster(
                True, name=cls.additional_cluster,
                version=config.COMP_VERSION,
                data_center=cls.additional_datacenter,
                cpu=config.CPU_NAME
        ):
            raise errors.ClusterException("Cluster creation failed")
        super(NegativeTemplateCases, cls).setup_class()

    @polarion("RHEVM3-12276")
    def test_create_template_with_exist_name(self):
        """
        Create new template with name that already exist
        """

        self.assertFalse(
            templates.createTemplate(
                positive=True, vm=self.vm_name, name=self.template_name
            )
        )

    @polarion("RHEVM3-12278")
    def test_create_template_with_wrong_data_center(self):
        """
        Create new template with wrong data center
        """
        logger.info("Add disk to vm %s", self.vm_name)
        if not vms.addDisk(
                True, self.vm_name, GB,
                storagedomain=self.master_domain
        ):
            raise errors.VMException("Failed add disk to vm")
        cluster = self.additional_cluster
        self.assertFalse(
            templates.createTemplate(
                positive=True, vm=self.vm_name, name=self.cluster_template,
                cluster=cluster
            )
        )

    @polarion("RHEVM3-12277")
    def test_update_template_name_to_already_exist(self):
        """
        Update template name to template name that already exist
        """
        if not templates.createTemplate(
                positive=True, vm=self.vm_name,
                name=self.update_template
        ):
            raise errors.TemplateException(
                "Cannot create template from vm %s" % self.vm_name
            )
        self.assertFalse(
            templates.updateTemplate(
                True, self.update_template,  name=self.template_name
            )
        )

    @classmethod
    def teardown_class(cls):
        """
        Remove vms and templates
        """
        logger.info("Remove disk from vm %s", cls.vm_name)
        if not vms.removeDisks(True, cls.vm_name, 1):
            logger.error("Failed to remove disk")
        super(NegativeTemplateCases, cls).teardown_class()
        if templates.check_template_existence(cls.update_template):
            logger.info("Remove template %s", cls.update_template)
            if not templates.removeTemplate(True, cls.update_template):
                raise errors.TemplateException("Failed to remove template")
        logging.info(
            "Remove additional datacenter %s", cls.additional_datacenter
        )
        if not dcs.removeDataCenter(True, cls.additional_datacenter):
            raise errors.DataCenterException("Failed to remove datacenter")
        logging.info(
            "Remove additional cluster %s from datacenter %s",
            cls.additional_cluster, cls.additional_datacenter
        )
        if not clusters.removeCluster(True, cls.additional_cluster):
            raise errors.ClusterException("Failed to remove cluster")

########################################################################


@attr(tier=1)
class BasicTemplate(BaseTemplateClass):
    """
    Create, update, search, remove template and
        also add permissions for template
    """
    __test__ = True
    template_name = 'template'
    vm_parameters = BASIC_PARAMETERS.copy()
    vm_name = vm_parameters.get('name')
    storage_template = 'storage_template'
    update_template = 'upgrade_template'
    group = 'Everyone'

    @attr(tier=2)
    @polarion("RHEVM3-12279")
    def test_specify_template_storage_domain(self):
        """
        Create new template on specific storage domain
        """
        sd = self.non_master_domain
        self.assertTrue(
            templates.createTemplate(
                positive=True, vm=self.vm_name, name=self.storage_template,
                storagedomain=sd
            )
        )

    @polarion("RHEVM3-12280")
    def test_update_template_details(self):
        """
        Update template name, description and cpu
        """
        template_dsc = 'Update template'
        self.assertTrue(
            templates.updateTemplate(
                True, self.template_name, name=self.update_template,
                description=template_dsc, cpu_socket=2, cpu_cores=2
            )
        )

    @polarion("RHEVM3-12281")
    def test_search_for_template(self):
        """
        Search for template
        """
        self.assertTrue(
            templates.searchForTemplate(
                True,
                expected_count=1,
                query_key='name',
                query_val='template',
                key_name='name')
        )

    @polarion("RHEVM3-12282")
    def test_add_template_permissions_to_group(self):
        """
        Add template permissions to group
        """
        self.assertTrue(
            mla.addTemplatePermissionsToGroup(
                True, self.group, self.template_name
            )
        )

    @classmethod
    def teardown_class(cls):
        """
        Update template name back and remove it
        """
        if templates.check_template_existence(cls.storage_template):
            logger.info("Remove template %s", cls.storage_template)
            if not templates.removeTemplate(True, cls.storage_template):
                raise errors.TemplateException("Failed to remove template")
        if templates.check_template_existence(cls.update_template):
            logger.info(
                "Update template %s name to %s", cls.update_template,
                cls.template_name
            )
            if not templates.updateTemplate(
                    True, cls.update_template, name=cls.template_name
            ):
                raise errors.TemplateException("Template update failed")
        super(BasicTemplate, cls).teardown_class()

########################################################################


class ImportExportTemplate(BaseTemplateClass):
    """
    Import and export template test cases
    """
    __test__ = True
    template_name = 'export_template'
    vm_parameters = BASIC_PARAMETERS.copy()
    export_domain = None

    @classmethod
    def setup_class(cls):
        super(ImportExportTemplate, cls).setup_class()
        cls.export_domain = sd_api.findExportStorageDomains(
            config.DC_NAME[0]
        )[0]

    @polarion("RHEVM3-12283")
    def test_import_export_template(self):
        """
        Import and export template
        """
        logger.info("Export template %s", self.template_name)
        self.assertTrue(
            templates.exportTemplate(
                True, self.template_name, self.export_domain
            )
        )
        logger.info(
            "Export template %s and override previous one", self.template_name
        )
        self.assertTrue(
            templates.exportTemplate(
                True, self.template_name, self.export_domain, exclusive=True
            )
        )
        logger.info("Remove template %s to be imported next")
        if not templates.removeTemplate(
                positive=True, template=self.template_name
        ):
            raise errors.TemplateException(
                "Cannot remove template %s" % self.template_name
            )
        logger.info("Import template %s from export domain")
        self.assertTrue(
            templates.import_template(
                True, self.template_name, self.export_domain,
                self.master_domain, config.CLUSTER_NAME[0]
            )
        )

    @classmethod
    def teardown_class(cls):
        super(ImportExportTemplate, cls).teardown_class()
        if templates.export_domain_template_exist(
                cls.template_name, cls.export_domain
        ):
            if not templates.removeTemplateFromExportDomain(
                    True, cls.template_name, config.DC_NAME[0],
                    cls.export_domain
            ):
                raise errors.TemplateException(
                    "Failed to remove template: %s from export domain: %d" %
                    (cls.tempalte_name, cls.export_domain)
                )

#############################################################


class TemplateNic(BaseTemplateClass):
    """
    Add, edit and remove nic from template
    """
    __test__ = True
    template_name = 'nic_template'
    vm_parameters = BASIC_PARAMETERS.copy()
    nic = 'template_nic'
    update_nic = 'update_nic'

    @polarion("RHEVM3-12283")
    def test_template_nic(self):
        """
        Add, edit and remove nic from template
        """
        network = config.MGMT_BRIDGE
        logger.info(
            "Add nic %s to template %s", self.nic, self.template_name
        )
        self.assertTrue(
            templates.addTemplateNic(
                True, self.template_name, name=self.nic, network=network
            )
        )
        logger.info(
            "Update nic %s on template %s", self.nic, self.template_name
        )
        self.assertTrue(
            templates.updateTemplateNic(
                True, self.template_name, self.nic, name=self.update_nic
            )
        )
        logger.info(
            "Remove nic %s from template %s", self.update_nic,
            self.template_name
        )
        self.assertTrue(
            templates.removeTemplateNic(
                True, self.template_name, self.update_nic
            )
        )
