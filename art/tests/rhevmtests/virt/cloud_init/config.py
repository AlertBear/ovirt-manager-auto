from rhevmtests.virt.config import *  # flake8: noqa

DC_NAME = DC_NAME[0]
STORAGE_TYPE = STORAGE_TYPE_NFS

USER_PKEY = False
VM_IP = None
# cloud init parameters
VM_USER_CLOUD_INIT_1 = 'cloud_user'
VM_USER_CLOUD_INIT_2 = 'cloud_user_2'
VM_USER_CLOUD_INIT = VM_USER_CLOUD_INIT_1
CLOUD_INIT_TEMPLATE = 'cloud_init_template'
CLOUD_INIT_VM_NAME = "cloud_init_vm"
CLOUD_INIT_NIC_NAME = 'eth4'
CLOUD_INIT_HOST_NAME = 'cloud_init.testing.com'
CLOUD_INIT_VM_DISK_NAME = 'cloud_init_disk'
NEW_ZEALAND_TZ = "NZ"
NEW_ZEALAND_TZ_LIST = ["%s%s" % (NEW_ZEALAND_TZ, tz) for tz in ["DT", "ST"]]
MEXICO_TZ = "EST"
MEXICO_TZ_VALUE = "EST"
DNS_SERVER = "1.2.3.4"
DNS_SEARCH = "foo.test.com"
# cloud init check commands
CHECK_USER_IN_GUEST = 'cat /etc/passwd | grep -E %s'
CHECK_DNS_IN_GUEST = 'cat /etc/resolv.conf | grep -E %s'
CHECK_TIME_ZONE_IN_GUEST = 'date +%Z'
CHECK_HOST_NAME = 'hostname'
CHECK_FILE_CONTENT = 'cat /tmp/test.txt'
NIC_FILE_NAME = '/etc/sysconfig/network-scripts/ifcfg-eth4'
CHECK_NIC_EXIST = "grep %s %s" % (CLOUD_INIT_NIC_NAME, NIC_FILE_NAME)
PRE_CASE_CONDITIONS = {
    "set_authorized_ssh_keys": False,
    "cloud_init_user": VM_USER_CLOUD_INIT_1
}
