from rhevmtests.config import GE

OVIRT_ANSIBLE_ROLES_PATH = (
    'automation/ART/art/tests/rhevmtests/integration/ansible/roles/playbooks'
)

# basic login information
ANSIBLE_ENGINE_URL = GE['api_url']
ANSIBLE_ENGINE_LOGIN = GE['username']
ANSIBLE_ENGINE_PASSWORD = GE['password']
ANSIBLE_ENGINE_CA_FILE = GE['engine_cafile']

# workaround for flow-node
ANSIBLE_ENGINE_INSECURE = "yes"

# select cluster and datacenter
ANSIBLE_ENGINE_DATACENTER_NAME = GE['data_center_name']
ANSIBLE_ENGINE_CLUSTER_NAME = GE['clusters'][0]['name']

ENGINE_HOSTS = [
    hosts['name'] for hosts in GE['hosts']
    if hosts['cluster'] == ANSIBLE_ENGINE_CLUSTER_NAME
]

ANSIBLE_DEFAULT_EXTRA_VARS = {
    "engine_url": ANSIBLE_ENGINE_URL,
    "engine_user": ANSIBLE_ENGINE_LOGIN,
    "engine_password": ANSIBLE_ENGINE_PASSWORD,
    "engine_cafile": ANSIBLE_ENGINE_CA_FILE,
    "engine_insecure": ANSIBLE_ENGINE_INSECURE,
    "cluster_name": ANSIBLE_ENGINE_CLUSTER_NAME,
    "data_center_name": ANSIBLE_ENGINE_DATACENTER_NAME
}

CLUSTER_UPDATED_MSG = 'Host cluster {cluster} was updated'
HOST_TO_MAINTENANCE = 'Host {host} was switched to Maintenance Mode.'
HOST_TO_UP = 'Status of host {host} was set to Up.'
HOST_STARTED_UPGRADE = 'Host {host} upgrade was started'
HOST_FINISHED_UPGRADE = 'Host {host} upgrade was completed successfully'

HOST_CHECK_START = 'Started to check for available updates on host {host}.'
HOST_CHECK_FINISH_NO_UPDATE = (
    "Check for available updates on host {host} was completed"
    " successfully with message \'no updates found.\'."
)
HOST_CHECK_FINISH_AVAILABLE_UPDATE = 'Host {host} has available updates'
