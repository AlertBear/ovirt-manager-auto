"""
Soft Fencing config module
"""
from rhevmtests.coresystem.config import *  # flake8: noqa

TEST_NAME = "Soft Fencing"
host_with_pm = None  # Filled in setup_module
host_with_pm_num = None  # Filled in setup_module
host_without_pm = None  # Filled in setup_module
host_without_pm_num = None  # Filled in setup_module
job_description = 'Handling non responsive Host'

job_finished = ENUMS['job_finished']
job_failed = ENUMS['job_failed']
service_vdsmd = 'vdsmd'
service_network = 'network'
