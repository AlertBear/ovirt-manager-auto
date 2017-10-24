"""
MOM test config module
"""
from rhevmtests.compute.sla.config import *  # flake8: noqa

# General test constants
NUMBER_OF_VMS = 10 if PPC_ARCH else 8
MOM_VMS = ["mom_vm_%s" % i for i in range(NUMBER_OF_VMS)]
BALLOON_FILE = "/etc/vdsm/mom.d/02-balloon.policy"
HOST_ALLOC_PATH = "/tmp/hostAlloc.py"
ALLOC_SCRIPT_LOCAL = "tests/rhevmtests/compute/sla/mom/hostAlloc.py"
DEFVAR_PRESSURE_THRESHOLD = "defvar pressure_threshold"
DEFVAR_PRESSURE_THRESHOLD_020 = "0.20"
DEFVAR_PRESSURE_THRESHOLD_040 = "0.40"
VM_BALLOON_MAX = "balloon_max"
VM_BALLOON_CURRENT = "balloon_cur"
VM_BALLOON_INFO = "balloonInfo"
BALLOON_TIMEOUT = 300

# Specific tests constants
DIFFERENT_MEMORY = GB * 5 if PPC_ARCH else GB / 2
MULTIPLY_VMS_MEMORY = GB * 2 if PPC_ARCH else GB / 2
MULTIPLY_VMS_MEMORY_GUARANTEED = GB if PPC_ARCH else GB / 4

MOM_SERVICE = "mom-vdsm"
