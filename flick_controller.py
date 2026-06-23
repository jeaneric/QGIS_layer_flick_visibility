"""Per-group flick state: shows exactly one included node at a time.

This class holds *no* timer and *no* run state of its own. It is driven by the
:class:`FlickCoordinator`, which owns the single shared clock so that several
groups stay perfectly in sync. Visibility is toggled through
``QgsLayerTreeNode.setItemVisibilityChecked``; changing layer-tree node
visibility refreshes the map canvas automatically via the project's
layer-tree -> map-canvas bridge, so no manual canvas refresh is required.
"""

from qgis.PyQt.QtCore import QObject, pyqtSignal


class FlickController(QObject):
    """Tracks one group's included nodes and which one is currently shown."""

    # name, position (1-based), total
    current_changed = pyqtSignal(str, int, int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._group = None      # parent QgsLayerTreeGroup
        self._nodes = []        # included QgsLayerTreeNode subset, in order
        self._shown = None      # index currently shown, or None

    def count(self):
        return len(self._nodes)

    def prepare(self, group_node, included_nodes):
        """Latch the node set and hide everything, ready for the first tick."""
        self._group = group_node
        self._nodes = [n for n in included_nodes if n is not None]
        self._shown = None

        # The parent group must be visible or none of its children render.
        try:
            if self._group is not None:
                self._group.setItemVisibilityChecked(True)
        except RuntimeError:
            pass
        self._hide_all_children()

    def apply_index(self, idx):
        """Show node ``idx`` (wrapped), hiding the previously shown one."""
        if not self._nodes:
            return
        idx = idx % len(self._nodes)
        if idx == self._shown:
            return
        if self._shown is not None:
            try:
                self._nodes[self._shown].setItemVisibilityChecked(False)
            except RuntimeError:
                pass
        node = self._nodes[idx]
        try:
            node.setItemVisibilityChecked(True)
            name = node.name()
        except RuntimeError:
            # Node was deleted from the tree underneath us; just record it.
            self._shown = idx
            return
        self._shown = idx
        self.current_changed.emit(name, idx + 1, len(self._nodes))

    # --------------------------------------------------------------- internals
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
