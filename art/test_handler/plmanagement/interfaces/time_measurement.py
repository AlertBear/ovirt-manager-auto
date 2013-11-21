
from art.test_handler.plmanagement import Interface


class ITimeMeasurement(Interface):
    def on_start_measure(self): # needs add some parameters, to identify what started
        """Called when measure of something starts """

    def on_stop_measure(self, method_name, elapsed_time):
        """
        Called when measure of something stops
        Parameters:
            method name - name of caller method
            elapsed_time - float in seconds
        """

