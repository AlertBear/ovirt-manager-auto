"""
 CoreSystem config
"""
__test__ = False

from rhevmtests.config import *  # flake8: noqa

PM1_TYPE = 'ipmilan'
PM2_TYPE = 'apc_snmp'

PM_TYPE_DEFAULT = 'apc'

HOST_FALSE_IP = '10.1.1.256'
ISO_IMAGE = PARAMETERS.get('iso_image', None)

USE_AGENT = PARAMETERS['useAgent']

CDROM_IMAGE_1 = PARAMETERS.get('cdrom_image_1')
CDROM_IMAGE_2 = PARAMETERS.get('cdrom_image_2')
FLOPPY_IMAGE = PARAMETERS.get('floppy_image')

INSTALLATION = True

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
