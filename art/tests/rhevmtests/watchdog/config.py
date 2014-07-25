"""
SLA test config module
"""
from rhevmtests.config import *  # flake8: noqa

PROVISIONING_PROFILE = ART_CONFIG['PROVISIONING_PROFILES']['rhel6.4-agent3.3']
ACTIVATION_KEY = PARAMETERS.get('activation_key')
REGISTER_URL = PARAMETERS.get('server_url')
WATCHDOG_MODEL = PARAMETERS.get('watchdog_model')
