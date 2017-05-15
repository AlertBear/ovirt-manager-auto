import pytest
import config
from art.test_handler.tools import bz, polarion
from art.rhevm_api.tests_lib.low_level import vms as ll_vms


"""
Standard scenario structure:
    [
        {test_name: description},
        {instance_to_be_created_as_setup: [
            dict_with_default_vm_params,
            {vm_param_to_be_changed_or_added_to_default: new_param_value, ...},
            ]
        },
        {scenario_dict_described_in_helpers_executor_method}
    ]

"""

ADD_VM_DEFAULTS = {
    "positive": True,
    "vmName": config.ADD_VM_NAME,
    'cluster': config.CLUSTER_NAME[0],
    'os_type': config.VM_OS_TYPE,
    'type': config.VM_TYPE,
    'display_type': config.VM_DISPLAY_TYPE
}

add_vm_scenario = [
    polarion("RHEVM3-12382")(bz({"1333340": {}})(
        [
            {"custom_boot_sequence": "Add vm with custom boot sequence"},
            {},
            {
                (1, config.CREATE): [
                    ADD_VM_DEFAULTS,
                    {
                        'boot': ['network', 'hd'],
                    }
                ],
                (2, config.COMPARE): {
                    (1, 'func'): [
                        ll_vms.get_vm_boot_sequence, [config.ADD_VM_NAME]
                    ],
                    (2, "val"): [
                        config.ENUMS['boot_sequence_network'],
                        config.ENUMS['boot_sequence_hd']
                    ]
                }
            }
        ]
    )),
    polarion("RHEVM3-10087")(
        [
            {"default_vm": "Add default vm without special parameters"},
            {},
            {
                (1, config.CREATE): [
                    ADD_VM_DEFAULTS,
                    {}
                ]
            }
        ]
    ),
    polarion("RHEVM3-12361")(
        [
            {"ha_server_vm": "Add HA server vm"},
            {},
            {
                (1, config.CREATE): [
                    ADD_VM_DEFAULTS,
                    {
                        "highly_available": True,
                        "type": config.ENUMS['vm_type_server']
                    }
                ]
            }
        ]
    ),
    polarion("RHEVM3-12363")(bz({"1333354": {}})(
        [
            {"custom_property": "Add vm with custom property"},
            {},
            {
                (1, config.CREATE): [
                    ADD_VM_DEFAULTS,
                    {
                        'custom_properties': 'sndbuf=111'
                    }
                ]
            }
        ]
    )),
    polarion("RHEVM3-12385")(
        [
            {"guaranteed_memory": "Add vm with guaranteed memory"},
            {},
            {
                (1, config.CREATE): [
                    ADD_VM_DEFAULTS,
                    {
                        'memory': config.GB*2,
                        'max_memory': config.GB*2,
                        'memory_guaranteed': config.GB*2
                    }
                ]
            }
        ]
    ),
    polarion("RHEVM3-12383")(
        [
            {"disk_vm": "Add vm with disk"},
            {},
            {
                (1, config.CREATE): [
                    ADD_VM_DEFAULTS,
                    {
                        'disk_type': config.DISK_TYPE_DATA,
                        'provisioned_size': config.GB*2,
                        'format': config.DISK_FORMAT_COW,
                        'interface': config.INTERFACE_VIRTIO
                    }
                ]
            }
        ]
    ),
    polarion("RHEVM3-12517")(
        [
            {"linux_boot_options": "Add vm with linux_boot_options"},
            {},
            {
                (1, config.CREATE): [
                    ADD_VM_DEFAULTS,
                    {
                        'kernel': '/kernel-path',
                        'initrd': '/initrd-path',
                        'cmdline': 'rd_NO_LUKS rd_NO_MD'
                    }
                ]
            }
        ]
    ),
    polarion("RHEVM3-12518")(
        pytest.mark.skipif(config.PPC_ARCH, reason=config.PPC_SKIP_MESSAGE)(
            [
                {"rhel_os": "Add vm with Rhel OS type"},
                {},
                {
                    (1, config.CREATE): [
                        ADD_VM_DEFAULTS,
                        {
                            'os_type': config.ENUMS['rhel6x64']
                        }
                    ]
                }
            ]
        )
    ),
    polarion("RHEVM3-12520")(
        pytest.mark.skipif(config.PPC_ARCH, reason=config.PPC_SKIP_MESSAGE)(
            [
                {"windows_7_os": "Add vm with Windows 7 OS type"},
                {},
                {
                    (1, config.CREATE): [
                        ADD_VM_DEFAULTS,
                        {
                            'os_type': config.ENUMS['windows7']
                        }
                    ]
                }
            ]
        )
    ),
    polarion("RHEVM3-12384")(
        pytest.mark.skipif(config.NO_STORAGE, reason=config.NO_STORAGE_MSG)(
            [
                {
                    "disk_on_specific_storage_domain": "Add vm with disk on "
                                                       "specific storage "
                                                       "domain"
                },
                {},
                {
                    (1, config.CREATE): [
                        ADD_VM_DEFAULTS, {
                            'storagedomain': config.MASTER_DOM,
                            'disk_type': config.DISK_TYPE_DATA,
                            'provisioned_size': config.GB * 2,
                            'interface': config.INTERFACE_VIRTIO,
                        }
                    ]
                }
            ]
        )
    ),
    polarion("RHEVM3-12519")(
        pytest.mark.skipif(config.NO_STORAGE, reason=config.NO_STORAGE_MSG)(
            [
                {"specific_domain": "Add vm with specific domain"},
                {},
                {
                    (1, config.CREATE): [
                        ADD_VM_DEFAULTS,
                        {
                            'storagedomain': config.MASTER_DOM,
                            'disk_type': config.DISK_TYPE_DATA
                        }
                    ]
                }
            ]
        )
    ),
    polarion("RHEVM3-12386")(
        [
            {
                "name_that_already_exist": "Add vm with name that already in "
                                           "use"
            },
            {},
            {
                (1, config.CREATE): [ADD_VM_DEFAULTS, {}],
                (2, config.CREATE): [
                    ADD_VM_DEFAULTS, {
                        "positive": False
                    }
                ]
            }
        ]
    ),
    polarion("RHEVM3-12521")(
        [
            {
                "wrong_number_of_displays": "Add vm with wrong number of "
                                            "displays"
            },
            {},
            {
                (1, config.CREATE): [
                    ADD_VM_DEFAULTS,
                    {
                        "positive": False,
                        'monitors': 36
                    }
                ]
            }
        ]
    ),
    polarion("RHEVM3-14952")(
        [
            {
                "add_vm_with_wrong_name": "Add vm with wrong name use special"
                                          " characters"
            },
            {},
            {
                (1, config.CREATE): [
                    ADD_VM_DEFAULTS,
                    {
                        "positive": False,
                        'vmName': "wrong_name+*////*_VM"
                    }
                ]
            }
        ]
    ),
    polarion("RHEVM3-14953")(
        pytest.mark.skipif(config.PPC_ARCH, reason=config.PPC_SKIP_MESSAGE)(
            [
                {
                    "add_and_remove_win_vm_name_long": "Add vm with windows os"
                                                       " and nome long the 40 "
                                                       "characters"
                },
                {},
                {
                    (1, config.CREATE): [
                        ADD_VM_DEFAULTS,
                        {
                            'vmName': 'a' * 40,
                            "os_type": config.ENUMS['windows7']
                        }
                    ]
                }
            ]
        )
    ),
    polarion("RHEVM3-17023")(
        [
            {
                "vm_with_wrong_length_name": "Add vm with name longer then 65"
                                             " characters"
            },
            {},
            {
                (1, config.CREATE): [
                    ADD_VM_DEFAULTS,
                    {
                        "positive": False,
                        'vmName': 'a' * 66
                    }
                ]
            }
        ]
    ),
    polarion("RHEVM3-15002")(
        [
            {
                "add_vm_with_long_name_crud": "Add vm with name equals to 64 "
                                              "characters check that we can "
                                              "update, run, remove  VM"
            },
            {},
            {
                (1, config.CREATE): [
                    ADD_VM_DEFAULTS,
                    {
                        "vmName": 'a' * 64,
                        "cluster": config.CLUSTER_NAME[0],
                        "template": config.TEMPLATE_NAME[0]
                    }
                    ],
                (2, config.UPDATE, True, 'a' * 64): {
                    "description": "TEST"
                },
                (3, config.START, 'a' * 64): True,
                (4, config.REMOVE, 'a' * 64): True
            }
        ]
    ),

]
