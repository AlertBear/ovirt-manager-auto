#! /usr/bin/python
# -*- coding: utf-8 -*-

import config

# initialization parameters
initialization_params = {
    'host_name': config.HOST_NAME,
    'user_name': config.VM_USER_CLOUD_INIT,
    'timezone': config.NEW_ZEALAND_TZ,
    'root_password': config.VDC_ROOT_PASSWORD
}

POOL_TYPE_AUTO = 'automatic'
VM_POOLS_PARAMS = {
    'size': 2,
    'cluster': config.CLUSTER_NAME[0],
    'max_user_vms': 1,
    'prestarted_vms': 0,
    'type_': POOL_TYPE_AUTO,
}
