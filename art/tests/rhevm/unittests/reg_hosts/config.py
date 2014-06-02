"""
config module for host regression test
"""
__test__ = False

from . import ART_CONFIG

TEST_NAME = "regression_hosts"
PARAMETERS = ART_CONFIG['PARAMETERS']
STORAGE_TYPE = PARAMETERS['storage_type']
VDC = PARAMETERS.get('host', None)
VDC_PASSWORD = PARAMETERS.get('vdc_root_password', None)
CPU_NAME = PARAMETERS['cpu_name']
BASE_NAME = PARAMETERS.get('test_name', TEST_NAME)
DC_NAME = PARAMETERS.get('dc_name', 'datacenter_%s' % BASE_NAME)
CLUSTER_NAME = PARAMETERS.get('cluster_name', 'cluster_%s' % BASE_NAME)
DATA_PATHS = PARAMETERS.as_list('data_domain_path')
DATA_NAME = ["%s_%d" % (STORAGE_TYPE.lower(), index) for index in
             range(len(DATA_PATHS))]
VERSION = PARAMETERS['compatibility_version']
CPU_NAME = PARAMETERS['cpu_name']
HOSTS = PARAMETERS.as_list('vds')
HOST_USER = PARAMETERS.get('host_user')
HOST_PASSWORD = PARAMETERS.as_list('vds_password')[0]
PM1_TYPE = PARAMETERS['pm1_type']
PM2_TYPE = PARAMETERS['pm2_type']
PM1_ADDRESS = PARAMETERS['pm1_address']
PM2_ADDRESS = PARAMETERS['pm2_address']
PM1_USER = PARAMETERS['pm1_user']
PM2_USER = PARAMETERS['pm2_user']
PM1_PASS = PARAMETERS['pm1_pass']
PM2_PASS = PARAMETERS['pm2_pass']
HOST_FALSE_IP = PARAMETERS['host_false_ip']
ISO_IMAGE = PARAMETERS.get('iso_image', None)
HOST_OS = PARAMETERS['host_os']
