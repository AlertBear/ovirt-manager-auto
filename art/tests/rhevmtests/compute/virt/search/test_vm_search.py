#! /usr/bin/python
# -*- coding: utf-8 -*-
"""
Polarion test plan:
/project/RHEVM3/wiki/Compute/3_5_VIRT_Search_Functionality
"""

import pytest

import config
import rhevmtests.compute.virt.helper as virt_helper
import rhevmtests.helpers as helpers
from art.rhevm_api.tests_lib.low_level import (
    vms as ll_vms,
    users as ll_users
)
from art.test_handler.tools import polarion
from art.unittest_lib import testflow, VirtTest
from art.unittest_lib import (
    tier2,
)
from fixtures import (
    add_user, create_vm_for_search
)


@pytest.mark.usefixtures(
    create_vm_for_search.__name__,
)
class TestVMSearchCase(VirtTest):
    """
    VM search test down
    """
    vm_api = ll_vms.VM_API

    @tier2
    @pytest.mark.parametrize(
        ("query", "vm_name", "positive"),
        [
            # Positive regex test:
            polarion("RHEVM-19197")(
                ["description=search_vm_test_down_status_description",
                 config.VM_DOWN_SEARCH_TEST, True]
            ),
            polarion("RHEVM-19198")(
                ["description=search_vm_test_down*",
                 config.VM_DOWN_SEARCH_TEST, True]
            ),
            polarion("RHEVM-19199")(
                ["description=*test_down_status*",
                 config.VM_DOWN_SEARCH_TEST, True]
            ),
            polarion("RHEVM-19200")(
                ["description=SEarch_vM_test_Down_staTUS_dEscription",
                 config.VM_DOWN_SEARCH_TEST, True]
            ),
            polarion("RHEVM-19201")(
                ["description=*", config.VM_DOWN_SEARCH_TEST, True]
            ),

            # Negative regex test:
            polarion("RHEVM-19202")(
                ["something else", config.VM_DOWN_SEARCH_TEST, False]
            ),
            polarion("RHEVM-19203")(
                ["something*", config.VM_DOWN_SEARCH_TEST, False]
            ),
            polarion("RHEVM-19204")(
                ["*else", config.VM_DOWN_SEARCH_TEST, False]
            ),
            polarion("RHEVM-19205")(
                ["*thing*", config.VM_DOWN_SEARCH_TEST, False]
            ),

            # Positive test when VM down
            polarion("RHEVM-19209")(
                ["name=search_vm_test_down_status",
                 config.VM_DOWN_SEARCH_TEST, True]
            ),
            polarion("RHEVM-19210")(
                ["status=down", config.VM_DOWN_SEARCH_TEST, True]
            ),
            polarion("RHEVM-19211")(
                ["datacenter=%s" % config.DC_NAME[0],
                 config.VM_DOWN_SEARCH_TEST, True]
            ),
            polarion("RHEVM-19212")(
                ["cluster=%s" % config.CLUSTER_NAME[0],
                 config.VM_DOWN_SEARCH_TEST, True]
            ),
            polarion("RHEVM-19213")(
                ["os={0}".format(config.VM_OS_TYPE),
                 config.VM_DOWN_SEARCH_TEST, True]
            ),
            polarion("RHEVM-19214")(
                ["template.name=%s" % config.TEMPLATE_NAME[0],
                 config.VM_DOWN_SEARCH_TEST, True]
            ),
            polarion("RHEVM-19215")(
                ["memory=1024", config.VM_DOWN_SEARCH_TEST, True]
            ),
            polarion("RHEVM-19216")(
                ["creationdate>1/1/2000", config.VM_DOWN_SEARCH_TEST, True]
            ),
            polarion("RHEVM-19218")(
                ["type=%s" % config.VM_TYPE_DESKTOP,
                 config.VM_DOWN_SEARCH_TEST, True]
            ),
            polarion("RHEVM-19219")(
                ["Storage=%s" % config.STORAGE_TYPE_NFS,
                 config.VM_DOWN_SEARCH_TEST, True]
            ),

            # Negative test when VM down
            polarion("RHEVM-19258")(
                ["status=up", config.VM_DOWN_SEARCH_TEST, False]
            ),
            polarion("RHEVM-19221")(
                ["cpu_usage>=0", config.VM_DOWN_SEARCH_TEST, False]
            ),
            polarion("RHEVM-19223")(
                ["mem_usage>=0", config.VM_DOWN_SEARCH_TEST, False]
            ),
            polarion("RHEVM-19222")(
                ["network_usage>=0", config.VM_DOWN_SEARCH_TEST, False]
            ),
            polarion("RHEVM-19224")(
                ["creationdate<1/1/2000", config.VM_DOWN_SEARCH_TEST, False]
            ),
            polarion("RHEVM-19226")(
                ["cluster!=%s" % config.CLUSTER_NAME[0],
                 config.VM_DOWN_SEARCH_TEST, False]
            ),
            polarion("RHEVM-19227")(
                ["os!=rhel_5", config.VM_DOWN_SEARCH_TEST, True]
            ),
            polarion("RHEVM-19259")(
                ["memory!=1024", config.VM_DOWN_SEARCH_TEST, False]
            ),
            polarion("RHEVM-19229")(
                ["type=%s" % config.VM_TYPE_SERVER,
                 config.VM_DOWN_SEARCH_TEST, False]
            ),
            ##############################################################
            # Positive test when VM up
            polarion("RHEVM-19260")(
                ["name=search_vm_test_up_status",
                 config.VM_UP_SEARCH_TEST, True]
            ),
            polarion("RHEVM-19261")(
                ["status=up", config.VM_UP_SEARCH_TEST, True]
            ),
            polarion("RHEVM-19262")(
                ["memory==2048", config.VM_UP_SEARCH_TEST, False]
            ),
            # Negative test when VM up
            polarion("RHEVM-19263")(
                ["status=down", config.VM_UP_SEARCH_TEST, False]
            ),
        ]
    )
    def test_vm_search(self, query, vm_name, positive):
        """
        Test that preform basic Vm queries.
        Note: VM status is according to his name

        Args:
            query(str): The query to preform
            vm_name (str): vm name
            positive (bool): The test type, can be True = POSITIVE
            False = NEGATIVE
        """

        assert virt_helper.test_basic_search_params(
            positive, self.vm_api, query, vm_name
        )

    @tier2
    @pytest.mark.usefixtures(add_user.__name__)
    @polarion("RHEVM-17307")
    def test_query_vm_created_by_user(self):
        """
        Positive: Query VMs that created by user with CREATED_BY_USER_ID
        """

        testflow.step("Login as user %s " % config.USER)
        ll_users.loginAsUser(
            user=config.USER,
            domain=config.VDC_ADMIN_DOMAIN,
            password=config.VDC_PASSWORD,
            filter=True
        )
        testflow.step(
            "Create VM %s as user %s",
            config.VM_CREATED_BY_USER,
            config.USER
        )
        assert ll_vms.createVm(
            positive=True,
            vmName=config.VM_CREATED_BY_USER,
            cluster=config.CLUSTER_NAME[0]
        )

        vms = helpers.search_object(
            util=self.vm_api,
            query="created_by_user_id=%s" %
                  ll_users.get_user_id(config.USER)
        )
        assert config.VM_CREATED_BY_USER in vms
