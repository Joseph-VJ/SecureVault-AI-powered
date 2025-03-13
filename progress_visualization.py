class ProgressTracker:
    def __init__(self):
        self.callback = None

    def set_callback(self, callback):
        """Set a callback function to update the GUI."""
        self.callback = callback

    def update_progress(self, processed, total):
        """Update progress and call the callback if set."""
        if self.callback:
            self.callback(processed, total)