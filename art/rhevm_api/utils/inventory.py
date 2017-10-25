import logging
from pprint import pformat
import art.rhevm_api.utils.test_utils as utils

logger = logging.getLogger("art.inventory")


class Inventory(object):
    def __init__(self):
        self.resource_types_to_dump = [
            ('storagedomain', 'storagedomains', lambda x: x.storage_domain),
            ('host', 'hosts', lambda x: x),
            ('cluster', 'clusters', lambda x: x),
            ('data_center', 'datacenters', lambda x: x),
            ('vm', 'vms', lambda x: x),
            ('network', 'networks', lambda x: x),
            ('mac_pool', 'macpools', lambda x: x),
            ('template', 'templates', lambda x: x),
            ('disk', 'disks', lambda x: x),
            ('vnic_profile', 'vnicprofiles', lambda x: x),
        ]
        # List of resource names that we should ignore
        self.ignored_rsrc_names = ["OVF_STORE"]
        # List of attributes that we should ignore
        self.whitelisted_attr = [
            "used", "available",
            "actual_size", "committed",
            "stop_time", "total_size", "update_available"
        ]
        self._summary = {}

    def dump_ge_resource(self, resource_type):
        """Dumps into _summary the status of all resources of some type

        Args:
            resource_type (string, string, lamda x:x): For each resource
            type this tuple holds the necessary parameters we need to pass to
            get_api call to get the list of resources of that type.

        """
        logger.info("Dumping resource type %s" % resource_type[0])
        data = []
        current_resources = utils.get_api(
            resource_type[0], resource_type[1]
        ).get(abs_link=False)
        for resource in resource_type[2](current_resources):
            resource_attributes = dict(
                (mkey, getattr(resource, mkey))
                for mkey, mvalue in resource.member_data_items_.iteritems()
                if (mvalue.get_data_type().startswith("xs:") and
                    mkey not in self.whitelisted_attr)
            )
            resource_attributes['name'] = resource.name
            resource_attributes['id'] = resource.id

            data.append(resource_attributes)

        self._summary[resource_type[1]] = data

    def get_summary_report(self):
        """Creates a dictionary containing the current GE state

        Returns:
            dict: A dictionary with current GE-state summary

        """
        for resource_type in self.resource_types_to_dump:
            try:
                self.dump_ge_resource(resource_type)
            except Exception as e:
                logger.error(
                    "Failed to create GE-state summary for resource %s" %
                    resource_type
                )
                logger.error(e)

        logger.info("Dumped GE state is: %s", pformat(self._summary, indent=2))
        return self._summary

    def find_resources_diff(
        self, rsrc_old_state, rsrc_cur_state
    ):
        """Finds all resources of some resource type that changed

        Args:
            rsrc_old_state (dict): Old state of some resource of the GE
            rsrc_cur_state (dict): Current state of some resource of the GE

        Returns:
            (dict, dict, dict): A tuple of
            (resources_changed, resources_added, resources_removed).

        """
        resources_removed = []
        resources_changed = []
        copy_rsrc_cur_state = rsrc_cur_state[:]
        for resource_old in rsrc_old_state:
            resource_id = resource_old['id']
            resource_name = resource_old['name']
            for resource_cur in rsrc_cur_state:
                if resource_cur['id'] == resource_id:
                    copy_rsrc_cur_state.remove(resource_cur)
                    if cmp(resource_cur, resource_old) != 0:
                        changed_resource = self.find_params_changed(
                            resource_old, resource_cur
                        )
                        if changed_resource[1]:
                            resources_changed.append(changed_resource)
                    break
            else:
                resources_removed.append(resource_name)
        resources_added = [
            rsc['name']
            for rsc in copy_rsrc_cur_state
            if rsc['name'] not in self.ignored_rsrc_names
        ]

        return resources_changed, resources_added, resources_removed

    def find_params_changed(
        self, rsrc_old_state, rsrc_cur_state
    ):
        """Finds attributes of some resource that got changed

        Args:
            rsrc_old_state (dict): Old state of some resource of the GE
            rsrc_cur_state (dict): Current state of some resource of the GE

        Returns:
            dict: A dictionary containing the resources differences.

        """
        values_changed = dict()
        resource_name = rsrc_old_state['name']
        for rsrc_param, rsrc_param_val in rsrc_old_state.iteritems():
            if rsrc_param_val != rsrc_cur_state[rsrc_param]:
                values_changed[rsrc_param] = (
                    "old_value: %s, new_value: %s" %
                    (rsrc_param_val, rsrc_cur_state[rsrc_param])
                )
        return (resource_name, values_changed)

    def compare_ge_state(self, old_state, new_state):
        """Creates a dictionary containing the GE state diff

        Args:
            param old_state (dict): Old state of the GE
            param new_state (dict): Current state of the GE

        Returns:
            dict: A dictionary containd the GE state differences.

        """
        diff_dict = dict()
        for resource_type_tpl in self.resource_types_to_dump:
            resource_type = resource_type_tpl[1]
            diff_dict[resource_type] = dict()

            resources_changed, resources_added, resources_removed = (
                self.find_resources_diff(
                    old_state[resource_type],
                    new_state[resource_type])
            )
            if resources_added:
                diff_dict[resource_type]['added'] = resources_added
            if resources_removed:
                diff_dict[resource_type]['removed'] = resources_removed
            if resources_changed:
                diff_dict[resource_type]['changed'] = resources_changed

            if not diff_dict[resource_type]:
                del diff_dict[resource_type]

        return diff_dict
