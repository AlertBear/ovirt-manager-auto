"""
Helper for otopi machine dialog parser
"""
import logging
import config as conf
import otopimdp.parser as otopi_parser
import art.test_handler.exceptions as errors


logger = logging.getLogger(__name__)


class OtopiParser(object):
    """
    Class to parse otopi machine dialog answers
    """
    @staticmethod
    def enable_machine_dialog(vds_resource):
        """
        Enable machine dialog environment variable on vds resource

        :param vds_resource: vds resource
        :type vds_resource: VDS
        """
        logger.info(
            "Enable machine parser environment variable on resource %s",
            vds_resource.fqdn
        )
        with vds_resource.executor().session() as vds_session:
            with vds_session.open_file(
                conf.HOSTED_ENGINE_ENV_DEFAULT, mode="w"
            ) as env_file:
                env_file.write(
                    'export environment="${environment} '
                    'DIALOG/dialect=str:machine"\n'
                )

    def start_parsing(self, vds_resource):
        """
        Start parse machine dialog HE deployment events on vds resource

        :param vds_resource: vds resource
        :type vds_resource: VDS
        :raise: HostedEngineException
        """
        with vds_resource.executor().session() as vds_session:
            he_deploy_command = vds_session.command(
                conf.HOSTED_ENGINE_DEPLOY_CMD
            )
            with he_deploy_command.execute(get_pty=True) as (
                stdin, stdout, stderr
            ):
                otopi_machine_parser = otopi_parser.MachineDialogParser(
                    input_=stdout, output=stdin
                )
                replyable_events = [
                    otopi_parser.CONFIRM_EVENT,
                    otopi_parser.QUERY_VALUE_EVENT,
                    otopi_parser.QUERY_STRING_EVENT,
                    otopi_parser.QUERY_MULTI_STRING_EVENT
                ]
                events_d = self._generate_events_dictionary(vds_resource)
                events_names_l = []
                while True:
                    event = otopi_machine_parser.next_event()
                    if event is None:
                        continue
                    event_attributes = event[otopi_parser.ATTRIBUTES_KEY]
                    for event_message in (
                        conf.ATTRIBUTE_RECORD, conf.ATTRIBUTE_NOTE
                    ):
                        message = event_attributes.get(event_message)
                        if message:
                            logger.info(message)
                    event_type = event[otopi_parser.TYPE_KEY]
                    if event_type not in replyable_events:
                        if event_type == otopi_parser.TERMINATE_EVENT:
                            break
                        continue
                    event_name = event_attributes[conf.EVENT_NAME]
                    events_names_l.append(event_name)
                    if "_PROCEED" in event_name:
                        event[otopi_parser.REPLY_KEY] = conf.ANSWER_YES
                    elif event_name in events_d:
                        event[otopi_parser.REPLY_KEY] = events_d[
                            event_name
                        ]
                    else:
                        if (
                            len(events_names_l) > 2 and
                            events_names_l[-1] ==
                            events_names_l[-2] ==
                            events_names_l[-3]
                        ):
                            raise errors.HostedEngineException(
                                "Unexpected event: %s" % event
                            )
                        else:
                            # Try to fill up with default
                            event[otopi_parser.REPLY_KEY] = conf.DEFAULT_ANSWER
                    otopi_machine_parser.send_response(event)
                rc = he_deploy_command.get_rc()
                if rc is not None and rc > 0:
                    raise errors.HostedEngineException(
                        "Failed to deploy hosted-engine on host %s" %
                        vds_resource.fqdn
                    )

    @staticmethod
    def _generate_events_dictionary(vds_resource):
        """
        Generate dictionary with answers for machine dialog events

        :param vds_resource: vds resource
        :type vds_resource: VDS
        :return: dictionary event_name: event_reply
        :rtype: dict
        """
        event_dictionary = dict()
        event_dictionary[
            "ovehosted_bridge_if"
        ] = vds_resource.get_network().find_int_by_ip(vds_resource.ip)
        event_dictionary["HOST_FIRST_HOST_ROOT_PASSWORD"] = conf.HOSTS_PW
        event_dictionary["OVEHOSTED_FORCE_CREATEVG"] = "Force"
        return event_dictionary
