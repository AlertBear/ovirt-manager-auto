from configobj import ConfigObj

global config
config = ConfigObj(raise_errors=True)

from . import ART_CONFIG
params = ART_CONFIG['PARAMETERS']
VM_NAME = params.get('vm_name')
ISO_UP_CONF = params.get('iso_up_conf_file')
LOG_COL_CONF = params.get('log_col_conf_file')
IMAGE_UP_CONF = params.get('image_up_conf_file')

rest_conn = ART_CONFIG['REST_CONNECTION']
REST_API_PASS = rest_conn.get('password')
REST_API_HOST = rest_conn.get('host')

#MAIN_SETUP = "https://10.34.63.3:443/api"
# workaround to skip sdk for now
MAIN_SETUP = "https://lilach-rhel.qa.lab.tlv.redhat.com:443/api"
PGPASS = "123456"
HOST_PASS = "qum5net"

ISO_DOMAIN_NAME = 'ISO_DOMAIN'
EXPORT_DOMAIN_NAME = 'EXPORT_DOMAIN'
DEFAULT = {
        'def_vm_name': VM_NAME,         # name
        'wait_timeout': 2400,# wait for VM state change. Total install: ~40min
        'install_timeout': 1800,        # wait for RHEVM installation
        '_password_host': HOST_PASS,
        '_password': REST_API_PASS,          # default password
        '_password_db': PGPASS,        # default db password
        '_organization': 'Nice Testing Org. Name', # organization name for certs
        }

SDK = {
        'address' : MAIN_SETUP,
        'user' : "vdcadmin@rhev.lab.eng.brq.redhat.com",
        'password': '%(_password)s'
    }

TESTING_ENV = {
        'password': '%(_password)s',
        'host_pass': '%(_password_host)s',
        'repo': '...',
        'user': 'admin',
        'db_pass': '%(_password_db)s',
        'organization': '%(_organization)s',
        }

ANSWERS = {
# DEFAULT ANSWERS FOR ANSWERFILE
        'password': "%(_password)s",
        'db_pass': "%(_password_db)s",
        'db_user': 'postgres',
        'organization': '%(_organization)s',
        'override_iptables': 'yes',
        'override_httpd': 'yes',
        'override_firewall': 'iptables',
        'application_mode': 'both',

# DEFAULT KEYWORDS FOR ANSWERFILE
        'AUTH_PASS': '%(password)s',
        'ORG_NAME': '%(organization)s',
        'DB_REMOTE_INSTALL': 'local',
        'DB_SECURE_CONNECTION': 'no',
        'DB_LOCAL_PASS': '%(db_pass)s',
        'CONFIG_NFS': 'no',
        'OVERRIDE_IPTABLES': '%(override_iptables)s',
        'OVERRIDE_HTTPD_CONFIG': '%(override_httpd)s',
        'OVERRIDE_FIREWALL': '%(override_firewall)s',
        'FIREWALL_MANAGER': '%(override_firewall)s',
        'APPLICATION_MODE': '%(application_mode)s',

        }
ANSWERS['__default__'] = (
            'AUTH_PASS', 'ORG_NAME', 'DB_REMOTE_INSTALL', \
            'DB_SECURE_CONNECTION', 'DB_LOCAL_PASS', 'CONFIG_NFS', \
            'FIREWALL_MANAGER', 'OVERRIDE_HTTPD_CONFIG','APPLICATION_MODE',
            )
        # SPECIFY LIST OF ANSWERS WHICH NEEDS TO BE OVERWITTEN
ANSWERS['3.1.0-32.el6ev'] = (
            'AUTH_PASS', 'ORG_NAME', 'DB_REMOTE_INSTALL', \
            'DB_SECURE_CONNECTION', 'DB_LOCAL_PASS', 'CONFIG_NFS', \
            'OVERRIDE_IPTABLES', 'OVERRIDE_HTTPD_CONFIG',
            )
ANSWERS['3.2.0-10.14.beta1.el6ev'] = ( #sf-10
            'AUTH_PASS', 'ORG_NAME', 'DB_REMOTE_INSTALL', \
            'DB_SECURE_CONNECTION', 'DB_LOCAL_PASS', 'CONFIG_NFS', \
            'OVERRIDE_FIREWALL', 'OVERRIDE_HTTPD_CONFIG',
            )
ANSWERS['3.3.0-0.5.master.el6ev'] = ( #is3
            'AUTH_PASS', 'ORG_NAME', 'DB_REMOTE_INSTALL', \
            'DB_SECURE_CONNECTION', 'DB_LOCAL_PASS', 'CONFIG_NFS', \
            'FIREWALL_MANAGER', 'OVERRIDE_HTTPD_CONFIG','APPLICATION_MODE',
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

IMAGE_UPLOADER = {
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
config['iso-uploader'] = ISO_UPLOADER
config['log_collector'] = LOG_COLLECTOR
config['image-uploader'] = IMAGE_UPLOADER
config['upgrade'] = UPGRADE

