###############################################################################
# External tasks
###############################################################################

__test__ = False

from rhevmtests.system.config import *  # flake8: noqa

SYSTEM_BASE_NAME = "SYSTEM"

EXTERNAL_JOB_DESCRIPTION = PARAMETERS.get('job_description', 'job_%s' %
                                          SYSTEM_BASE_NAME)
EXTERNAL_STEP_DESCRIPTION = PARAMETERS.get('step_description', 'step_%s' %
                                           SYSTEM_BASE_NAME)
EXTERNAL_SUB_STEP_DESCRIPTION = PARAMETERS.get('sub_step_description',
                                               'sub_step_%s' %
                                               SYSTEM_BASE_NAME)
