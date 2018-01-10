import json
import logging
import os
import requests
from multiprocessing import Process, Manager
from time import sleep

from art.core_api.apis_exceptions import APITimeout
from art.rhevm_api.tests_lib.low_level import vms as ll_vms

import config

ACCEPTABLE_STATUSES = {"ok": 200, "mna": 405}
# Main actions to look at Hystrix log
ACTIONS = [
    "GetVmByVmId", "SearchVmTemplate",
    "SearchVM", "RunVm",
    "RemoveAllVmImages", "AddVm",
    "RemoveVm", "UpdateVm"
]
# Main vdsm commands to look at Hystrix log
VDSM_COMMANDS = [
    "VdsSetVmStatus", "VdsDestroyVm",
    "VdsCreate", "VdsGetAllVmStats"
]

logger = logging.getLogger(__name__)
HYSTRIX_WAIT = 60


def functor(f, collection):
    """
    Description:
        Applies a given function to a given collection.
    Args:
        collection (list): Collection of function arguments.
    """
    processes = {}
    for element in collection:
        processes[element] = Process(target=f, args=(element,))
        processes[element].start()
    for process in processes.values():
        process.join()


def init_pipe(pipe):
    """
    Description:
        Creates a message pipe (file).
    Args:
        pipe (str): Pipe's path.
    """
    fd = os.open(pipe, os.O_CREAT | os.O_SYNC)
    os.close(fd)


def init_pipes(pipes):
    """
    Description:
        Creates pipes by given paths.
    Args:
        pipes (list[str]): List of pipes pathes.
    """
    functor(init_pipe, pipes)


def cleanup_pipe(pipe):
    """
    Description:
        Removes given pipe.
    Args:
        pipe (str): Pipe's path.
    """
    os.remove(pipe)


def cleanup_pipes(pipes):
    """
    Description:
        Removes given pipes.
    Args:
        pipes (list[str]): List of pipes pathes.
    """
    functor(cleanup_pipe, pipes)


def write_message(input_pipe, message):
    """
    Description:
        Writes a message to a file descriptor in non-blocking way.
    Args:
        input_pipe (str): Message passing pipe (file path).
        message (str): Message to send.
    """
    logger.info("Writing message '%s' to pipe %s", message, input_pipe)
    fd = os.open(input_pipe, os.O_WRONLY | os.O_NONBLOCK | os.O_TRUNC)
    os.write(fd, message)
    os.close(fd)
    logger.info("\tDONE")


def read_message(input_pipe):
    """
    Description:
        Reads a message from given message pipe in non-blocking way.
    Args:
        input_pipe (str): Message passing pipe (file path).
    Returns:
        str: Message from pipe.
    """
    logger.info("Reading message...")
    fd = os.open(input_pipe, os.O_RDONLY | os.O_NONBLOCK)
    message = os.read(fd, 22)
    logger.info("\tMessage '%s'", message)
    os.close(fd)
    return message


def check_hystrix_status():
    """
    Description:
       Checks if ovirt Hystrix stream is alive.
    Raises:
       requests.HTTPError: If GET stream url returns either not HTTP 200 or
           HTTP 405, there's something wrong so it's better to raise and fail
           here.
    Returns:
       bool: True if GET stream url returns HTTP 200, False otherwise.
    """
    status_code = int(requests.get(
        config.hystrix_stream_url,
        auth=(
            config.hystrix_auth_user,
            config.VDC_PASSWORD
        ),
        stream=True,
        verify=False
    ).status_code)

    if status_code not in ACCEPTABLE_STATUSES.values():
        raise requests.HTTPError(
            "Something really bad happen. Wrong status: {}!".format(
                status_code
            )
        )
    else:
        return status_code == ACCEPTABLE_STATUSES["ok"]


def get_hystrix_stream_commands(d):
    """
    Description:
        Fills given dictionary with all catched Hystrix command names.
    Args:
        d (multiprocessing.Manager.dict): Process-safe dictionary.
    """
    req = requests.get(
        config.hystrix_stream_url,
        auth=(
            config.hystrix_auth_user,
            config.VDC_PASSWORD
        ),
        stream=True,
        verify=False
    )
    for line in req.iter_lines():
        try:
            event_message = read_message(config.event_pipe)
            status_message = read_message(config.status_pipe)
        except IOError as err:
            logger.error(err)

        if line and line.startswith("data"):
            hystrix_command_name = json.loads(line[5:])["name"]

            logger.info(
                "For hystrix command {command} we have event message '{event}'"
                " and status message '{status}'".format(
                    command=hystrix_command_name,
                    event=event_message,
                    status=status_message
                )
            )

            if event_message != "done" and status_message != "err":
                d[hystrix_command_name] = True
            else:
                break


def generate_events():
    """
    Description:
        Generates events on engine and writes messages into a Hystrix pipe.
    """
    write_message(config.event_pipe, "creating_vm")
    res = ll_vms.createVm(
        positive=True,
        vmName=config.HYSTRIX_VM_NAME,
        cluster=config.CLUSTER_NAME[0],
        template=config.TEMPLATE_NAME[0],
        provisioned_size=config.gb,
    )
    write_message(config.status_pipe, "ok" if res else "err")

    write_message(config.event_pipe, "starting_vm")
    res = ll_vms.startVm(
        positive=True,
        vm=config.HYSTRIX_VM_NAME,
        wait_for_status=config.VM_UP,
        wait_for_ip=False,
        placement_host=config.HOSTS[0]
    )
    write_message(config.status_pipe, "ok" if res else "err")

    write_message(config.event_pipe, "stopping_vm")
    res = ll_vms.stopVm(positive=True, vm=config.HYSTRIX_VM_NAME)
    if not res:
        try:
            ll_vms.wait_for_vm_states(
                vm_name=config.HYSTRIX_VM_NAME,
                states=[config.VM_DOWN]
            )
        except APITimeout:
            write_message(config.status_pipe, "err")
    else:
        write_message(config.status_pipe, "ok")

    write_message(config.event_pipe, "removing_vm")
    res = ll_vms.removeVm(
        positive=True,
        vm=config.HYSTRIX_VM_NAME,
        wait=True
    )
    write_message(config.status_pipe, "ok" if res else "err")

    sleep(HYSTRIX_WAIT)
    write_message(config.event_pipe, "done")


def check_hystrix_monitoring():
    """
    Description:
        Checks if Hystrix monitors engine and vdsm events properly.
    Throws:
        assertion error: check that all actions are logged in hystrix
    """
    manager = Manager()

    d = manager.dict()

    events_generator = Process(target=generate_events)
    dict_builder = Process(target=get_hystrix_stream_commands, args=(d,))

    events_generator.start()
    dict_builder.start()

    events_generator.join()
    dict_builder.join()

    for action in ACTIONS:
        assert d.get(action, False), (
            "Failed to get action {}".format(action)
        )
    for vdsm_command in VDSM_COMMANDS:
        assert d.get(vdsm_command, False), (
            "Failed to get vdsm command {}".format(vdsm_command)
        )
