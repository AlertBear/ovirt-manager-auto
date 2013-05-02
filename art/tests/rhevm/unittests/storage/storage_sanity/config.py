"""
Config module for storage sanity tests
"""
__test__ = False

from . import ART_CONFIG

PARAMETERS = ART_CONFIG['PARAMETERS']

DATA_CENTER_TYPE = PARAMETERS['data_center_type']

STORAGE = ART_CONFIG['STORAGE']

EXTEND_LUN = STORAGE.get('extend_lun', None)

FIRST_HOST = PARAMETERS.as_list('vds')[0]

BASENAME = "%sTestStorage" % DATA_CENTER_TYPE

DATA_CENTER_NAME = 'datacenter_%s' % BASENAME

VDC = PARAMETERS.get('host', None)
VDC_PASSWORD = PARAMETERS.get('password', None)
