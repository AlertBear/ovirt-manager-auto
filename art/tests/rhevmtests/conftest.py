# -*- coding: utf-8 -*-

"""
Pytest conftest file for RHV tests
"""

import pytest


@pytest.fixture(scope="session", autouse=True)
def prepare_env(request):
    """
    Since we need ART to initialized imports are done here
    """
    import helpers
    import config
    from art.rhevm_api import resources
    from art.rhevm_api.tests_lib.low_level import hosts as ll_hosts

    def finalizer():
        """
        Teardown after all tests
        """
        # Check unfinished jobs after all tests
        helpers.get_unfinished_jobs_list()

        # Clean up all storage domains which are not in GE yaml
        helpers.storage_cleanup()
    request.addfinalizer(finalizer)

    """ Set unfinished jobs to FINISHED status before run tests """
    helpers.clean_unfinished_jobs_on_engine()

    hosts_list = ll_hosts.get_host_list()
    assert hosts_list, "No hosts in setup"
    for host in hosts_list:
        config.HOSTS.append(host.name)
        config.HOSTS_IP.append(host.address)
        config.VDS_HOSTS.append(resources.VDS(host.address, config.HOSTS_PW))

    if ll_hosts.is_hosted_engine_configured(
        host_name=hosts_list[0].get_name()
    ):
        config.VM_NAME.append(config.HE_VM)
        config.SD_LIST.append(config.HE_STORAGE_DOMAIN)

    helpers.storage_cleanup()


@pytest.fixture(autouse=True)
def append_captured_log_to_item_stdout(request, caplog):
    """
    This fixture will add captured report sections for each item,
    which will be parsed by the junitxml pytest plugin, to produce
    the xml file.
    """
    yield
    for when in ('setup', 'call', 'teardown'):
        records = caplog.get_records(when)
        for record in records:
            request.node.add_report_section(
                when, 'stdout',
                record.message.decode('utf-8', errors='replace') + '\n')
