"""
External tasks configuration module
"""
from rhevmtests.coresystem.config import (
    PARAMETERS as parameters
)

SYSTEM_BASE_NAME = "SYSTEM"

job_description = parameters.get(
    "job_description",
    "job_{0}".format(SYSTEM_BASE_NAME)
)
step_description = parameters.get(
    "step_description",
    "step_{0}".format(SYSTEM_BASE_NAME)
)
sub_step_description = parameters.get(
    "sub_step_description",
    "sub_step_{0}".format(SYSTEM_BASE_NAME)
)
