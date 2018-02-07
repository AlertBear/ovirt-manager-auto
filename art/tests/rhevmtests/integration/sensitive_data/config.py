from rhevmtests.config import *  # flake8: noqa


CONF_DIR = '/etc/ovirt-engine/engine.conf.d/'
LOGS_PATH = '/var/log/ovirt-engine/'

PKI_PATH = '/etc/pki/ovirt-engine/keys/'
PRIVATE_KEY_HEADER = '-----BEGIN PRIVATE KEY-----'

CONFS = {
    '10-setup-pki.conf': 'ENGINE_PKI_ENGINE_STORE_PASSWORD',
    '10-setup-database.conf': 'ENGINE_DB_PASSWORD',
    '10-setup-dwh-database.conf': 'DWH_DB_PASSWORD',
    '11-setup-sso.conf': 'ENGINE_SSO_CLIENT_SECRET',
}