"""
This is place for fixtures for upgrade purpose and other pytest related stuff.

If you want to create some resources before upgrade and clean them after
upgrade procedure is finished, use session scope as in example below:

@pytest.fixture(scope='session')
def prepare_vm_resources(request):
    def fin():
        if skip_before_upgrade_check():
            return
        print "[TEARDOWN] Fixture removing VM: %s" % VM
    request.addfinalizer(fin)
    print "[SETUP] Fixture creating VM: %s" % VM

Be aware that after upgrade, data structure can change and we will run
another execution of pytest after upgrade! So you should clean all stuff in the
next run of pytest on upgraded version.
"""

import inspect
import logging

from art.rhevm_api import resources
import pytest
import art.rhevm_api.tests_lib.low_level.hosts as ll_hosts

import config

logger = logging.getLogger(__name__)

skip_upgrade_condition = config.current_version == config.upgrade_version


def _get_parent_frame_name():
    """
    Returns parent name of function from which you call this function.
    """
    curframe = inspect.currentframe()
    return inspect.getouterframes(curframe, 2)[2][3]


def skip_before_upgrade_check():
    """
    Check if it is before upgrade, and writes info to the log.

    Returns:
        boolean: True if it is before upgrade, False otherwise
    """
    if not skip_upgrade_condition:
        logger.info(
            "Skipping from: %s before upgrade", _get_parent_frame_name()
        )
        return True
    return False


def skip_after_upgrade_check():
    """
    Check if it is after upgrade, and writes info to the log.

    Returns:
        boolean: True if it is before upgrade, False otherwise
    """
    if skip_upgrade_condition:
        logger.info(
            "Skipping from: %s after upgrade", _get_parent_frame_name()
        )
        return True
    return False


@pytest.fixture(scope="session")
def populate_host_list():
    """
    Populate list of hosts in GE

    Raises:
          EnvironmnentError: if hosts do not exist
    """
    host_objs = ll_hosts.get_host_list()
    if not host_objs:
        raise EnvironmentError("This environment doesn't include hosts")
    logger.info(
        "This GE includes the following hosts: %s",
        [host_obj.name for host_obj in host_objs]
    )
    for host in host_objs:
        config.hosts.add(host.name)

        host_type = host.get_type()

        resource_host = resources.Host(host.address)
        resource_host.users.append(
            resources.RootUser(config.root_password)
        )

        if host_type == config.HOST_RHEL_TYPE:
            config.hosts_rhel.add(resource_host)
            config.hosts_rhel_names.add(host.name)
        elif host_type == config.HOST_RHVH_TYPE:
            config.hosts_rhvh.add(resource_host)
            config.hosts_rhvh_names.add(host.name)
        else:
            raise EnvironmentError("Unknown host type {} - {} [{}]".format(
                host_type, host.name, host.address
            ))
