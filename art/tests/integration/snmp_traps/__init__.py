from datetime import datetime
from multiprocessing.dummy import Pool, cpu_count
from operator import methodcaller
from os import path
from random import randint
from tempfile import gettempdir
from time import sleep

from art.rhevm_api.tests_lib.low_level import vms
from art.unittest_lib import testflow

import config

# dummy call because of https://bugs.python.org/issue7980
datetime.strptime('2012-01-01', '%Y-%m-%d')

pool = Pool(cpu_count())

configs_dir = path.join(path.dirname(path.realpath(__file__)), "configs")

temp_dir = gettempdir()
if temp_dir is None:
    temp_dir = "/var/tmp"

services = ["snmpd", "snmptrapd", "ovirt-engine-notifier"]
configurations = ["snmptrapd", "snmptrapd_users", "snmpd", "ovirt_notifier"]


def generate_helper(configurations, helper=dict()):
    """
    Description:
        Generates helper dictionary to store configuration files paths.
    Args:
        configurations (list[str]): list of configurations
        helper (dict[str]): helper dictionary
    """
    configuration = configurations[0]

    if configuration == "snmptrapd":
        helper[configuration] = "/etc/snmp/snmptrapd.conf"
    elif configuration == "snmptrapd_users":
        helper[configuration] = "/var/lib/net-snmp/snmptrapd.conf"
    elif configuration == "ovirt_notifier":
        helper[configuration] = (
            "/etc/ovirt-engine/notifier/notifier.conf.d/99-snmp.conf"
        )
    elif configuration == "snmpd":
        helper[configuration] = "/etc/snmp/snmpd.conf"
    else:
        raise NotImplementedError(
            "There's no implementation for this configuration."
        )
    if len(configurations) > 1:
        return generate_helper(configurations[1:], helper)
    else:
        return helper


# Helper dictionary to store configuration file path for every
# service needs to be configured.
helper = generate_helper(configurations)


def copy_config_file(configuration):
    """
    Description:
        Copies config file for given configuration to engine host.
    Args:
        configuration (str): Configuration name.
    """
    assert config.engine.host.fs.put(
        path.join(configs_dir, ".".join([configuration, "conf"])),
        helper[configuration]
    )


def copy_ovirt_notifier_config_file(source_path):
    """
    Description:
        Copies ovirt notifier config file from ART sources to host.
    Args:
        source_path (str): Path of configuration file in ART sources.
    """
    configuration = configurations[-1]
    assert config.engine.host.fs.put(
        source_path,
        helper[configuration]
    )


def copy_config_files(configurations):
    """
    Description:
        Copies services configuration files to
        host for gives configurations.
    Args:
        configurations (list[str]): List of configurations to configure.
    """
    pool.map(copy_config_file, configurations)


def start_service(service_name):
    """
    Description:
        Starting given service by name and making log.
    Args:
        service_name (str): name of the service to stop.
    """
    assert config.engine.host.service(
        service_name
    ).start(), "There was an error while starting a service."


def start_services(services):
    """
    Description:
        Start given list of services.
    Args:
        services (list[str]): List of services to start.
    """
    pool.map(start_service, services)


def stop_service(service_name):
    """
    Description:
        Stopping given service by name and making log.
    Args:
        service_name (str): Name of the service to stop.
    """
    assert config.engine.host.service(
        service_name
    ).stop(), "There was an error while stopping a service."


def stop_services(services):
    """
    Description:
        Stop given list of services.
    Args:
        services (list[str]): List of services to stop.
    """
    pool.map(stop_service, services)


def purge_config(configuration):
    """
    Description:
        Remove this configuration file for given configuration.
    Args:
        configuration (str): Configuration to get rid of.
    """
    return config.engine.host.fs.remove(helper[configuration])


def purge_configs(configurations):
    """
    Description:
        Removes the configuration files for given configurations.
    Args:
        configurations (list[str]): List of configurations you want to
        get rid of.
    """
    pool.map(purge_config, configurations)


def package_management(action, *packages):
    """
    Description:
        Package management abstraction.
    Args:
        action (str): "install", "remove" yum action
        *packages (tuple[str]): Names of packages to process
    """
    if action not in ["install", "remove"]:
        raise ValueError("Action must be 'install' or 'remove'.")

    command = ("yum", action, "-y")
    assert config.engine.host.run_command(
        command + packages
    )[0] == 0, "There was an error while processing packages."


def install_packages(*packages):
    """
    Description:
        Installs a given package or packages.
    Args:
        *packages (tuple[str]): Names of packages to install.
    """
    action = "install"
    package_management(action, *packages)


def remove_packages(*packages):
    """
    Description:
        Removes a given package or packages.
    Args:
        *packages (tuple[str]): Names of packages to remove.
    """
    action = "remove"
    package_management(action, *packages)


def install_snmp_packages():
    """
    Description:
        Installs net-snmp-utils package and logs to testflow
    """
    install_packages("net-snmp-utils", "net-snmp")


def remove_snmp_packages():
    """
    Description:
        Removes net-snmp-utils package and logs to testflow
    """
    remove_packages("net-snmp-utils", "net-snmp")


def start_ovirt_notifier_service():
    """
    Description:
        Starts ovirt-engine-notifier service.
    """
    assert config.engine.host.service(
        services[-1]
    ).start(), "There was en error while starting service."


def stop_ovirt_notifier_service():
    """
    Description:
        Stops ovirt-engine-notifier service.
    """
    assert config.engine.host.service(
        services[-1]
    ).stop(), "There was en error while stopping service."


# TODO: Remove
# These two flush methods are temporary because I've
# sent a patch to python-rrmngmnt which adds flush_file
# method to file system class and maybe it's now in
# package in pip
def flush_snmp_log():
    """
    Description:
        Flushes snmptrapd.log file on engine host.
    """
    try:
        res = config.engine.host.fs.flush_file(
            config.SNMPTRAPD_LOG
        )
    except:
        res = config.engine.host.run_command(
            ["truncate", "-s", "0", config.SNMPTRAPD_LOG]
        )[0] == 0
    finally:
        assert res, "There was an error while flushing a log file."


def flush_ovirt_notifier_log():
    """
    Description:
        Flushes notifier.log file on engine host.
    """
    try:
        res = config.engine.host.fs.flush_file(
            config.NOTIFIER_LOG
        )
    except:
        res = config.engine.host.run_command(
            ["truncate", "-s", "0", config.NOTIFIER_LOG]
        )[0] == 0
    finally:
        assert res, "There was an error while flushing a log file."


def flush_logs():
    """
    Description:
        Flushes snmptrapd.log and notifier.log files on engine host.
    """
    flush_snmp_log()
    flush_ovirt_notifier_log()


def generate_events():
    """
    Description:
        Generates events on engine.
    """
    functions = list()

    def create_vm(vm_name):
        return vms.createVm(
            positive=True,
            vmName=vm_name,
            cluster=config.clusters_names[0],
            template=config.templates_names[0],
            provisioned_size=config.gb,
        )
    functions.append(create_vm)

    def start_vm(vm_name):
        return vms.startVm(
            positive=True,
            vm=vm_name,
            wait_for_status=config.vm_state_up,
            wait_for_ip=False,
            placement_host=config.hosts[
                randint(0, len(config.hosts) - 1)
            ],
        )
    functions.append(start_vm)

    def remove_vm(vm_name):
        return vms.removeVm(
            positive=True,
            vm=vm_name,
            stopVM="true",
        )
    functions.append(remove_vm)

    def mapper(fun):
        """
        Description:
            Closure to return a function which maps iterable
            collection to function argument.
        Args:
            fun (function): function to apply to collection.
        Returns:
            function: Mapped function.
        """
        return lambda names: pool.map(fun, names)

    mapped_functions = [mapper(fun) for fun in functions]

    # Can't use threaded map here because I need creation, starting
    # and removing vms to be in strict order.
    if False in map(
            methodcaller("__call__", config.snmp_vms_names),
            mapped_functions
    ):
        raise Exception("There was a problem while generating events.")


def get_snmp_result():
    """
    Description:
        Get the result of snmp traps.
    Returns:
        bool: True if number of events is equals to the number
        of events in snmptrapd.log file.
    """
    actions = ["add_vm", "vm_start", "vm_stop", "vm_remove"]

    # We need to sleep because of communication time of
    # notifier and traps
    sleep(10)

    notifier_log = config.engine.host.fs.read_file(
        config.NOTIFIER_LOG
    ).lower()
    snmptrapd_log = config.engine.host.fs.read_file(
        config.SNMPTRAPD_LOG
    ).lower()

    if not notifier_log or not snmptrapd_log:
        return False

    def actions_counter(log, action):
        action_string_length = len(action)

        def recurse(count, start):
            location = log.find(action, start)
            if location != -1:
                return recurse(
                    count + 1, location + action_string_length
                )
            else:
                return count

        return recurse(0, 0)

    for action in actions:
        if (
                actions_counter(notifier_log, action) !=
                actions_counter(snmptrapd_log, action)
        ):
            return False

    return True


def setup_class_helper():
    """
    We need to stop the services we are reconfiguring.
    The next step is to create scripts on engine host.
    Then we need to execute these scripts to get config files.
    And the final step in this module setup function is to
    run all services we need except of ovirt-engine-notifier
    as it will be managed within tests.
    """
    # As by default ovirt-notifier-service is not enabled
    # on engine hosts it has to be enabled.
    assert config.engine.host.service(
        services[-1]
    ).enable(), "There was an error while enabling a service."

    functions = (
        stop_services,
        copy_config_files,
        start_services,
    )

    def executor(function):
        if function.__name__ in ["stop_services", "start_services"]:
            return function(services[:-1])
        elif function.__name__ in ["copy_config_files"]:
            return function(configurations[:-1])
        else:
            raise NotImplementedError(
                "There's no implemented scenario for {0}.".format(
                    function.__name__
                )
            )

    # Here used non-threaded map just because functions must apply in
    # given order.
    if False in map(executor, functions):
        raise Exception("There is something wrong in module setup.")


def finalize_class_helper():
    # First, it needs to disable service ovirt-engine-notifier
    # as it will not be using anymore
    config.engine.host.service(services[-1]).disable()

    # We need to stop the services as they will not be using anymore
    # We don't need to stop ovirt-engine-notifier service as it is
    # already in disabled state
    stop_services(services[:-1])

    # And finally purge all configs for good
    purge_configs(configurations)


def setup_package():
    """
    SNMP Traps Package Test Setup Function
    """
    testflow.setup("Setting up package %s", __name__)

    # We need to install net-snmp and net-snmp-utils packages first.
    install_snmp_packages()


def teardown_package():
    """
    SNMP Traps Package Teardown Function
    """
    testflow.teardown("Tearing down package %s.", __name__)

    remove_snmp_packages()
