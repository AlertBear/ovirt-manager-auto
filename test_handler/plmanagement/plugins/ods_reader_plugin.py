from test_handler.plmanagement import Component, ExtensionPoint, implements
from test_handler.plmanagement.interfaces.input_reader import IInputListener, IInputProducer

class ODSReader(Component):
    implements(IInputProducer)
    reader_listeners = ExtensionPoint(IInputListener)

    def __init__(self):
        self.input_path = None
        self.ready = True

    def on_next_action_reqest(self):
        self.read()

    def read(self):
        for a in '''ODS_ACTION_1 ODS_ACTION_2 ODS_ACTION_3 ODS_ACTION_4
                    VERY_LONG_ACTION_SPECIFIER'''.split():
            for observer in self.reader_listeners:
                observer.on_next_action(a)
        self.ready = False

    @classmethod
    def is_enabled(cls, params, conf):
        return False
