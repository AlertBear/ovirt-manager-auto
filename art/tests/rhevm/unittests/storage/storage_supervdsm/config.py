"""
Config module for storage supervdsm
"""
__test__ = False

from art.test_handler.settings import opts
from art.rhevm_api.utils import test_utils
from . import ART_CONFIG

PARAMETERS = ART_CONFIG['PARAMETERS']

STORAGE = ART_CONFIG['STORAGE']

DATA_CENTER_TYPE = (PARAMETERS['data_center_type']).split("_")[0]

FIRST_HOST = PARAMETERS.as_list('vds')[0]
FIRST_HOST_PASSWORD = PARAMETERS.as_list('vds_password')[0]

BASENAME = "%sTestStorage" % DATA_CENTER_TYPE
VM_NAME = "vm_%s" % BASENAME

DEFAULT_CLUSTER_NAME = 'cluster_%s' % BASENAME
DEFAULT_DATA_CENTER_NAME = 'datacenter_%s' % BASENAME
DATA_CENTER_NAME = PARAMETERS.setdefault("dc_name", DEFAULT_DATA_CENTER_NAME)
CLUSTER_NAME = PARAMETERS.setdefault("cluster_name", DEFAULT_CLUSTER_NAME)

VDC = PARAMETERS.get('host', None)
VDC_PASSWORD = PARAMETERS.get('password', None)
