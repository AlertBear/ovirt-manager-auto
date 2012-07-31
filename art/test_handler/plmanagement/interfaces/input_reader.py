from art.test_handler.plmanagement import Interface

class IInputListener(Interface):
    def on_next_action(self, action):
        """ Called when next action ready. """

class IInputProducer(Interface):
    def on_next_action_reqest(self):
        """ Called to get next action. """
