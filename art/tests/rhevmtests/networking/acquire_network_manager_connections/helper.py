# -*- coding: utf-8 -*-

"""
Helper for acquire connections created by NetworkManager
"""

import shlex

import config as nm_conf
from rhevmtests.networking import (
    config as conf,
    helper as network_helper
)


def create_eth_connection(nic_type, nics, vlan_id, connection):
    """
    Create ethernet connection via nmcli

    Args:
        nic_type (str): NIC type
        nics (list): Host NICs
        vlan_id (str): VLAN id
        connection (str): Connection name

    Raises:
        AssertionError: If create connection failed
    """

    con_type = "vlan" if vlan_id else "ethernet"
    nic = nics[0]
    add_cmd = nm_conf.BASE_CMD.format(
        type_=con_type, connection=nic, nic=nic
    )
    if vlan_id:
        add_cmd += (
            " dev {vlan_nic}.{vlan_id_nic} id {vlan_id}".format(
                vlan_nic=nic, vlan_id_nic=vlan_id, vlan_id=vlan_id
            )
        )

    assert not conf.VDS_0_HOST.run_command(
        command=shlex.split(add_cmd), tcp_timeout=nm_conf.TIMEOUT
    )[0]
    connect_cmd = nm_conf.CONNECT_CMD.format(nic=nic)
    assert not conf.VDS_0_HOST.run_command(
        command=shlex.split(connect_cmd)
    )[0]

    if vlan_id:
        cmd = nm_conf.VLAN_CMD.format(
            type_=con_type, connection=connection, nic=nic,
            dev=nic, vlan_id_1=vlan_id, vlan_id_2=vlan_id
        )
    else:
        cmd = nm_conf.BASE_CMD.format(
            type_=con_type, connection=connection, nic=nic
        )

    assert not conf.VDS_0_HOST.run_command(
        command=shlex.split(cmd), tcp_timeout=nm_conf.TIMEOUT
    )[0]
    assert not conf.VDS_0_HOST.run_command(
        command=shlex.split(nm_conf.CON_UP_CMD.format(connection=connection))
    )[0]


def create_bond_connection(nics, vlan_id):
    """
    Create BOND connection via nmcli

    Args:
        nics (list): Host NICs
        vlan_id (str): VLAN id

    Raises:
        AssertionError: If create connection failed
    """
    assert not conf.VDS_0_HOST.run_command(
        command=shlex.split(nm_conf.BOND_CMD)
    )[0]
    for nic in nics:
        add_cmd = nm_conf.BASE_CMD.format(
            type_="ethernet", connection=nic, nic=nic
        )
        assert not conf.VDS_0_HOST.run_command(command=shlex.split(
            add_cmd), tcp_timeout=nm_conf.TIMEOUT
        )[0]
        assert not conf.VDS_0_HOST.run_command(
            command=shlex.split(nm_conf.SLAVE_CMD.format(slave=nic))
        )[0]
        conf.VDS_0_HOST.run_command(
            command=shlex.split(
                nm_conf.CON_DOWN_CMD.format(connection=nic))
        )
        assert not conf.VDS_0_HOST.run_command(
            command=shlex.split(
                nm_conf.CON_UP_CMD.format(connection=nic))
        )[0]

    if vlan_id:
        vlan_cmd = nm_conf.VLAN_CMD.format(
            type_="vlan", connection="bond1.{vlan}".format(vlan=vlan_id),
            nic="bond1", vlan_id_1=vlan_id, dev="bond1", vlan_id_2=vlan_id
        )
        assert not conf.VDS_0_HOST.run_command(
            command=shlex.split(vlan_cmd), tcp_timeout=nm_conf.TIMEOUT
        )[0]
        assert not conf.VDS_0_HOST.run_command(
            command=shlex.split(nm_conf.CON_UP_CMD.format(
                connection="bond1.{vlan}".format(vlan=vlan_id)))
        )[0]

    assert not conf.VDS_0_HOST.run_command(
        command=shlex.split(nm_conf.CON_UP_CMD.format(connection="bond1"))
    )[0]


def remove_nm_controlled(nics):
    """
    Remove NM_CONTROLLED=no from host NICs ifcfg files

    Args:
        nics (list): Host NICs list
    """
    for nic in nics:
        cmd = (
            nm_conf.SED_CMD.format(path_=network_helper.IFCFG_PATH, nic=nic)
        )
        conf.VDS_0_HOST.run_command(command=shlex.split(cmd))


def reload_nm():
    """
    Reload NetworkManager

    Raises:
        AssertionError: If reload failed
    """
    assert not conf.VDS_0_HOST.run_command(
        command=shlex.split(nm_conf.RELOAD_CMD)
    )[0]
