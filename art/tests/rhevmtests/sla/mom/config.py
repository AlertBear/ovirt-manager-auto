"""
MOM test config module
"""
from rhevmtests.sla.config import *  # flake8: noqa

VM_NUM = 10 if PPC_ARCH else 8
POOL_NAME = "mom"
NUM_OF_HOSTS = 2
BALLOON_FILE = "/etc/vdsm/mom.d/02-balloon.policy"
SLEEP_TIME = 20
WAIT_FOR_IP_TIMEOUT = 300
BALLOON_ITERATIONS = 25  # number of iterations for testing test ballooning
NEGATIVE_ITERATION = 10
HOST_ALLOC_PATH = "/tmp/hostAlloc.py"
ALLOC_SCRIPT_LOCAL = "tests/rhevmtests/sla/mom/hostAlloc.py"
SERVICE_PUPPET = "puppet"
SERVICE_GUEST_AGENT = "ovirt-guest-agent"