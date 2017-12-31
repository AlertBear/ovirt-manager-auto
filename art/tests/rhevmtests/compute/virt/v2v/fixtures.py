#! /usr/bin/python
# -*- coding: utf-8 -*-

import pytest
import helper
import config
from art.rhevm_api.utils import jobs
from art.unittest_lib import testflow
from art.rhevm_api.tests_lib.low_level import (
    vms as ll_vms,
)
from art.rhevm_api.tests_lib.high_level import (
    storagedomains as hl_storagedomains
)


@pytest.fixture(scope='class')
def teardown_fixture(request):
    """
    Remove vms safely
    """
    def fin():
        testflow.teardown("Remove all vms in list: %s", config.ALL_V2V_VMS)
        ll_vms.safely_remove_vms(config.ALL_V2V_VMS)
    request.addfinalizer(fin)


@pytest.fixture(scope='class')
def v2v_parallel_import_fixture(request):
    """
    Imports vms parallel from the external provider like VMWare, KVM
    """
    vms_to_import = request.node.cls.vms_to_import
    providers = getattr(
        request.node.cls, 'providers', config.VMWARE_PROVIDERS
    )
    vms_to_remove = [vms[1] for vms in vms_to_import]

    def fin():
        """
        Remove created vm/s safely if it exists
        """
        testflow.teardown("Remove all vms in list: %s", vms_to_remove)
        ll_vms.safely_remove_vms(vms_to_remove)
    request.addfinalizer(fin)
    job_list = list()
    for provider in providers:
        for vm_info in helper.get_all_vms_import_info(
            provider=provider, vms_to_import=vms_to_import
        ):
            job_list.append(
                jobs.Job(
                    helper.import_vm_from_external_provider, (),
                    vm_info
                )
            )
    job_set = jobs.JobsSet()
    job_set.addJobs(job_list)
    job_set.start()
    job_set.join()
    results = list()
    for job in job_list:
        if not job.result or job.result is False:
            results.append(False)
            testflow.setup("Failed to import {vm} , Exception: {ex}".format(
                vm=job.kwargs["provider_vm_name"], ex=job.exception)
            )
        else:
            results.append(True)
    assert all(results)


@pytest.fixture(scope='class')
def attach_and_activate_iso_domain(request):
    """
    Attach / detach iso domain to setup
    """
    def fin():
        """
        teardown detach iso domain
        """
        testflow.teardown("Detach iso domain")
        hl_storagedomains.detach_and_deactivate_domain(
            config.DC_NAME[0], config.SHARED_ISO_DOMAIN_NAME,
            engine=config.ENGINE
        )
    request.addfinalizer(fin)
    testflow.setup("Attach and activate iso domain")
    assert hl_storagedomains.attach_and_activate_domain(
        config.DC_NAME[0], config.SHARED_ISO_DOMAIN_NAME
    )
