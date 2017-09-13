#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Fixtures for default route tests
"""

import shlex

import pytest

import helper
import rhevmtests.networking.config as conf
from art.rhevm_api import resources
from art.unittest_lib import testflow


@pytest.fixture(scope="module", autouse=True)
def set_route_to_engine_and_local_host(request):
    """
    Set static routes to engine and to local host that run the test in order to
    keep connection while we change the host default route
    """
    add_cmd = "ip route add {subnet} via {gateway}"
    del_cmd = "ip route del {subnet}"
    check_cmd = "ip route | grep -c {subnet}"

    # Get local host network info
    local_resource = resources.VDS('localhost', conf.VDC_ROOT_USER)
    _, local_ip_and_masks = local_resource.network.find_ips()
    local_int = local_resource.network.find_mgmt_interface()
    assert local_int
    local_ip = local_resource.network.find_ip_by_int(interface=local_int)
    assert local_ip
    local_subnet = helper.get_subnet_from_ip(
        ip_and_masks=local_ip_and_masks, ip=local_ip
    )

    # Get VDS network info
    vds = conf.VDS_0_HOST
    vds_dgw = vds.network.find_default_gw()
    assert vds_dgw

    # Get engine network info
    engine = conf.ENGINE_HOST
    _, engine_ip_and_masks = engine.network.find_ips()
    assert engine_ip_and_masks
    engine_subnet = helper.get_subnet_from_ip(
        ip_and_masks=engine_ip_and_masks, ip=engine.ip
    )

    def fin():
        """
        Remove static routes
        """
        testflow.teardown("Remove static route from host")
        for subnet in (local_subnet, engine_subnet):
            vds.run_command(
                command=shlex.split(del_cmd.format(subnet=subnet))
            )
    request.addfinalizer(fin)

    testflow.setup("Add static route to host")
    for subnet in (local_subnet, engine_subnet):
        out = vds.run_command(shlex.split(check_cmd.format(subnet=subnet)))[1]
        if out != 0:
            continue

        rc, out, err = vds.run_command(
            command=shlex.split(add_cmd.format(subnet=subnet, gateway=vds_dgw))
        )
        assert not rc, (out, err)
