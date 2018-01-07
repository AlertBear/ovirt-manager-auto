from art.rhevm_api import resources
from art.test_handler.settings import ART_CONFIG

PARAMETERS = ART_CONFIG['PARAMETERS']
VDC_ROOT_PASSWORD = PARAMETERS.get('vdc_root_password')
REST_CONNECTION = ART_CONFIG['REST_CONNECTION']
VDC_PASSWORD = REST_CONNECTION['password']
VDC_PORT = REST_CONNECTION['port']
ENGINE_ENTRY_POINT = REST_CONNECTION['entry_point']

VDC_ADMIN_USER = 'admin'
VDC_ADMIN_DOMAIN = 'internal'
VDC_HOST = REST_CONNECTION['host']

ENGINE_HOST = resources.Host(VDC_HOST)
ENGINE_HOST.users.append(resources.RootUser(VDC_ROOT_PASSWORD))

ENGINE = resources.Engine(
    ENGINE_HOST,
    resources.ADUser(
        VDC_ADMIN_USER,
        VDC_PASSWORD,
        resources.Domain(VDC_ADMIN_DOMAIN)
    ),
    schema=REST_CONNECTION.get('schema'),
    port=VDC_PORT,
    entry_point=ENGINE_ENTRY_POINT
)

HOST_RHVH = 'ovirt_node'
HOST_RHEL = 'rhel'

MACHINES = ('engine', 'host_rhel', 'host_rhvh')

ENGINE_SERVICES = {
    'ovirt-engine',
    'ovirt-engine-dwhd',
    'ovirt-fence-kdump-listener',
    'ovirt-imageio-proxy',
    'ovirt-vmconsole-proxy-sshd',
    'ovirt-websocket-proxy'
}

HOST_SERVICES = {
    'vdsmd',
    'supervdsmd',
    'sanlock',
    'libvirtd',
    'ovirt-imageio-daemon',
    'mom-vdsm',
    'ovirt-vmconsole-host-sshd',
}

SERVICES = ENGINE_SERVICES.union(HOST_SERVICES)

MACHINE_SERVICES = {
    'engine': ENGINE_SERVICES,
    'host_rhel': HOST_SERVICES,
    'host_rhvh': HOST_SERVICES
}

ACTIONS = ('enabled', 'running', 'is-faultless')

# Can't be in class scope
# Python2 leaks the loop control variable
# { 'service_name': 'bug_id'}
BUGGED_SERVICES = {
}

DISABLED_SERVICES = [
    'ovirt-imageio-daemon',
    'sanlock'
]

DAYS_TO_CHECK_LOGS = 7
