"""
This module is responsible to collect some leftovers in the GEs,
e.g. Clusters, Storages, Vms etc, after each team's package finishes
and store them into a json file
"""

import json
import logging

__all__ = [
    "pytest_addoption",
    "pytest_configure",
]

logger = logging.getLogger("pytest.art.leftovers")


class LeftoversInfo(object):
    """
    Collection of hooks that are going to be used to GE state dumping.
    Here we will gather all information we need for the leftovers
    report file and generate the report.
    """
    def __init__(self):
        self.summary = dict()
        self.ge_state = dict()
        self.team = None

    def _get_inventory_instance(self):
        """
        The inventory module should not be imported at module level
        since data structures are not generated at that time
        """
        from art.rhevm_api.utils.inventory import Inventory
        return Inventory()

    def pretty_print_ge_state_report(self):
        """
        Shows GE state information in the form of tables per resource type
        using tabulate module
        """
        # Filter ge_state dict and create a short GE state summary
        short_report_attrs = ["name", "status"]
        ignore_rsrc_names = ["OVF_STORE"]
        short_summary = {}
        for resource_type in self.ge_state:
            short_summary[resource_type] = []
            resource_obj_list = self.ge_state[resource_type]
            for resource in resource_obj_list:
                if ('name' in resource and
                        resource['name'] in ignore_rsrc_names):
                    continue
                resource_dict = {}
                attr_gen = (attr for attr in short_report_attrs
                            if attr in resource)
                for attr in attr_gen:
                    resource_dict[attr] = resource[attr]
                short_summary[resource_type].append(resource_dict)

        from tabulate import tabulate
        logger.info(
            "Printing GE State before team's %s package execution", self.team
        )
        full_short_summary = []
        for resource_type in short_summary:
            full_short_summary.append(
                "\n{}\n{}\n{}".format(
                    resource_type.title(),
                    len(resource_type)*"*",
                    tabulate(
                        short_summary[resource_type],
                        headers="keys", tablefmt='orgtbl'
                    )
                )
            )
        logger.info("\n".join(full_short_summary))

    def pytest_rhv_setup(self, team):
        """
        Get dict containing GE description at package setup
        """
        if self.team:
            logger.info(
                "Calling pytest_rhv_teardown for previous team execution"
            )
            self.pytest_rhv_teardown(self.team)

        logger.info("Running pytest_rhv_setup for %s team", team)
        inventory = self._get_inventory_instance()
        self.ge_state = inventory.get_summary_report()
        self.team = team
        self.pretty_print_ge_state_report()

    def pytest_rhv_teardown(self, team):
        """
        Get dict containing GE description at package teardown
        Compare this dict with the one that was fetched in package setup,
        create some difference and store it in json file.
        """
        logger.info("Running pytest_rhv_teardown for %s team", team)
        inventory = self._get_inventory_instance()
        new_ge_state = inventory.get_summary_report()
        diff_summary = {}
        diff_summary = inventory.compare_ge_state(
            self.ge_state, new_ge_state)
        self.summary[team] = diff_summary

    def pytest_unconfigure(self, config):
        """
        When whole test run finishes write the summary into file
        into json format.
        """
        if self.team:
            logger.info("Calling pytest_rhv_teardown for last team execution")
            self.pytest_rhv_teardown(self.team)

        with open(config.option.leftovers_file, 'w') as fp:
            json.dump(self.summary, fp, indent=4)


def pytest_addoption(parser):
    parser.addoption(
        '--leftovers-report', dest="leftovers_report",
        action="store_true", default=False,
        help="show leftovers info into json format",
    )
    parser.addoption(
        '--leftovers-file', dest="leftovers_file",
        type=str, default=None, metavar="path",
        help="create a json style report file at given path (only valid when "
        "leftovers_report option is enabled)"
    )


def pytest_configure(config):
    """
    Load the test leftovers plugin into pytest
    """
    if not config.getoption('leftovers_report'):
        return
    config.pluginmanager.register(LeftoversInfo())
