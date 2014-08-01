"""
 CoreSystem config
"""
__test__ = False

from rhevmtests.config import *  # flake8: noqa
from art.rhevm_api.utils import test_utils


SYSTEM_BASE_NAME = "CoreSystem"
PM1_TYPE = 'ipmilan'
PM2_TYPE = 'apc-snmp'
PM1_ADDRESS = '10.35.35.35'
PM2_ADDRESS = '10.11.11.11'
PM1_USER = 'user1'
PM2_USER = 'user2'
PM1_PASS = 'pass1'
PM2_PASS = 'pass2'
HOST_FALSE_IP = '10.1.1.256'
ISO_IMAGE = PARAMETERS.get('iso_image', None)

OS_TYPE = test_utils.convertOsNameToOsTypeElement(
    True, PARAMETERS['vm_os'])[1]['osTypeElement']

USE_AGENT = PARAMETERS['useAgent']

CDROM_IMAGE_1 = PARAMETERS.get('cdrom_image_1')
CDROM_IMAGE_2 = PARAMETERS.get('cdrom_image_2')
FLOPPY_IMAGE = PARAMETERS.get('floppy_image')

TEMPLATE_NAME = ["".join([TEST_NAME, '_', elm]) for elm in
                 PARAMETERS.as_list('template_name')]

INSTALLATION = PARAMETERS.get('installation', 'true')

DC_NAME = PARAMETERS.get('dc_name', 'datacenter_%s' % SYSTEM_BASE_NAME)
CLUSTER_NAME = PARAMETERS.get('cluster_name', 'cluster_%s' % SYSTEM_BASE_NAME)
TEMPLATE_NAME = PARAMETERS.get('template', 'hooks_template')
TCMS_PLAN_CUSTOM = 10054
TCMS_PLAN_VNIC = 10167
VER = COMP_VERSION
CUSTOM_PROPERTY = "UserDefinedVMProperties='auto_custom_hook=^[0-9]+$'"
CUSTOM_PROPERTY_VNIC = ("""CustomDeviceProperties='{type=interface;"""
                        """prop={speed=^([0-9]{1,5})$;"""
                        """port_mirroring=^(True|False)$;"""
                        """bandwidth=^([0-9]{1,5})$}}'""")
VM_TEMPLATE_FOR_TEST = 'vm-templ-for-test'
VM_FOR_TEMPLATE = 'vm_for_template'

CONFIG_ELEMENTS = 'elements_conf'
CONFIG_SECTION = 'RHEVM Utilities'
VARS = opts[CONFIG_ELEMENTS][CONFIG_SECTION]
