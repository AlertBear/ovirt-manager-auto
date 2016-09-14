"""
Configuration file for scheduler sanity test
"""
from rhevmtests.sla.config import *  # flake8: noqa

FILTER_TYPE = ENUMS["policy_unit_type_filter"]
FILTER_PIN_TO_HOST = ENUMS["filter_pin_to_host"]
FILTER_MEMORY = ENUMS["filter_memory"]
FILTER_CPU = ENUMS["filter_cpu"]
FILTER_NETWORK = ENUMS["filter_network"]
NETWORK_FILTER_NAME = "network_filter"
