"""
Testing inheritance between VMs and templates.
Prerequisites: 1 DC, 1 host, 1 SD (NFS).
Every test case creates new template from a VM of given type (Server/Desktop).
Then new VM from this template is checked, if it matches the template type.
"""

from nose.tools import istest
from unittest import TestCase
import logging

import art.rhevm_api.tests_lib.low_level.vms as vms
import art.rhevm_api.tests_lib.low_level.templates as templates

from art.rhevm_api.utils.test_utils import get_api
import art.test_handler.exceptions as errors
from art.test_handler.settings import opts
from art.test_handler.tools import tcms
from random import choice
import config

HOST_API = get_api('host', 'hosts')
VM_API = get_api('vm', 'vms')
TEMP_API = get_api('template', 'templates')
CAP_API = get_api('version', 'capabilities')

logger = logging.getLogger(__package__ + __name__)

ENUMS = opts['elements_conf']['RHEVM Enums']

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

########################################################################


class VMTypeTestCase(TestCase):
    '''
    Base class for VM type tests
    '''
    __test__ = False

    @classmethod
    def setup_class(cls):
        '''
        Create a server VM and a template
        '''
        if not vms.addVm(positive=True, name=cls.master_name,
                         vmDescription=cls.master_desc,
                         cluster=config.cluster_name,
                         type=cls.vm_type):
            raise errors.VMException("Cannot create vm %s" % cls.master_name)
        logger.info("Successfully created VM.")
        if not templates.createTemplate(positive=True, vm=cls.master_name,
                                        name=cls.template_name):
            raise errors.TemplateException("Cannot create template from "
                                           "vm %s" % cls.master_name)
        logger.info("Successfully created template.")
        if not vms.addVm(positive=True, name=cls.copy_name,
                         vmDescription="Server - copy",
                         cluster=config.cluster_name,
                         template=cls.template_name):
            raise errors.VMException("Cannot create vm %s from template"
                                     % cls.copy_name)
        logger.info("Successfully created VM from template")

    def _check_obj_type(self, obj, expected_type):
        '''
        '''
        logger.info("Expected value is %s" % self.vm_type)
        actual_type = obj.get_type()
        logger.info("Actual value is %s" % actual_type)
        return actual_type == self.vm_type

    @classmethod
    def teardown_class(cls):
        '''
        Remove VM's and template
        '''
        if not vms.removeVm(positive=True, vm=cls.master_name):
            raise errors.VMException("Cannot remove vm %s" % cls.master_name)
        logger.info("Successfully removed %s." % cls.master_name)
        if not vms.removeVm(positive=True, vm=cls.copy_name):
            raise errors.VMException("Cannot remove vm %s" % cls.copy_name)
        logger.info("Successfully removed %s." % cls.copy_name)
        if not templates.removeTemplate(positive=True,
                                        template=cls.template_name):
            raise errors.TemplateException("Cannot remove template %s"
                                           % cls.template_name)
        logger.info("Successfully removed %s." % cls.template_name)

########################################################################
#                             Test Cases                               #
########################################################################


class VMTypeServer(VMTypeTestCase):
    """
    VM type inheritance: server
    """
    __test__ = True
    master_name = "vm_type_server_master"
    master_desc = "Server - master"
    template_name = "template_type_server"
    copy_name = "vm_type_server_copy"
    copy_spec = "Server - copy"
    vm_type = SERVER

    @istest
    @tcms('9798', '284040')
    def check_server_inheritance_template(self):
        """
        Check if template type is 'server'
        """
        template_obj = TEMP_API.find(self.template_name)
        self.assertTrue(template_obj is not None, "Error finding template!")
        self.assertTrue(self._check_obj_type(template_obj, self.vm_type),
                        "Template type does not match!")
        logger.info("Template type matches original VM type.")

    @istest
    @tcms('9798', '284041')
    def check_server_inheritance_vm(self):
        """
        Check if cloned VM type is 'server'
        """
        vm_obj = VM_API.find(self.copy_name)
        self.assertTrue(vm_obj is not None, "Error finding cloned VM!")
        self.assertTrue(self._check_obj_type(vm_obj, self.vm_type),
                        "VM type does not match!")
        logger.info("VM type matches original VM type.")

########################################################################


class VMTypeDesktop(VMTypeTestCase):
    """
    VM type inheritance: desktop
    """
    __test__ = True
    master_name = "vm_type_desktop_master"
    master_desc = "Desktop - master"
    template_name = "template_type_desktop"
    copy_name = "vm_type_desktop_copy"
    copy_spec = "Desktop - copy"
    vm_type = DESKTOP

    @istest
    @tcms('9798', '284042')
    def check_desktop_inheritance_template(self):
        """
        Check if template type is 'desktop'
        """
        template_obj = TEMP_API.find(self.template_name)
        self.assertTrue(template_obj is not None, "Error finding template!")
        self.assertTrue(self._check_obj_type(template_obj, self.vm_type),
                        "Template type does not match!")
        logger.info("Template type matches original VM type.")

    @istest
    @tcms('9798', '284043')
    def check_desktop_inheritance_vm(self):
        """
        Check if cloned VM type is 'server'
        """
        vm_obj = VM_API.find(self.copy_name)
        self.assertTrue(vm_obj is not None, "Error finding cloned VM!")
        self.assertTrue(self._check_obj_type(vm_obj, self.vm_type),
                        "VM type does not match!")
        logger.info("VM type matches original VM type.")

########################################################################


class VMMemory(TestCase):
    """
    Memory inheritance
    """
    __test__ = True
    master_name = "memory_master"
    template_name = "template_memory"
    copy_name = "memory_copy"
    default_mem = 512 * 1024 * 1024

    @classmethod
    def setup_class(cls):
        '''
        Create a VM and a template
        '''
        # Calculate default memory, and give twice as much
        blank_temp = TEMP_API.find(BLANK)
        if blank_temp is not None:
            cls.default_mem = int(blank_temp.get_memory())
        logger.info("Default memory is %d" % cls.default_mem)
        if not vms.addVm(positive=True, name=cls.master_name,
                         vmDescription="Memory - master",
                         cluster=config.cluster_name,
                         memory=cls.default_mem * 2):
            raise errors.VMException("Cannot create vm %s" % cls.master_name)
        logger.info("Successfully created VM with twice as much memory.")
        if not templates.createTemplate(positive=True, vm=cls.master_name,
                                        name=cls.template_name):
            raise errors.TemplateException("Cannot create template from "
                                           "vm %s" % cls.master_name)
        logger.info("Successfully created template.")
        if not vms.addVm(positive=True, name=cls.copy_name,
                         vmDescription="Memory - copy",
                         cluster=config.cluster_name,
                         template=cls.template_name):
            raise errors.VMException("Cannot create vm %s from template"
                                     % cls.copy_name)
        logger.info("Successfully created VM from template")

    @istest
    @tcms('9798', '284044')
    def check_memory_inheritance_template(self):
        """
        Check if template's memory matches master VM's memory
        """
        template_obj = TEMP_API.find(self.template_name)
        self.assertTrue(template_obj is not None, "Error finding template!")
        logger.info("Expected value is %d" % (2 * self.default_mem))
        actual_value = int(template_obj.get_memory())
        logger.info("Actual value is %d" % actual_value)
        self.assertTrue(actual_value == 2 * self.default_mem,
                        "Template's memory does not match!")
        logger.info("Template's memory matches original VM's memory.")

    @istest
    @tcms('9798', '284045')
    def check_memory_inheritance_vm(self):
        """
        Check if cloned VM's memory matches master VM's memory
        """
        vm_obj = VM_API.find(self.copy_name)
        self.assertTrue(vm_obj is not None, "Error finding cloned VM!")
        logger.info("Expected value is %d" % (2 * self.default_mem))
        actual_value = int(vm_obj.get_memory())
        logger.info("Actual value is %d" % actual_value)
        self.assertTrue(actual_value == 2 * self.default_mem,
                        "Cloned VM's memory does not match!")
        logger.info("Cloned VM's memory matches original VM's memory.")

    @classmethod
    def teardown_class(cls):
        '''
        Remove VM's and template
        '''
        if not vms.removeVm(positive=True, vm=cls.master_name):
            raise errors.VMException("Cannot remove vm %s" % cls.master_name)
        logger.info("Successfully removed %s." % cls.master_name)
        if not vms.removeVm(positive=True, vm=cls.copy_name):
            raise errors.VMException("Cannot remove vm %s" % cls.copy_name)
        logger.info("Successfully removed %s." % cls.copy_name)
        if not templates.removeTemplate(positive=True,
                                        template=cls.template_name):
            raise errors.TemplateException("Cannot remove template %s"
                                           % cls.template_name)
        logger.info("Successfully removed %s." % cls.template_name)

########################################################################


class VMCpuTopology(TestCase):
    """
    CPU topology inheritance
    """
    __test__ = True
    master_name = "cpu_topology_master"
    template_name = "template_cpu_topology"
    copy_name = "cpu_topology_copy"
    default_sockets = 1
    default_cores = 1

    @classmethod
    def setup_class(cls):
        '''
        Create a VM and a template
        '''
        # Calculate default number of cores, and give twice as much
        blank_temp = TEMP_API.find(BLANK)
        if blank_temp is not None:
            topology = blank_temp.get_cpu().get_topology()
            cls.default_sockets = int(topology.get_sockets())
            cls.default_cores = int(topology.get_cores())
        logger.info("Default number of sockets is %d" % cls.default_sockets)
        logger.info("Default number of cores is %d" % cls.default_cores)
        if not vms.addVm(positive=True, name=cls.master_name,
                         vmDescription="CPU topology - master",
                         cluster=config.cluster_name,
                         cpu_socket=cls.default_sockets * 2,
                         cpu_cores=cls.default_cores * 2):
            raise errors.VMException("Cannot create vm %s" % cls.master_name)
        logger.info("Successfully created VM with twice as much sockets and "
                    "cores.")
        if not templates.createTemplate(positive=True, vm=cls.master_name,
                                        name=cls.template_name):
            raise errors.TemplateException("Cannot create template from "
                                           "vm %s" % cls.master_name)
        logger.info("Successfully created template.")
        if not vms.addVm(positive=True, name=cls.copy_name,
                         vmDescription="CPU topology - copy",
                         cluster=config.cluster_name,
                         template=cls.template_name):
            raise errors.VMException("Cannot create vm %s from template"
                                     % cls.copy_name)
        logger.info("Successfully created VM from template")

    @istest
    @tcms('9798', '284046')
    def check_cpu_topology_inheritance_template(self):
        """
        Check if template's CPU topology matches master VM's CPU topology
        """
        template_obj = TEMP_API.find(self.template_name)
        self.assertTrue(template_obj is not None, "Error finding template!")
        logger.info("Expected number of sockets is %d"\
                    % (2 * self.default_sockets))
        logger.info("Expected number of cores is %d"\
                    % (2 * self.default_cores))
        topology = template_obj.get_cpu().get_topology()
        actual_sockets = int(topology.get_sockets())
        actual_cores = int(topology.get_cores())
        logger.info("Actual number of sockets is %d" % actual_sockets)
        logger.info("Actual number of cores is %d" % actual_cores)
        self.assertTrue(actual_sockets == 2 * self.default_sockets
                        and
                        actual_cores == 2 * self.default_cores,
                        "Template's CPU topology does not match!")
        logger.info("Template's CPU topology matches original VM's CPU"
                    " topology.")

    @istest
    @tcms('9798', '284047')
    def check_cpu_topology_inheritance_vm(self):
        """
        Check if cloned VM's CPU topology matches master VM's CPU topology
        """
        vm_obj = VM_API.find(self.copy_name)
        self.assertTrue(vm_obj is not None, "Error finding cloned VM!")
        logger.info("Expected number of sockets is %d"\
                    % (2 * self.default_sockets))
        logger.info("Expected number of cores is %d"\
                    % (2 * self.default_cores))
        topology = vm_obj.get_cpu().get_topology()
        actual_sockets = int(topology.get_sockets())
        actual_cores = int(topology.get_cores())
        logger.info("Actual number of sockets is %d" % actual_sockets)
        logger.info("Actual number of cores is %d" % actual_cores)
        self.assertTrue(actual_sockets == 2 * self.default_sockets
                        and
                        actual_cores == 2 * self.default_cores,
                        "Cloned VM's CPU topology does not match!")
        logger.info("Cloned VM's CPU topology matches original VM's CPU"
                    " topology.")

    @classmethod
    def teardown_class(cls):
        '''
        Remove VM's and template
        '''
        if not vms.removeVm(positive=True, vm=cls.master_name):
            raise errors.VMException("Cannot remove vm %s" % cls.master_name)
        logger.info("Successfully removed %s." % cls.master_name)
        if not vms.removeVm(positive=True, vm=cls.copy_name):
            raise errors.VMException("Cannot remove vm %s" % cls.copy_name)
        logger.info("Successfully removed %s." % cls.copy_name)
        if not templates.removeTemplate(positive=True,
                                        template=cls.template_name):
            raise errors.TemplateException("Cannot remove template %s"
                                           % cls.template_name)
        logger.info("Successfully removed %s." % cls.template_name)

########################################################################


class VMOs(TestCase):
    """
    OS inheritance
    """
    __test__ = True
    master_name = "OS_master"
    template_name = "template_OS"
    copy_name = "OS_copy"
    default_os = UNASSIGNED
    target_os = RHEL6

    @classmethod
    def setup_class(cls):
        '''
        Create a VM and a template
        '''
        # Check default OS type
        blank_temp = TEMP_API.find(BLANK)
        if blank_temp is not None:
            cls.default_os = blank_temp.get_os().get_type()
        logger.info("Default OS type is %s" % cls.default_os)
        # Get list of all possible OS types, and exclude default
        cap = CAP_API.get(absLink=False)
        version = config.version.split('.')
        version_caps = [v for v in cap if str(v.get_major()) == version[0] and
                        str(v.get_minor()) == version[1]][0]
        os_types = version_caps.get_os_types().get_os_type()
        os_types.remove(cls.default_os)
        # Pick a random OS type - doesn't matter which
        # as long as it's not default OS
        cls.target_os = choice(os_types)
        if not vms.addVm(positive=True, name=cls.master_name,
                         vmDescription="OS - master",
                         cluster=config.cluster_name,
                         os_type=cls.target_os):
            raise errors.VMException("Cannot create vm %s" % cls.master_name)
        logger.info("Successfully created VM.")
        if not templates.createTemplate(positive=True, vm=cls.master_name,
                                        name=cls.template_name):
            raise errors.TemplateException("Cannot create template from "
                                           "vm %s" % cls.master_name)
        logger.info("Successfully created template.")
        if not vms.addVm(positive=True, name=cls.copy_name,
                         vmDescription="OS - copy",
                         cluster=config.cluster_name,
                         template=cls.template_name):
            raise errors.VMException("Cannot create vm %s from template"
                                     % cls.copy_name)
        logger.info("Successfully created VM from template")

    @istest
    @tcms('9798', '284048')
    def check_os_inheritance_template(self):
        """
        Check if template's OS type matches master VM's OS type
        """
        template_obj = TEMP_API.find(self.template_name)
        self.assertTrue(template_obj is not None, "Error finding template!")
        logger.info("Expected OS type is %s" % self.target_os)
        os = template_obj.get_os().get_type()
        logger.info("Actual OS type is %s" % os)
        self.assertTrue(os == self.target_os,
                        "Template's OS type does not match!")
        logger.info("Template's OS type matches original VM's OS type.")

    @istest
    @tcms('9798', '284049')
    def check_os_inheritance_vm(self):
        """
        Check if cloned VM's OS type matches master VM's OS type
        """
        vm_obj = VM_API.find(self.copy_name)
        self.assertTrue(vm_obj is not None, "Error finding cloned VM!")
        logger.info("Expected OS type is %s" % self.target_os)
        os = vm_obj.get_os().get_type()
        logger.info("Actual OS type is %s" % os)
        self.assertTrue(os == self.target_os,
                        "Cloned VM's OS type does not match!")
        logger.info("Cloned VM's OS type matches original VM's OS type.")

    @classmethod
    def teardown_class(cls):
        '''
        Remove VM's and template
        '''
        if not vms.removeVm(positive=True, vm=cls.master_name):
            raise errors.VMException("Cannot remove vm %s" % cls.master_name)
        logger.info("Successfully removed %s." % cls.master_name)
        if not vms.removeVm(positive=True, vm=cls.copy_name):
            raise errors.VMException("Cannot remove vm %s" % cls.copy_name)
        logger.info("Successfully removed %s." % cls.copy_name)
        if not templates.removeTemplate(positive=True,
                                        template=cls.template_name):
            raise errors.TemplateException("Cannot remove template %s"
                                           % cls.template_name)
        logger.info("Successfully removed %s." % cls.template_name)

########################################################################


class VMHa(TestCase):
    """
    HA inheritance
    """
    __test__ = True
    master_name = "HA_master"
    template_name = "template_HA"
    copy_name = "HA_copy"
    default_HA = False
    priority_default = 0
    target_priority = 50
    target_HA = True

    @classmethod
    def setup_class(cls):
        '''
        Create a VM and a template
        '''
        # Check default HA properties
        blank_temp = TEMP_API.find(BLANK)
        if blank_temp is not None:
            cls.default_HA = blank_temp.get_high_availability().get_enabled()
            priority = blank_temp.get_high_availability().get_priority()
            cls.priority_default = int(priority)
        logger.info("Default HA status is %s" % cls.default_HA)
        logger.info("Default HA priority is %d" % cls.priority_default)
        cls.target_HA = True if cls.default_HA == False else False
        cls.target_priority = 50 if cls.priority_default != 50 else 100
        if not vms.addVm(positive=True, name=cls.master_name,
                         vmDescription="HA - master",
                         type=SERVER, cluster=config.cluster_name,
                         highly_available=cls.target_HA,
                         availablity_priority=cls.target_priority):
            raise errors.VMException("Cannot create vm %s" % cls.master_name)
        logger.info("Successfully created VM.")
        if not templates.createTemplate(positive=True, vm=cls.master_name,
                                        name=cls.template_name):
            raise errors.TemplateException("Cannot create template from "
                                           "vm %s" % cls.master_name)
        logger.info("Successfully created template.")
        if not vms.addVm(positive=True, name=cls.copy_name,
                         vmDescription="HA - copy",
                         cluster=config.cluster_name,
                         template=cls.template_name):
            raise errors.VMException("Cannot create vm %s from template"
                                     % cls.copy_name)
        logger.info("Successfully created VM from template")

    @istest
    @tcms('9798', '284050')
    def check_HA_inheritance_template(self):
        """
        Check if template's HA matches master VM's HA
        """
        template_obj = TEMP_API.find(self.template_name)
        self.assertTrue(template_obj is not None, "Error finding template!")
        logger.info("Expected high availability status is %s"\
                    % self.target_HA)
        logger.info("Expected high availability priority is %d"\
                    % self.target_priority)
        enabled = template_obj.get_high_availability().get_enabled()
        priority = int(template_obj.get_high_availability().get_priority())
        logger.info("Actual high availability status is %s"\
                    % enabled)
        logger.info("Actual high availability priority is %d"\
                    % priority)
        self.assertTrue(enabled == self.target_HA
                        and priority == self.target_priority,
                        "Template's HA does not match!")
        logger.info("Template's HA matches original VM's HA.")

    @istest
    @tcms('9798', '284051')
    def check_HA_inheritance_vm(self):
        """
        Check if cloned VM's HA matches master VM's HA
        """
        vm_obj = VM_API.find(self.copy_name)
        self.assertTrue(vm_obj is not None, "Error finding cloned VM!")
        logger.info("Expected high availability status is %s"\
                    % self.target_HA)
        logger.info("Expected high availability priority is %d"\
                    % self.target_priority)
        enabled = vm_obj.get_high_availability().get_enabled()
        priority = int(vm_obj.get_high_availability().get_priority())
        logger.info("Actual high availability status is %s"\
                    % enabled)
        logger.info("Actual high availability priority is %d"\
                    % priority)
        self.assertTrue(enabled == self.target_HA
                        and priority == self.target_priority,
                        "Cloned VM's HA does not match!")
        logger.info("Cloned VM's HA matches original VM's HA.")

    @classmethod
    def teardown_class(cls):
        '''
        Remove VM's and template
        '''
        if not vms.removeVm(positive=True, vm=cls.master_name):
            raise errors.VMException("Cannot remove vm %s" % cls.master_name)
        logger.info("Successfully removed %s." % cls.master_name)
        if not vms.removeVm(positive=True, vm=cls.copy_name):
            raise errors.VMException("Cannot remove vm %s" % cls.copy_name)
        logger.info("Successfully removed %s." % cls.copy_name)
        if not templates.removeTemplate(positive=True,
                                        template=cls.template_name):
            raise errors.TemplateException("Cannot remove template %s"
                                           % cls.template_name)
        logger.info("Successfully removed %s." % cls.template_name)

########################################################################


class VMDisplay(TestCase):
    """
    Display inheritance
    """
    __test__ = True
    master_name = "display_master"
    template_name = "template_display"
    copy_name = "display_copy"
    display_default = SPICE
    target_display = VNC

    @classmethod
    def setup_class(cls):
        '''
        Create a VM and a template
        '''
        # Check default display properties
        blank_temp = TEMP_API.find(BLANK)
        if blank_temp is not None:
            cls.display_default = blank_temp.get_display().get_type()
        logger.info("Default display type is %s" % cls.display_default)
        cls.target_display = VNC if cls.display_default == SPICE else SPICE
        if not vms.addVm(positive=True, name=cls.master_name,
                         vmDescription="Display - master",
                         cluster=config.cluster_name,
                         display_type=cls.target_display):
            raise errors.VMException("Cannot create vm %s" % cls.master_name)
        logger.info("Successfully created VM.")
        if not templates.createTemplate(positive=True, vm=cls.master_name,
                                        name=cls.template_name):
            raise errors.TemplateException("Cannot create template from "
                                           "vm %s" % cls.master_name)
        logger.info("Successfully created template.")
        if not vms.addVm(positive=True, name=cls.copy_name,
                         vmDescription="Display - copy",
                         cluster=config.cluster_name,
                         template=cls.template_name):
            raise errors.VMException("Cannot create vm %s from template"
                                     % cls.copy_name)
        logger.info("Successfully created VM from template")

    @istest
    @tcms('9798', '284052')
    def check_display_inheritance_template(self):
        """
        Check if template's display type matches master VM's display type
        """
        template_obj = TEMP_API.find(self.template_name)
        self.assertTrue(template_obj is not None, "Error finding template!")
        logger.info("Expected display type is %s" % self.target_display)
        display = template_obj.get_display().get_type()
        logger.info("Actual display type is %s" % display)
        self.assertTrue(display == self.target_display,
                        "Template's display type does not match!")
        logger.info("Template's display type matches original VM's HA.")

    @istest
    @tcms('9798', '284053')
    def check_display_inheritance_vm(self):
        """
        Check if cloned VM's display type matches master VM's display type
        """
        vm_obj = VM_API.find(self.copy_name)
        self.assertTrue(vm_obj is not None, "Error finding cloned VM!")
        logger.info("Expected display type is %s" % self.target_display)
        display = vm_obj.get_display().get_type()
        logger.info("Actual display type is %s" % display)
        self.assertTrue(display == self.target_display,
                        "Cloned VM's display type does not match!")
        logger.info("Cloned VM's display type matches original VM's HA.")

    @classmethod
    def teardown_class(cls):
        '''
        Remove VM's and template
        '''
        if not vms.removeVm(positive=True, vm=cls.master_name):
            raise errors.VMException("Cannot remove vm %s" % cls.master_name)
        logger.info("Successfully removed %s." % cls.master_name)
        if not vms.removeVm(positive=True, vm=cls.copy_name):
            raise errors.VMException("Cannot remove vm %s" % cls.copy_name)
        logger.info("Successfully removed %s." % cls.copy_name)
        if not templates.removeTemplate(positive=True,
                                        template=cls.template_name):
            raise errors.TemplateException("Cannot remove template %s"
                                           % cls.template_name)
        logger.info("Successfully removed %s." % cls.template_name)

########################################################################


class VMStateless(TestCase):
    """
    Stateless inheritance
    """
    __test__ = True
    master_name = "stateless_master"
    template_name = "template_stateless"
    copy_name = "stateless_copy"
    default_stateless = False
    target_stateless = True

    @classmethod
    def setup_class(cls):
        '''
        Create a VM and a template
        '''
        # Check default stateless properties
        blank_temp = TEMP_API.find(BLANK)
        if blank_temp is not None:
            cls.default_stateless = blank_temp.get_stateless()
        logger.info("Default stateless status is %s" % cls.default_stateless)
        cls.target_stateless = True if cls.default_stateless == False \
                               else False
        if not vms.addVm(positive=True, name=cls.master_name,
                         vmDescription="Stateless - master",
                         cluster=config.cluster_name,
                         stateless=cls.target_stateless):
            raise errors.VMException("Cannot create vm %s" % cls.master_name)
        logger.info("Successfully created VM.")
        if not templates.createTemplate(positive=True, vm=cls.master_name,
                                        name=cls.template_name):
            raise errors.TemplateException("Cannot create template from "
                                           "vm %s" % cls.master_name)
        logger.info("Successfully created template.")
        if not vms.addVm(positive=True, name=cls.copy_name,
                         vmDescription="Stateless - copy",
                         cluster=config.cluster_name,
                         template=cls.template_name):
            raise errors.VMException("Cannot create vm %s from template"
                                     % cls.copy_name)
        logger.info("Successfully created VM from template")

    @istest
    @tcms('9798', '284109')
    def check_stateless_inheritance_template(self):
        """
        Check if template's stateless status matches master VM's
        stateless status
        """
        template_obj = TEMP_API.find(self.template_name)
        self.assertTrue(template_obj is not None, "Error finding template!")
        logger.info("Expected stateless status is %s" % self.target_stateless)
        stateless = template_obj.get_stateless()
        logger.info("Actual stateless status is %s" % stateless)
        self.assertTrue(stateless == self.target_stateless,
                        "Template's stateless status does not match!")
        logger.info("Template's stateless status matches original VM's"
                    " stateless status.")

    @istest
    @tcms('9798', '284054')
    def check_stateless_inheritance_vm(self):
        """
        Check if cloned VM's stateless status matches master VM's
        stateless status
        """
        vm_obj = VM_API.find(self.copy_name)
        self.assertTrue(vm_obj is not None, "Error finding cloned VM!")
        logger.info("Expected stateless status is %s" % self.target_stateless)
        stateless = vm_obj.get_stateless()
        logger.info("Actual stateless status is %s" % stateless)
        self.assertTrue(stateless == self.target_stateless,
                        "Cloned VM's stateless status does not match!")
        logger.info("Cloned VM's stateless status matches original VM's"
                    " stateless status.")

    @classmethod
    def teardown_class(cls):
        '''
        Remove VM's and template
        '''
        if not vms.removeVm(positive=True, vm=cls.master_name):
            raise errors.VMException("Cannot remove vm %s" % cls.master_name)
        logger.info("Successfully removed %s." % cls.master_name)
        if not vms.removeVm(positive=True, vm=cls.copy_name):
            raise errors.VMException("Cannot remove vm %s" % cls.copy_name)
        logger.info("Successfully removed %s." % cls.copy_name)
        if not templates.removeTemplate(positive=True,
                                        template=cls.template_name):
            raise errors.TemplateException("Cannot remove template %s"
                                           % cls.template_name)
        logger.info("Successfully removed %s." % cls.template_name)

########################################################################


class VMDeleteProtection(TestCase):
    """
    Delete protection inheritance
    """
    __test__ = True
    master_name = "delete_protection_master"
    template_name = "template_delete_protection"
    copy_name = "delete_protection_copy"
    default_protection = False
    target_protection = True

    @classmethod
    def setup_class(cls):
        '''
        Create a VM and a template
        '''
        # Check default delete protection properties
        blank_temp = TEMP_API.find(BLANK)
        if blank_temp is not None:
            cls.default_protection = blank_temp.get_delete_protected()
        logger.info("Default delete protection status is %s"
                    % cls.default_protection)
        cls.target_protection = True if cls.default_protection == False \
                               else False
        if not vms.addVm(positive=True, name=cls.master_name,
                         vmDescription="Delete protection - master",
                         cluster=config.cluster_name,
                         protected=cls.target_protection):
            raise errors.VMException("Cannot create vm %s" % cls.master_name)
        logger.info("Successfully created VM.")
        if not templates.createTemplate(positive=True, vm=cls.master_name,
                                        name=cls.template_name):
            raise errors.TemplateException("Cannot create template from "
                                           "vm %s" % cls.master_name)
        logger.info("Successfully created template.")
        if not vms.addVm(positive=True, name=cls.copy_name,
                         vmDescription="Delete protection - copy",
                         cluster=config.cluster_name,
                         template=cls.template_name):
            raise errors.VMException("Cannot create vm %s from template"
                                     % cls.copy_name)
        logger.info("Successfully created VM from template")

    @istest
    @tcms('9798', '284055')
    def check_protection_inheritance_template(self):
        """
        Check if template's delete protection status matches master VM's
        delete protection status
        """
        template_obj = TEMP_API.find(self.template_name)
        self.assertTrue(template_obj is not None, "Error finding template!")
        logger.info("Expected delete protection status is %s"\
                    % self.target_protection)
        protection = template_obj.get_delete_protected()
        logger.info("Actual delete protection status is %s" % protection)
        self.assertTrue(protection == self.target_protection,
                        "Template's delete protection status does not match!")
        logger.info("Template's delete protection status matches original VM's"
                    " delete protection status.")

    @istest
    @tcms('9798', '284056')
    def check_protection_inheritance_vm(self):
        """
        Check if cloned VM's delete protection status matches master VM's
        delete protection status
        """
        vm_obj = VM_API.find(self.copy_name)
        self.assertTrue(vm_obj is not None, "Error finding cloned VM!")
        logger.info("Expected delete protection status is %s"\
                    % self.target_protection)
        protection = vm_obj.get_delete_protected()
        logger.info("Actual delete protection status is %s" % protection)
        self.assertTrue(protection == self.target_protection,
                        "Cloned VM's delete protection status does not match!")
        logger.info("Cloned VM's delete protection status matches original "
                    "VM's delete protection status.")

    @classmethod
    def teardown_class(cls):
        '''
        Remove VM's and template
        '''
        if not vms.updateVm(positive=True, vm=cls.master_name,
                            protected=False):
            raise errors.VMException("Cannot update vm %s" % cls.master_name)
        logger.info("Successfully removed delete protection from %s."
                     % cls.master_name)
        if not vms.removeVm(positive=True, vm=cls.master_name):
            raise errors.VMException("Cannot remove vm %s" % cls.master_name)
        logger.info("Successfully removed %s." % cls.master_name)
        if not vms.updateVm(positive=True, vm=cls.copy_name,
                            protected=False):
            raise errors.VMException("Cannot update vm %s" % cls.copy_name)
        logger.info("Successfully removed delete protection from %s."
                     % cls.copy_name)
        if not vms.removeVm(positive=True, vm=cls.copy_name):
            raise errors.VMException("Cannot remove vm %s" % cls.copy_name)
        logger.info("Successfully removed %s." % cls.copy_name)
        if not templates.updateTemplate(positive=True,
                                        template=cls.template_name,
                                        protected=False):
            raise errors.TemplateException("Cannot update template %s"
                                           % cls.copy_name)
        logger.info("Successfully removed delete protection from %s."
                     % cls.template_name)
        if not templates.removeTemplate(positive=True,
                                        template=cls.template_name):
            raise errors.TemplateException("Cannot remove template %s"
                                           % cls.template_name)
        logger.info("Successfully removed %s." % cls.template_name)

########################################################################


class VMBoot(TestCase):
    """
    Boot order inheritance
    """
    __test__ = True
    master_name = "boot_master"
    template_name = "template_boot"
    copy_name = "boot_copy"
    default_boot = "hd"
    target_boot = "cdrom"

    @classmethod
    def setup_class(cls):
        '''
        Create a VM and a template
        '''
        # Check default boot device
        blank_temp = TEMP_API.find(BLANK)
        if blank_temp is not None:
            cls.default_boot = blank_temp.get_os().get_boot()[0].get_dev()
        logger.info("Default boot device is %s" % cls.default_boot)
        cap = CAP_API.get(absLink=False)
        version = config.version.split('.')
        version_caps = [v for v in cap if str(v.get_major()) == version[0] and
                        str(v.get_minor()) == version[1]][0]
        boot_types = version_caps.get_boot_devices().get_boot_device()
        boot_types.remove(cls.default_boot)
        # Pick a random boot device - doesn't matter which
        # as long as it's not default boot device
        cls.target_boot = choice(boot_types)
        if not vms.addVm(positive=True, name=cls.master_name,
                         vmDescription="Boot - master",
                         cluster=config.cluster_name,
                         boot=cls.target_boot):
            raise errors.VMException("Cannot create vm %s" % cls.master_name)
        logger.info("Successfully created VM.")
        if not templates.createTemplate(positive=True, vm=cls.master_name,
                                        name=cls.template_name):
            raise errors.TemplateException("Cannot create template from "
                                           "vm %s" % cls.master_name)
        logger.info("Successfully created template.")
        if not vms.addVm(positive=True, name=cls.copy_name,
                         vmDescription="Boot protection - copy",
                         cluster=config.cluster_name,
                         template=cls.template_name):
            raise errors.VMException("Cannot create vm %s from template"
                                     % cls.copy_name)
        logger.info("Successfully created VM from template")

    @istest
    @tcms('9798', '284057')
    def check_boot_inheritance_template(self):
        """
        Check if template's boot device matches master VM's boot device status
        """
        template_obj = TEMP_API.find(self.template_name)
        self.assertTrue(template_obj is not None, "Error finding template!")
        logger.info("Expected boot device is %s" % self.target_boot)
        boot = template_obj.get_os().get_boot()[0].get_dev()
        logger.info("Actual boot device is %s" % boot)
        self.assertTrue(boot == self.target_boot,
                        "Template's boot device does not match!")
        logger.info("Template's boot device matches original VM's"
                    " boot device.")

    @istest
    @tcms('9798', '284058')
    def check_boot_inheritance_vm(self):
        """
        Check if cloned VM's boot device matches master VM's boot device
        """
        vm_obj = VM_API.find(self.copy_name)
        self.assertTrue(vm_obj is not None, "Error finding cloned VM!")
        logger.info("Expected boot device is %s" % self.target_boot)
        boot = vm_obj.get_os().get_boot()[0].get_dev()
        logger.info("Actual boot device is %s" % boot)
        self.assertTrue(boot == self.target_boot,
                        "Cloned VM's boot device status does not match!")
        logger.info("Cloned VM's boot device status matches original "
                    "VM's boot device.")

    @classmethod
    def teardown_class(cls):
        '''
        Remove VM's and template
        '''
        if not vms.removeVm(positive=True, vm=cls.master_name):
            raise errors.VMException("Cannot remove vm %s" % cls.master_name)
        logger.info("Successfully removed %s." % cls.master_name)
        if not vms.removeVm(positive=True, vm=cls.copy_name):
            raise errors.VMException("Cannot remove vm %s" % cls.copy_name)
        logger.info("Successfully removed %s." % cls.copy_name)
        if not templates.removeTemplate(positive=True,
                                        template=cls.template_name):
            raise errors.TemplateException("Cannot remove template %s"
                                           % cls.template_name)
        logger.info("Successfully removed %s." % cls.template_name)

########################################################################
