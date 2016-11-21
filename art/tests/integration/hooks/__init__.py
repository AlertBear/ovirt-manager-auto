from art.rhevm_api.utils import test_utils
from art.unittest_lib import testflow
from utilities.rhevm_tools.base import Setup
from utilities.rhevm_tools.config import ConfigUtility

from hooks import config


def get_default_custom_property_value(custom_property):
    for prop in custom_property.split("\n"):
        if config.compatibility_version in prop:
            return "'" + prop.split(
                "version"
            )[0].replace(": ", "=", 1).strip() + "'"


def setup_package():
    testflow.setup("Setting up %s package.", __name__)

    testflow.step("Running Setup() for getting all configuration.")
    setup = Setup(
        config.vdc_host,
        config.vdc_root_user,
        config.vdc_root_password,
        conf=config.configuration_variables
    )

    testflow.step("Configuring custom properties for this module needs.")
    config_utility = ConfigUtility(setup)

    config_utility(get="UserDefinedVMProperties")
    config.custom_property_default = get_default_custom_property_value(
        config_utility.out
    )

    config_utility(get="CustomDeviceProperties")
    config.custom_property_vnic_default = get_default_custom_property_value(
        config_utility.out
    )

    config_utility(
        set=config.CUSTOM_PROPERTY_HOOKS,
        cver=config.compatibility_version
    )
    config_utility(
        set=config.CUSTOM_PROPERTY_VNIC_HOOKS,
        cver=config.compatibility_version
    )
    test_utils.restart_engine(config.engine, 5, 70)


def teardown_package():
    testflow.teardown("Tearing down package %s.", __name__)

    testflow.step("Running Setup() for getting all configuration.")
    setup = Setup(
        config.vdc_host,
        config.vdc_root_user,
        config.vdc_root_password,
        conf=config.configuration_variables
    )

    testflow.step("Configuring custom properties to default values.")
    config_utility = ConfigUtility(setup)
    config_utility(
        set=config.custom_property_default,
        cver=config.compatibility_version
    )
    config_utility(
        set=config.custom_property_vnic_default,
        cver=config.compatibility_version
    )

    test_utils.restart_engine(config.engine, 5, 70)
