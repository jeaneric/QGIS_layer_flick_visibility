"""Shared clock that keeps several group flicks synchronised.

A single :class:`~qgis.PyQt.QtCore.QTimer` ticks at the *base* interval. Each
registered group keeps its own *phase* (a count of base ticks it has actually
experienced) and advances at a whole-number *multiplier* of the base:

    group index = (phase // multiplier) % item_count

On every tick only groups that are not individually paused bump their phase, so
one group can be frozen while the rest keep moving and nothing drifts out of
sync. The base group always uses multiplier 1; an added group with multiplier
``N`` advances once every ``N`` base intervals.

There are two independent levels of pausing:

* the **master** Pause/Resume (this coordinator's state) stops the timer, so
  nothing advances; and
* a **per-group** pause (``set_group_paused``) that freezes a single group while
  the master clock keeps running for the others.
"""

from qgis.PyQt.QtCore import QObject, QTimer, pyqtSignal

# Coordinator (master) states
STOPPED = "stopped"
RUNNING = "running"
PAUSED = "paused"


class _Entry:
    """Per-group bookkeeping held by the coordinator while running."""

    __slots__ = ("controller", "multiplier", "paused", "phase")

    def __init__(self, controller, multiplier):
        self.controller = controller
        self.multiplier = max(1, int(multiplier))
        self.paused = False
        self.phase = 0


class FlickCoordinator(QObject):
    """Owns the timer; advances each non-paused group on the shared tick."""

    state_changed = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._on_tick)
        self._entries = []
        self._base_ms = 2000
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
            _Entry(c, m) for c, m in entries if c.count() > 0
        ]
        if not self._entries:
            return False
        self._base_ms = max(100, int(round(base_interval_seconds * 1000)))
        self._apply_all()
        self._timer.start(self._base_ms)
        self._set_state(RUNNING)
        return True

    def step(self, delta):
        """Move every non-paused group by ``delta`` base ticks (Prev/Next)."""
        if not self._entries:
            return
        for entry in self._entries:
            if not entry.paused:
                entry.phase += delta
        self._apply_all()
        if self._state == RUNNING:
            # Restart so a full base interval elapses after a manual jump.
            self._timer.start(self._base_ms)

    def pause(self):
        """Master pause: stop the timer so every group freezes."""
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

    def set_group_paused(self, controller, paused):
        """Freeze or unfreeze a single group while the master clock runs."""
        for entry in self._entries:
            if entry.controller is controller:
                entry.paused = bool(paused)
                return

    # --------------------------------------------------------------- internals
    def _on_tick(self):
        for entry in self._entries:
            if not entry.paused:
                entry.phase += 1
        self._apply_all()

    def _apply_all(self):
        for entry in self._entries:
            count = entry.controller.count()
            if count <= 0:
                continue
            entry.controller.apply_index((entry.phase // entry.multiplier) % count)
