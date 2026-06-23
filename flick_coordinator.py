"""Shared clock that keeps several group flicks synchronised.

A single :class:`~qgis.PyQt.QtCore.QTimer` ticks at the *base* interval. Every
registered group advances on the global tick timeline at a whole-number
*multiplier* of that base, so all groups stay in lockstep:

    group index at tick ``t`` = (t // multiplier) % item_count

The base group always uses multiplier 1; an added group with multiplier ``N``
advances once every ``N`` base intervals. Modelling each group's index purely as
a function of the global ``tick`` makes manual stepping (Prev/Next) just
``tick += delta`` followed by a recompute, which can never drift out of sync.
"""

from qgis.PyQt.QtCore import QObject, QTimer, pyqtSignal

# Coordinator states
STOPPED = "stopped"
RUNNING = "running"
PAUSED = "paused"


class FlickCoordinator(QObject):
    """Owns the timer and the global tick that all groups derive their index from."""

    state_changed = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._on_tick)
        self._entries = []      # list of (FlickController, multiplier)
        self._base_ms = 2000
        self._tick = 0
        self._state = STOPPED

    @property
    def state(self):
        return self._state

    def _set_state(self, state):
        if state != self._state:
            self._state = state
            self.state_changed.emit(state)

    # --------------------------------------------------------------- controls
    def start(self, base_interval_seconds, entries):
        """Begin cycling. ``entries`` is a list of (controller, multiplier).

        Controllers must already be prepared (node set latched). Returns True if
        anything was started.
        """
        self._entries = [
            (c, max(1, int(m))) for c, m in entries if c.count() > 0
        ]
        if not self._entries:
            return False
        self._base_ms = max(100, int(round(base_interval_seconds * 1000)))
        self._tick = 0
        self._apply_all()
        self._timer.start(self._base_ms)
        self._set_state(RUNNING)
        return True

    def step(self, delta):
        """Move the whole timeline by ``delta`` base ticks (Prev/Next)."""
        if not self._entries:
            return
        self._tick += delta
        self._apply_all()
        if self._state == RUNNING:
            # Restart so a full base interval elapses after a manual jump.
            self._timer.start(self._base_ms)

    def pause(self):
        if self._state != RUNNING:
            return
        self._timer.stop()
        self._set_state(PAUSED)

    def resume(self):
        if self._state != PAUSED:
            return
        self._timer.start(self._base_ms)
        self._set_state(RUNNING)

    def stop(self):
        """Stop cycling. Current visibility is left as-is by design."""
        self._timer.stop()
        self._set_state(STOPPED)

    # --------------------------------------------------------------- internals
    def _on_tick(self):
        self._tick += 1
        self._apply_all()

    def _apply_all(self):
        for controller, multiplier in self._entries:
            count = controller.count()
            if count <= 0:
                continue
            controller.apply_index((self._tick // multiplier) % count)
