# -*- coding: utf-8 -*-

from art.test_handler.plmanagement import *
from art.test_handler.plmanagement.interfaces.input_reader import IInputListener
from art.test_handler.plmanagement.interfaces.application import IApplicationListener


class ActionUglyPrinter(Component):
    implements(IInputListener)

    def on_next_action(self, action):
        print "Uggly printing:", self, action


class ActionPrettyPrinter(Component, IApplicationListener):
    implements(IInputListener, IApplicationListener)

    def on_next_action(self, action):
        TITLE = "The next action is:"
        boxwidth = max(len(s) + 4 for s in (TITLE, action))
        print "░" * boxwidth
        print '░\x1b[7m {} \x1b[27m░'.format(TITLE.center(boxwidth - 4))
        print "░ {} ░".format(action.center(boxwidth - 4))
        print "░" * boxwidth
        print

    def on_application_start(self):
        print "=========== Hello ============"

    def on_application_exit(self):
        "========== Bye bye ==========="

    @classmethod
    def is_enabled(cls, params, conf):
        return False
