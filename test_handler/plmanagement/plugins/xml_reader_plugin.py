from test_handler.plmanagement import *      # Note that test_handler.plmanagement is star-friendly.
from test_handler.plmanagement.interfaces.input_reader import IInputListener, IInputProducer

class XMLReader(Component):
    implements(IInputProducer)
    reader_listeners = ExtensionPoint(IInputListener)

    def __init__(self):
        self.input_path = None
        self.ready = True

    def on_next_action_reqest(self):
        self.read()

    def read(self):
        for a in 'XML_ACTION_1 XML_ACTION_2 XML_ACTION_3 XML_ACTION_4'.split():
            for observer in self.reader_listeners:
                observer.on_next_action(a)
        self.ready = False

    @classmethod
    def is_enabled(cls, params, conf):
        return False
