"""Flick engine: cycles visibility across layer-tree nodes on a timer.

Kept free of any UI code so it can be reused/tested independently. Visibility is
toggled through ``QgsLayerTreeNode.setItemVisibilityChecked``; changing layer-tree
node visibility refreshes the map canvas automatically via the project's
layer-tree -> map-canvas bridge, so no manual canvas refresh is required.
"""

from qgis.PyQt.QtCore import QObject, QTimer, pyqtSignal

# Controller states
STOPPED = "stopped"
RUNNING = "running"
PAUSED = "paused"


class FlickController(QObject):
    """Steps through a list of included layer-tree nodes one at a time."""

    # name, position (1-based), total
    current_changed = pyqtSignal(str, int, int)
    # one of STOPPED / RUNNING / PAUSED
    state_changed = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._advance)
        self._group = None      # parent QgsLayerTreeGroup
        self._nodes = []        # included QgsLayerTreeNode subset, in order
        self._index = 0
        self._interval_ms = 2000
        self._state = STOPPED

    # ------------------------------------------------------------------ state
    @property
    def state(self):
        return self._state

    def _set_state(self, state):
        if state != self._state:
            self._state = state
            self.state_changed.emit(state)

    # --------------------------------------------------------------- controls
    def start(self, group_node, included_nodes, interval_seconds):
        """Begin cycling. Returns True if started, False if nothing to show."""
        nodes = [n for n in included_nodes if n is not None]
        if not nodes:
            return False
        self._group = group_node
        self._nodes = nodes
        self._interval_ms = max(100, int(round(interval_seconds * 1000)))
        self._index = 0

        # The parent group must be visible or none of its children render.
        try:
            if self._group is not None:
                self._group.setItemVisibilityChecked(True)
        except RuntimeError:
            pass

        self._hide_all_children()
        self._show_current()
        self._timer.start(self._interval_ms)
        self._set_state(RUNNING)
        return True

    def step(self, delta):
        """Move ``delta`` items (e.g. +1 Next, -1 Previous), wrapping around."""
        if not self._nodes:
            return
        self._hide_current()
        self._index = (self._index + delta) % len(self._nodes)
        self._show_current()
        if self._state == RUNNING:
            # Restart so a full interval elapses after a manual jump.
            self._timer.start(self._interval_ms)

    def pause(self):
        if self._state != RUNNING:
            return
        self._timer.stop()
        self._set_state(PAUSED)

    def resume(self):
        if self._state != PAUSED:
            return
        self._timer.start(self._interval_ms)
        self._set_state(RUNNING)

    def stop(self):
        """Stop cycling. Current visibility is left as-is by design."""
        self._timer.stop()
        self._set_state(STOPPED)

    # --------------------------------------------------------------- internals
    def _advance(self):
        self.step(1)

    def _hide_all_children(self):
        """Hide every first-level child of the group, even excluded ones."""
        children = self._nodes
        if self._group is not None:
            try:
                children = self._group.children()
            except RuntimeError:
                children = self._nodes
        for node in children:
            try:
                node.setItemVisibilityChecked(False)
            except RuntimeError:
                pass

    def _hide_current(self):
        if not self._nodes:
            return
        try:
            self._nodes[self._index].setItemVisibilityChecked(False)
        except RuntimeError:
            pass

    def _show_current(self):
        if not self._nodes:
            return
        node = self._nodes[self._index]
        try:
            node.setItemVisibilityChecked(True)
            name = node.name()
        except RuntimeError:
            # Node was deleted from the tree underneath us.
            self.stop()
            return
        self.current_changed.emit(name, self._index + 1, len(self._nodes))
