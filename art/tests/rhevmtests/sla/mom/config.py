"""
MOM test config module
"""
from rhevmtests.sla.config import *  # flake8: noqa

VM_NUM = 10 if PPC_ARCH else 8
POOL_NAME = "mom"
windows_images = (
    {
        "name": "mom-w8", "image": "windows8.1_x64_GT_Disk1"
    },
    {
        "name": "mom-w7", "image": "Windows7_64b_GT_Disk1"
    }
)