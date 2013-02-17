from configobj import ConfigObj

global config
config = ConfigObj(raise_errors=True)

from . import ART_CONFIG
params = ART_CONFIG['PARAMETERS']
VM_NAME = params.get('vm_name')

#MAIN_SETUP = "https://10.34.63.3:443/api"
# workaround to skip sdk for now
MAIN_SETUP = "https://lilach-rhel.qa.lab.tlv.redhat.com:443/api"
PGPASS = "123456"

DEFAULT = {
        'def_vm_name': VM_NAME,         # name
        'wait_timeout': 600,            # wait for VM state change
        'install_timeout': 1800,        # wait for RHEVM installation
        '_password': '123456',          # default password
        '_organization': 'Nice Testing Org. Name', # organization name for certs
        }

SDK = {
        'address' : MAIN_SETUP,
        'user' : "vdcadmin@rhev.lab.eng.brq.redhat.com",
        'password': '%(_password)s'
    }

TESTING_ENV = {
        'password': '%(_password)s',
        'repo': '...',
        'user': 'admin',
        'db_pass': '%(_password)s',
        'organization': '%(_organization)s',
        }

ANSWERS = {
# DEFAULT ANSWERS FOR ANSWERFILE
        'password': "%(_password)s",
        'db_pass': "%(_password)s",
        'db_user': 'postgres',
        'organization': '%(_organization)s',
        'override_iptables': 'yes',
        'override_httpd': 'yes',

# DEFAULT KEYWORDS FOR ANSWERFILE
        'AUTH_PASS': '%(password)s',
        'ORG_NAME': '%(organization)s',
        'DB_REMOTE_INSTALL': 'local',
        'DB_SECURE_CONNECTION': 'no',
        'DB_LOCAL_PASS': '%(db_pass)s',
        'CONFIG_NFS': 'no',
        'OVERRIDE_IPTABLES': '%(override_iptables)s',
        'OVERRIDE_HTTPD_CONFIG': '%(override_httpd)s',

        }
ANSWERS['__default__'] = (
            'AUTH_PASS', 'ORG_NAME', 'DB_REMOTE_INSTALL', \
            'DB_SECURE_CONNECTION', 'DB_LOCAL_PASS', 'CONFIG_NFS', \
            'OVERRIDE_IPTABLES', 'OVERRIDE_HTTPD_CONFIG',
            )
        # SPECIFY LIST OF ANSWERS WHICH NEEDS TO BE OVERWITTEN
ANSWERS['3.1.0_0001-3.el6'] = ( #si1
            'AUTH_PASS', 'ORG_NAME', 'DB_REMOTE_INSTALL', \
            'DB_SECURE_CONNECTION', 'DB_LOCAL_PASS', 'CONFIG_NFS', \
            'OVERRIDE_IPTABLES'
            )
ANSWERS['3.1.0_0001-6.el6ev'] = ( #si2.1
            'AUTH_PASS', 'ORG_NAME', 'DB_REMOTE_INSTALL', \
            'DB_SECURE_CONNECTION', 'DB_LOCAL_PASS', 'CONFIG_NFS', \
            'OVERRIDE_IPTABLES', 'OVERRIDE_HTTPD_CONFIG',
            )
ANSWERS['3.1.0-2.el6ev'] = ( #si7
            'AUTH_PASS', 'ORG_NAME', 'DB_REMOTE_INSTALL', \
            'DB_SECURE_CONNECTION', 'DB_LOCAL_PASS', 'CONFIG_NFS', \
            'OVERRIDE_IPTABLES', 'OVERRIDE_HTTPD_CONFIG',
            )
ANSWERS['3.1.0-7.el6ev'] = ( #si11
            'AUTH_PASS', 'ORG_NAME', 'DB_REMOTE_INSTALL', \
            'DB_SECURE_CONNECTION', 'DB_LOCAL_PASS', 'CONFIG_NFS', \
            'OVERRIDE_IPTABLES', 'OVERRIDE_HTTPD_CONFIG',
            )


SETUP = {
        'vm_name': '%(def_vm_name)s',
        'answer_file': '/tmp/answer_file',
        'organization': '%(_organization)s',
        'db_pass': '123456',
        }

CLEANUP = {
        'vm_name': '%(def_vm_name)s',
        }

CONFIG = {
        'vm_name': '%(def_vm_name)s',
        }

MANAGE_DOMAINS = {
        'vm_name': '%(def_vm_name)s',
        }

ISO_UPLOADER = {
        'vm_name': '%(def_vm_name)s',
        }

LOG_COLLECTOR = {
        'vm_name': '%(def_vm_name)s',
        }

UPGRADE = {
        'vm_name': '%(def_vm_name)s',
        }


config.update(DEFAULT)
config['SDK'] = SDK
config['testing_env'] = TESTING_ENV
config['ANSWERS'] = ANSWERS
config['setup'] = SETUP
config['cleanup'] = CLEANUP
config['config'] = CONFIG
config['manage_domains'] = MANAGE_DOMAINS
config['iso_uploader'] = ISO_UPLOADER
config['log_collector'] = LOG_COLLECTOR
config['upgrade'] = UPGRADE

