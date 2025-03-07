import threading
class UpdaterThread:
    """
    Non-blocking update mechanism using threading.Timer.
    - start(): Begin repeated manager.update() calls
    - stop():  Stop further updates
    - reinit(times, interval): Reconfigure and reset counters
    """

    def __init__(self, manager, times=0, interval=1):
        """
        :param manager:   The object that has an .update() method.
        :param times:     How many times to call update() before stopping.
                          If times=0, update() repeats indefinitely.
        :param interval:  Seconds between calls.
        """
        self.manager = manager
        self.times = times
        self.interval = interval
        self.count = 0

        self._timer = None     # Holds the active Timer object
        self._running = False  # Indicates if updates are active

    def start(self):
        """
        Start (or restart) scheduling updates in a non-blocking way.
        Resets count if needed.
        """
        if self._running:
            # Already running, do nothing or reset if you'd like
            return

        self._running = True
        self.count = 0  # Reset the counter each time we start
        self._schedule_update()

    def stop(self):
        """
        Stop scheduling further updates.
        """
        self._running = False
        if self._timer is not None:
            self._timer.cancel()  # Cancel any scheduled call
            self._timer = None

    def reinit(self, times, interval):
        """
        Change times and interval, and reset the counter.
        If already running, it continues with the new settings 
        from the next scheduling cycle.
        """
        self.times = times
        self.interval = interval
        self.count = 0

    def _schedule_update(self):
        """
        Internal method to schedule the next update call.
        Called automatically after each update to set the next Timer.
        """
        # If we're no longer running, do nothing
        if not self._running:
            print("UpdaterThread stopped.")
            return

        # If times != 0 and we've reached the limit, stop
        if self.times != 0 and self.count >= self.times:
            print("Done updating manager non-blocking.")
            self.stop()
            return

        # Perform the update
        self.manager.render()
        self.count += 1

        # Schedule the next update
        self._timer = threading.Timer(self.interval, self._schedule_update)
        self._timer.daemon = True
        self._timer.start()

