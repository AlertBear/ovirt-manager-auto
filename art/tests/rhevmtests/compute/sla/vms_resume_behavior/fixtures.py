"""
Resume Behavior test fixtures
"""
import pytest
import art.unittest_lib as u_libs
import helpers
import config as conf
from concurrent.futures import ThreadPoolExecutor


@pytest.fixture()
def block_unblock_storage(request):
    """
    1) Block the Storage
    2) Wait for I/O error
    3) Wait for interval=sleep_after_io_error before unblocking the storage.
       This wait interval for 'KILL' must be not less than 80 sec (engine
       implementation. For other options - leave_paused and auto_resume - it
       must not be 80. The default for tests is 10 sec)
    4) Unblock the Storage
    """
    vms_to_pause = request.node.cls.vms_to_pause
    sleep_after_io_error = request.getfixturevalue("sleep_after_io_error")
    results = []
    with ThreadPoolExecutor(
        max_workers=len(conf.RESUME_BEHAVIOR_VMS)
    ) as executor:
        for item in vms_to_pause:
            u_libs.testflow.setup(
                "Block storage for VM %s. Wait for %s after getting I/O error."
                "Unblock storage", item, sleep_after_io_error
            )
            results.append(
                executor.submit(
                    helpers.block_unblock_storage_for_threadpool,
                    sleep_after_io_error=sleep_after_io_error,
                    vm=item
                )
            )
    for result in results:
        if result.exception():
            raise result.exception()
