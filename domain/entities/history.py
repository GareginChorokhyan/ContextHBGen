class History:
    def __init__(self):
        self._events = []

    def record_event(self, event):
        self._events.append(event)

    def get_history(self):
        return self._events
