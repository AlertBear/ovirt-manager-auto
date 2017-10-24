"""
Configuration file for scheduler sanity test
"""
from rhevmtests.compute.sla.config import *  # flake8: noqa


FILTER_PIN_TO_HOST = ENUMS["filter_pin_to_host"]
FILTER_MEMORY = ENUMS["filter_memory"]
FILTER_CPU = ENUMS["filter_cpu"]
FILTER_NETWORK = ENUMS["filter_network"]
NETWORK_FILTER_NAME = "network_filter"
