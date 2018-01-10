from multiprocessing import cpu_count
from multiprocessing.dummy import Pool
from operator import methodcaller
from os import path
from random import randint
from tempfile import gettempdir
from time import sleep

from art.core_api.apis_exceptions import APITimeout
from art.rhevm_api.tests_lib.low_level import vms

import config

configs_dir = path.join(path.dirname(path.realpath(__file__)), "configs")

temp_dir = gettempdir()
if temp_dir is None:
    temp_dir = "/var/tmp"


def generate_helper(configurations, _helper=None):
    """
    Description:
        Generates helper dictionary to store configuration files paths.
    Args:
        configurations (list[str]): list of configurations
        _helper (dict[str]): helper dictionary
    """
    if _helper is None:
        _helper = dict()
    c = configurations[0]

    if c == "snmptrapd":
        _helper[c] = "/etc/snmp/snmptrapd.conf"
    elif c == "snmptrapd_users":
        _helper[c] = "/var/lib/net-snmp/snmptrapd.conf"
    elif c == "ovirt_notifier":
        _helper[c] = (
            "/etc/ovirt-engine/notifier/notifier.conf.d/99-snmp.conf"
        )
    elif c == "snmpd":
        _helper[c] = "/etc/snmp/snmpd.conf"
    else:
        raise NotImplementedError(
            "There's no implementation for this configuration."
        )

    if len(configurations) > 1:
        return generate_helper(configurations[1:], _helper)
    else:
        return _helper


# Helper dictionary to store configuration file path for every
# service needs to be configured.
helper = generate_helper(config.CONFIGURATIONS)


def copy_config_file(configuration):
    """
    Description:
        Copies config file for given configuration to engine host.
    Args:
        configuration (str): Configuration name.
    """
    assert config.ENGINE.host.fs.put(
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
    configuration = config.CONFIGURATIONS[config.NOTIFIER_CONFIG]
    assert config.ENGINE.host.fs.put(
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
    map(copy_config_file, configurations)


def start_service(service_name):
    """
    Description:
        Starting given service by name and making log.
    Args:
        service_name (str): name of the service to stop.
    """
    assert config.ENGINE.host.service(
        service_name
    ).start(), "There was an error while starting a service."


def start_services(services):
    """
    Description:
        Start given list of services.
    Args:
        services (list[str]): List of services to start.
    """
    map(start_service, services)


def stop_service(service_name):
    """
    Description:
        Stopping given service by name and making log.
    Args:
        service_name (str): Name of the service to stop.
    """
    assert config.ENGINE.host.service(
        service_name
    ).stop(), "There was an error while stopping a service."


def stop_services(services):
    """
    Description:
        Stop given list of services.
    Args:
        services (list[str]): List of services to stop.
    """
    map(stop_service, services)


def purge_config(configuration):
    """
    Description:
        Remove this configuration file for given configuration.
    Args:
        configuration (str): Configuration to get rid of.
    """
    return config.ENGINE.host.fs.remove(helper[configuration])


def purge_configs(configurations):
    """
    Description:
        Removes the configuration files for given configurations.
    Args:
        configurations (list[str]): List of configurations you want to
        get rid of.
    """
    map(purge_config, configurations)


def install_snmp_packages():
    """
    Description:
        Installs net-snmp-utils package and logs to testflow
    """
    for package in config.SNMP_PACKAGES:
        config.ENGINE.host.package_manager.install(package)


def remove_snmp_packages():
    """
    Description:
        Removes net-snmp-utils package and logs to testflow
    """
    for package in config.SNMP_PACKAGES:
        config.ENGINE.host.package_manager.remove(package)


def start_ovirt_notifier_service():
    """
    Description:
        Starts ovirt-engine-notifier service.
    """
    assert config.ENGINE.host.service(
        config.SERVICES[config.NOTIFIER_SERVICE]
    ).start(), "There was en error while starting service."


def stop_ovirt_notifier_service():
    """
    Description:
        Stops ovirt-engine-notifier service.
    """
    assert config.ENGINE.host.service(
        config.SERVICES[config.NOTIFIER_SERVICE]
    ).stop(), "There was en error while stopping service."


def flush_logs():
    """
    Description:
        Flushes snmpd.log and notifier.log files on engine host.
    """
    for log in config.LOGS_LIST:
        assert config.ENGINE.host.fs.flush_file(
            log
        ), "There was an error while flushing a log file."
    config.ENGINE.host.fs.chown(
        config.NOTIFIER_LOG, config.OVIRT_USER, config.OVIRT_GROUP
    )


def generate_events():
    """
    Description:
        Generates events on engine.
    """
    pool = Pool(cpu_count())
    functions = list()

    def create_vm(vm_name):
        return vms.createVm(
            positive=True,
            vmName=vm_name,
            cluster=config.CLUSTER_NAME[0],
            template=config.TEMPLATE_NAME[0],
            provisioned_size=config.GB,
        )

    functions.append(create_vm)

    def start_vm(vm_name):
        return vms.startVm(
            positive=True,
            vm=vm_name,
            wait_for_status=config.VM_UP,
            wait_for_ip=False,
            placement_host=config.HOSTS[
                randint(0, len(config.HOSTS) - 1)
            ],
        )

    functions.append(start_vm)

    def stop_vm(vm_name):
        res = vms.stopVm(
            positive=True,
            vm=vm_name
        )
        if not res:
            try:
                vms.wait_for_vm_states(
                    vm_name=vm_name,
                    states=[config.VM_DOWN]
                )
                return not res
            except APITimeout:
                return res
        else:
            return res

    functions.append(stop_vm)

    def remove_vm(vm_name):
        return vms.removeVm(
            positive=True,
            vm=vm_name
        )

    functions.append(remove_vm)

    def mapper(f):
        """
        Description:
            Closure to return a function which maps iterable
            collection to function argument.
        Args:
            f (function): function to apply to collection.
        Returns:
            function: Mapped function.
        """
        return lambda names: pool.map(f, names)

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
        of events in snmpd.log file.
    """
    actions = ["add_vm", "vm_start", "vm_stop", "vm_remove"]

    # We need to sleep because of communication time of
    # notifier and traps
    sleep(10)

    notifier_log = config.ENGINE.host.fs.read_file(
        config.NOTIFIER_LOG
    ).lower()
    snmpd_log = config.ENGINE.host.fs.read_file(
        config.SNMPD_LOG
    ).lower()

    if not notifier_log or not snmpd_log:
        return False

    def actions_counter(log, a):
        action_string_length = len(a)

        def recurse(count, start):
            location = log.find(a, start)
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
            actions_counter(snmpd_log, action)
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
    # Flushing logs as they may have information which will may cause
    # this tests failure.
    flush_logs()

    # As by default ovirt-notifier-service is not enabled
    # on engine hosts it has to be enabled.
    assert config.ENGINE.host.service(
        config.SERVICES[config.NOTIFIER_SERVICE]
    ).enable(), "There was an error while enabling a service."

    functions = (
        stop_services,
        copy_config_files,
        start_services,
    )

    def executor(function):
        if function.__name__ in ["stop_services", "start_services"]:
            return function(config.SERVICES[:config.NOTIFIER_SERVICE])
        elif function.__name__ in ["copy_config_files"]:
            return function(config.CONFIGURATIONS[:config.NOTIFIER_CONFIG])
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
    config.ENGINE.host.service(
        config.SERVICES[config.NOTIFIER_SERVICE]
    ).disable()

    # We need to stop the services as they will not be using anymore
    # We don't need to stop ovirt-engine-notifier service as it is
    # already in disabled state
    stop_services(config.SERVICES[:config.NOTIFIER_SERVICE])

    # And finally purge all configs for good
    purge_configs(config.CONFIGURATIONS)


def restore_selinux_context():
    """
    In case the log file was created or flushed manually, we need to
    restore selinux context on it
    """
    config.ENGINE.host.run_command(['restorecon', '-R', config.SNMPD_LOG])
