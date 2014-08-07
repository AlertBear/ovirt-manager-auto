"""
Soft Fencing config module
"""

__test__ = False

from rhevmtests.system.config import *  # flake8: noqa


TEST_NAME = "Soft Fencing"
PM_ADDRESS = PARAMETERS['pm_address']
PM_TYPE_IPMILAN = PARAMETERS['pm_type_ipmilan']
PM_PASSWORD = PARAMETERS['pm_password']
PM_USER = PARAMETERS['pm_user']
host_with_pm = HOSTS[0]
host_without_pm = HOSTS[1]
job_description = 'Executing SSH Soft Fencing on host'

job_finished = ENUMS['job_finished']
job_failed = ENUMS['job_failed']
service_vdsmd = 'vdsmd'
service_network = 'network'
