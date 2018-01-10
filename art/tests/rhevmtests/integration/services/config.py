from rhevmtests.config import *  # flake8: noqa


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
