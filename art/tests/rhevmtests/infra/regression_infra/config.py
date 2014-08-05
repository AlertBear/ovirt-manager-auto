"""
Config module for data center sanity tests
"""

# This must be here so nose doesn't consider this as a test
__test__ = False

from rhevmtests.config import *  # flake8: noqa


DATA_CENTER_1_NAME = "RestDataCenter1"
DATA_CENTER_1_NAME_UPDATED = "RestDataCenter1Updated"
DATA_CENTER_2_NAME = "RestDataCenter2"
DATA_CENTER_3_NAME = "RestDataCenter3"

CLUSTER_1_NAME = "RestCluster1"
CLUSTER_2_NAME = "RestCluster2"
CLUSTER_3_NAME = "RestCluster3"
CLUSTER_4_NAME = "RestCluster4"

HOST_NAME = HOSTS[0]

STORAGE_DOMAIN_NAME = "DataDomainRest"
DATA_DOMAIN_ADDRESS = PARAMETERS.as_list('data_domain_address')[0]
DATA_DOMAIN_PATH = PARAMETERS.as_list('data_domain_path')[0]

VM_NAME = VM_NAME[0]
TEMPLATE_NAME = TEMPLATE_NAME[0]

USER_VDCADMIN = AD_USERNAME
USERNAME = "istein"
USER_DOMAIN = AD_USER_DOMAIN
USER_NO_ROLES = AD_USER_NO_ROLES
USER_NON_EXISTING = "user_doesnt_exist"

TAG_1_NAME = "TagRestTest_sentinel1"
TAG_2_NAME = "TagRestTest2"
TAG_3_NAME = "TagRestTest3"
TAG_4_NAME = "TagRestTest_to_existing_name"
TAG_5_NAME = "TagRestTestExisting"
TAG_SUB_NAME = "SubTagRestTest"
GROUP = "Everyone"
