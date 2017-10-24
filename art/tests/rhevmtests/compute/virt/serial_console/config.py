"""
Virt - serial console config
"""

from rhevmtests.networking import config as net_conf
from rhevmtests.compute.virt.config import *  # flake8: noqa

SERIAL_CONSOLE_VM = "serial_console_VM"
SERIAL_CONSOLE_VM_NIC = net_conf.VM_NICS[-1]
SERIAL_CONSOLE_VM_USER = 'root'
SERIAL_CONSOLE_VM_PASSWORD = 'qum5net'
SERIAL_CONSOLE_PRIVATE_KEY_NAME = '/root/.ssh/sc_id_rsa'
SC_ADMIN = 'admin'
SC_DEFAULT_PORT = '2222'
SC_CONNECTION_POINT = 'ovirt-vmconsole@{engine}'.format(
    engine=ENGINE.host.fqdn
)
ENV_READY = True
PROXY_KEY_LOCATION = (
    '/etc/pki/ovirt-engine/certs/vmconsole-proxy-host-cert.pub'
)

SC_HOST_SERVICE = 'ovirt-vmconsole-host-sshd'
SC_ENGINE_SERVICE = 'ovirt-vmconsole-proxy-sshd'
GETTY_SERVICE = 'serial-getty@ttyS0'
SC_VM_ID = None

GENERATE_PRIVATE_KEY_CMD = ['ssh-keygen',
                            '-t',
                            'rsa',
                            '-f',
                            SERIAL_CONSOLE_PRIVATE_KEY_NAME,
                            '-q',
                            '-N',
                            '']
CONNECT_TO_CONSOLE_COMMAND = ['ssh',
                              '-o',
                              'StrictHostKeyChecking=no',
                              '-t',
                              '-i',
                              SERIAL_CONSOLE_PRIVATE_KEY_NAME,
                              '-p',
                              SC_DEFAULT_PORT,
                              SC_CONNECTION_POINT]

TEST_FILE = '/root/sc_test_file'
GEN_FILE_CMD = 'echo {text} > {test_file}'

SKIP_MESSAGE = (
    'Necessary services to run serial console test cases are not active on'
    ' Engine or Host side. Therefore all other SC cases will be skipped.'
)
KEY_UPLOAD_FAILURE_MSG = (
    'Was not able to set the ssh public key for admin user'
)
GETTY_SERVICE_FAILED = 'Was not able to {action} serial-getty@ttyS0 service.'

HELP_RETURN = (
    'usage: ovirt-vmconsole-proxy-shell [-h] [--debug] '
    '{help,info,connect,list} ...\n\n'
    'oVirt VM console proxy shell\n\n'
    'positional arguments:\n'
    '  {help,info,connect,list}\n'
    '                        sub-command help\n'
    '    help                present help\n'
    '    info                present information\n'
    '    connect             connect to console [default]\n'
    '    list                list consoles\n\noptional arguments:\n'
    '  -h, --help            show this help message and exit\n'
    '  --debug               enable debug log\n'
)
PACKAGE = 'package=ovirt-vmconsole-proxy-shell'
