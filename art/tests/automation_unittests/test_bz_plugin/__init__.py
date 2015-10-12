__author__ = 'ncredi'

import logging
from bugzilla import Bugzilla44
from bugzilla.bug import _Bug

from art.test_handler.plmanagement.plugins.bz_plugin import (
    BugNotFound,
    INFO_TAGS,
)
from art.test_handler.settings import initPlmanager

logger = logging.getLogger(__name__)


class FakeBugs(object):

    def __init__(self):
        self.cache = {}
        self.bugzilla = Bugzilla44(url='faceBzUrl')

    def bz(self, bz_id):
        """
        Set all BZs as solved if BZ plugin is not available
        """
        if bz_id == '1':
            bug_dict = {
                "bug_id": 1,
                "product": 'dont care at this point',
                "version": ['3.5'],
                "resolution": '',
                "bug_status": 'NEW',
                "target_release": None,
                "component": ['component_1'],
            }
        elif bz_id == '2':
            bug_dict = {
                "bug_id": 2,
                "product": 'dont care at this point',
                "version": ['3.4', '3.5'],
                "resolution": '',
                "bug_status": 'ON_QA',
                "target_release": None,
                "component": ['component_2'],
            }
        elif bz_id == '3':
            bug_dict = {
                "bug_id": 3,
                "product": 'dont care at this point',
                "version": ['3.4', '3.5'],
                "resolution": '',
                "bug_status": 'ON_QA',
                "target_release": ['3.6'],
                "component": ['component_3'],
            }
        elif bz_id == '4':
            bug_dict = {
                "bug_id": 4,
                "product": 'dont care at this point',
                "version": ['3.5'],
                "resolution": 'CURRENTRELEASE',
                "bug_status": 'VERIFIED',
                "target_release": ['3.5'],
                "component": ['component_4'],
            }
        elif bz_id == '5':
            bug_dict = {
                "bug_id": 5,
                "product": 'dont care at this point',
                "version": ['3.5'],
                "resolution": '',
                "bug_status": 'CLOSED',
                "target_release": ['3.6'],
                "component": ['component_5'],
            }
        elif bz_id == '6':
            bug_dict = {
                "bug_id": 6,
                "product": 'dont care at this point',
                "version": ['3.5.1'],
                "resolution": 'DUPLICATE',
                "bug_status": 'CLOSED',
                "target_release": None,
                "dupe_of": '1',
                "component": ['component_6'],
            }
        elif bz_id == '7' or bz_id == '8':
            bug_dict = {
                "bug_id": 7,
                "product": 'dont care at this point',
                "version": ['1.0'],
                "resolution": '',
                "bug_status": 'CLOSED',
                "target_release": ['1.0'],
                "component": ['component_7'],
            }
        elif bz_id == '10':
            bug_dict = {
                "bug_id": 10,
                "product": 'dont care at this point',
                "version": ['1.0'],
                "resolution": '',
                "bug_status": 'NEW',
                "target_release": ['1.0'],
                "component": ['component_10'],
            }
        elif bz_id == '11':
            bug_dict = {
                "bug_id": 11,
                "product": 'dont care at this point',
                "version": ['3.5'],
                "resolution": 'CURRENTRELEASE',
                "bug_status": 'VERIFIED',
                "target_release": ['3.5'],
                "component": ['component_11'],
            }
        else:
            raise BugNotFound(bz_id)

        bug_dict["assigned_to"] = 'dontcare@redhat.com'
        bug_dict["summary"] = 'no summary'

        bug = _Bug(dict=bug_dict, autorefresh=False, bugzilla=self.bugzilla)

        msg = "BUG<%s> info: %s" % (bz_id, dict((x, getattr(bug, x)) for x in
                                    INFO_TAGS if hasattr(bug, x)))
        logger.info(msg)
        return bug


def setup_package():
    plmanager = initPlmanager()
    BZ_PLUGIN = [
        pl for pl in plmanager.application_liteners if pl.name == "Bugzilla"
    ][0]
    BZ_PLUGIN.bz = FakeBugs().bz
