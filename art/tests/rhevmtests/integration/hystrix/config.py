from tempfile import mktemp

from rhevmtests.config import *  # flake8: noqa


HYSTRIX_STREAM_ENTRY_POINT = "ovirt-engine/services/hystrix.stream"
HYSTRIX_PROPERTY_KEY = "HystrixMonitoringEnabled"

HYSTRIX_VM_NAME = "hystrix_vm"

event_pipe = mktemp()
status_pipe = mktemp()

# Disk size for virtual machine constant size
gb = 1024 ** 3

hystrix_stream_url = "{0}://{1}:{2}/{3}".format(
    REST_CONNECTION.get('scheme'),
    VDC_HOST,
    REST_CONNECTION.get('port'),
    HYSTRIX_STREAM_ENTRY_POINT
)

hystrix_auth_user = "{0}@{1}".format(VDC_ADMIN_USER, VDC_ADMIN_DOMAIN)
