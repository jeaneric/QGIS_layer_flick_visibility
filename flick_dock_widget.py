"""Dockable options panel for the Layer Flick Visibility plugin."""

from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QComboBox,
    QPushButton,
    QToolButton,
    QListWidget,
    QListWidgetItem,
    QDoubleSpinBox,
    QLabel,
    QGroupBox,
)
from qgis.core import QgsProject, QgsLayerTreeGroup
from qgis.gui import QgsDockWidget

from .flick_controller import FlickController, STOPPED, RUNNING, PAUSED

# Role used to stash the layer-tree node object on combo/list items.
NODE_ROLE = Qt.UserRole + 1


class FlickDockWidget(QgsDockWidget):
    """Panel with group selection, per-item include list and transport buttons."""

    def __init__(self, iface, parent=None):
        super().__init__("Layer Flick Visibility", parent)
        self.iface = iface
        self.setObjectName("LayerFlickDockWidget")

        self.controller = FlickController(self)
        self._build_ui()
        self._connect()
        self.populate_groups()
        self._update_buttons(STOPPED)

    # ------------------------------------------------------------------- build
    def _build_ui(self):
        container = QWidget(self)
        root = QVBoxLayout(container)

        # --- Group selection -------------------------------------------------
        group_box = QGroupBox("Group", container)
        gl = QVBoxLayout(group_box)
        row = QHBoxLayout()
        self.group_combo = QComboBox(group_box)
        self.refresh_btn = QToolButton(group_box)
        self.refresh_btn.setText("↻")  # refresh glyph
        self.refresh_btn.setToolTip("Reload the list of groups from the project")
        row.addWidget(self.group_combo, 1)
        row.addWidget(self.refresh_btn, 0)
        gl.addLayout(row)
        root.addWidget(group_box)

        # --- Items / include list -------------------------------------------
        items_box = QGroupBox("Items to cycle (first level)", container)
        il = QVBoxLayout(items_box)
        self.items_list = QListWidget(items_box)
        self.items_list.setToolTip(
            "Checked items are included in the loop; uncheck to exclude."
        )
        il.addWidget(self.items_list)
        check_row = QHBoxLayout()
        self.check_all_btn = QPushButton("Check all", items_box)
        self.uncheck_all_btn = QPushButton("Uncheck all", items_box)
        check_row.addWidget(self.check_all_btn)
        check_row.addWidget(self.uncheck_all_btn)
        check_row.addStretch(1)
        il.addLayout(check_row)
        root.addWidget(items_box, 1)

        # --- Interval --------------------------------------------------------
        form = QFormLayout()
        self.interval_spin = QDoubleSpinBox(container)
        self.interval_spin.setRange(0.1, 60.0)
        self.interval_spin.setSingleStep(0.5)
        self.interval_spin.setDecimals(1)
        self.interval_spin.setValue(2.0)
        self.interval_spin.setSuffix(" s")
        form.addRow("Interval:", self.interval_spin)
        root.addLayout(form)

        # --- Transport row ---------------------------------------------------
        transport = QHBoxLayout()
        self.prev_btn = QPushButton("◀ Prev", container)
        self.play_btn = QPushButton("▶ Play", container)
        self.pause_btn = QPushButton("⏸ Pause", container)
        self.stop_btn = QPushButton("■ Stop", container)
        self.next_btn = QPushButton("Next ▶", container)
        for btn in (self.prev_btn, self.play_btn, self.pause_btn,
                    self.stop_btn, self.next_btn):
            transport.addWidget(btn)
        root.addLayout(transport)

        # --- Status ----------------------------------------------------------
        self.status_label = QLabel("Stopped.", container)
        self.status_label.setWordWrap(True)
        root.addWidget(self.status_label)

        self.setWidget(container)

    def _connect(self):
        self.refresh_btn.clicked.connect(self.populate_groups)
        self.group_combo.currentIndexChanged.connect(self._on_group_changed)
        self.check_all_btn.clicked.connect(lambda: self._set_all_checked(True))
        self.uncheck_all_btn.clicked.connect(lambda: self._set_all_checked(False))

        self.play_btn.clicked.connect(self._on_play)
        self.pause_btn.clicked.connect(self._on_pause_resume)
        self.stop_btn.clicked.connect(self.controller.stop)
        self.prev_btn.clicked.connect(lambda: self.controller.step(-1))
        self.next_btn.clicked.connect(lambda: self.controller.step(1))

        self.controller.current_changed.connect(self._on_current_changed)
        self.controller.state_changed.connect(self._update_buttons)

    # ------------------------------------------------------------- populating
    def populate_groups(self):
        """Walk the layer tree and list every group (nested included)."""
        self.controller.stop()
        self.group_combo.blockSignals(True)
        self.group_combo.clear()

        root = QgsProject.instance().layerTreeRoot()
        for group in self._iter_groups(root):
            label = self._group_path(group, root)
            self.group_combo.addItem(label)
            self.group_combo.setItemData(
                self.group_combo.count() - 1, group, NODE_ROLE
            )

        self.group_combo.blockSignals(False)
        if self.group_combo.count() == 0:
            self.items_list.clear()
            self.status_label.setText("No groups in this project.")
        else:
            self.group_combo.setCurrentIndex(0)
            self.populate_items()

    def _iter_groups(self, node):
        """Yield every QgsLayerTreeGroup below ``node`` (excluding the root)."""
        for child in node.children():
            if isinstance(child, QgsLayerTreeGroup):
                yield child
                yield from self._iter_groups(child)

    def _group_path(self, group, root):
        """Build an indented 'Parent / Child' label for a nested group."""
        parts = []
        node = group
        while node is not None and node is not root:
            parts.append(node.name())
            node = node.parent()
        return " / ".join(reversed(parts))

    def populate_items(self):
        """Fill the include list from the selected group's first-level children."""
        self.items_list.clear()
        group = self._current_group()
        if group is None:
            return
        try:
            children = group.children()
        except RuntimeError:
            return
        for node in children:
            item = QListWidgetItem(node.name())
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Checked)
            item.setData(NODE_ROLE, node)
            self.items_list.addItem(item)

    def _set_all_checked(self, checked):
        state = Qt.Checked if checked else Qt.Unchecked
        for i in range(self.items_list.count()):
            self.items_list.item(i).setCheckState(state)

    # --------------------------------------------------------------- accessors
    def _current_group(self):
        idx = self.group_combo.currentIndex()
        if idx < 0:
            return None
        return self.group_combo.itemData(idx, NODE_ROLE)

    def _included_nodes(self):
        nodes = []
        for i in range(self.items_list.count()):
            item = self.items_list.item(i)
            if item.checkState() == Qt.Checked:
                nodes.append(item.data(NODE_ROLE))
        return nodes

    # ----------------------------------------------------------------- actions
    def _on_group_changed(self, _index):
        self.controller.stop()
        self.populate_items()

    def _on_play(self):
        group = self._current_group()
        if group is None:
            self.iface.messageBar().pushWarning(
                "Layer Flick", "Select a group first."
            )
            return
        nodes = self._included_nodes()
        if not nodes:
            self.iface.messageBar().pushWarning(
                "Layer Flick", "No items are checked to cycle through."
            )
            return
        self.controller.start(group, nodes, self.interval_spin.value())

    def _on_pause_resume(self):
        if self.controller.state == RUNNING:
            self.controller.pause()
        elif self.controller.state == PAUSED:
            self.controller.resume()

    # ----------------------------------------------------------------- signals
    def _on_current_changed(self, name, position, total):
        self.status_label.setText("{} / {} — {}".format(position, total, name))

    def _update_buttons(self, state):
        running = state == RUNNING
        paused = state == PAUSED
        active = running or paused

        self.play_btn.setEnabled(state == STOPPED)
        self.pause_btn.setEnabled(active)
        self.stop_btn.setEnabled(active)
        self.prev_btn.setEnabled(active)
        self.next_btn.setEnabled(active)

        # Group / item selection is locked while a run is active.
        self.group_combo.setEnabled(not active)
        self.refresh_btn.setEnabled(not active)
        self.items_list.setEnabled(not active)
        self.check_all_btn.setEnabled(not active)
        self.uncheck_all_btn.setEnabled(not active)

        self.pause_btn.setText("⏸ Pause" if running else "▶ Resume")
        if state == STOPPED:
            self.status_label.setText("Stopped.")
        elif paused:
            self.status_label.setText(
                self.status_label.text().replace(" (paused)", "") + " (paused)"
            )

    # ------------------------------------------------------------------- close
    def closeEvent(self, event):
        self.controller.stop()
        super().closeEvent(event)
