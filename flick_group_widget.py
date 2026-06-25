"""One group's configuration block: group picker, include list and timing.

Two flavours, chosen by ``is_base``:

* **Base group** - owns the interval in seconds (the master clock).
* **Synced group** - owns an integer *multiplier* of the base interval, plus a
  header explaining the sync relationship and a Remove (cancel) button.
"""

from qgis.PyQt.QtCore import Qt, pyqtSignal
from qgis.PyQt.QtWidgets import (
    QGroupBox,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QComboBox,
    QPushButton,
    QToolButton,
    QListWidget,
    QListWidgetItem,
    QDoubleSpinBox,
    QSpinBox,
    QLabel,
    QSizePolicy,
)
from qgis.core import QgsProject, QgsLayerTreeGroup

from .flick_controller import FlickController

# Role used to stash the layer-tree node object on combo/list items.
NODE_ROLE = Qt.ItemDataRole.UserRole + 1


class FlickGroupWidget(QGroupBox):
    """Editable configuration for a single flicking group."""

    remove_requested = pyqtSignal(object)        # emits self
    config_changed = pyqtSignal()                # interval / multiplier / group changed
    group_pause_changed = pyqtSignal(object, bool)  # self, paused

    def __init__(self, iface, is_base, parent=None):
        super().__init__(parent)
        self.iface = iface
        self.is_base = is_base
        self.controller = FlickController(self)
        self._paused = False
        self._status_core = "—"
        self._build_ui()
        self._connect()
        self.populate_groups()
        self.controller.current_changed.connect(self._on_current_changed)

    # ------------------------------------------------------------------- build
    def _build_ui(self):
        self.setTitle("Base group" if self.is_base else "Synced group")
        layout = QVBoxLayout(self)

        # Sync header (added rows only)
        self.header_label = QLabel("", self)
        self.header_label.setWordWrap(True)
        if not self.is_base:
            layout.addWidget(self.header_label)

        # Group selector
        grow = QHBoxLayout()
        self.group_combo = QComboBox(self)
        self.refresh_btn = QToolButton(self)
        self.refresh_btn.setText("↻")  # refresh glyph
        self.refresh_btn.setToolTip("Reload the list of groups from the project")
        grow.addWidget(QLabel("Group:", self))
        grow.addWidget(self.group_combo, 1)
        grow.addWidget(self.refresh_btn)
        layout.addLayout(grow)

        # Include list
        self.items_list = QListWidget(self)
        self.items_list.setToolTip(
            "Checked items are included in the loop; uncheck to exclude."
        )
        self.items_list.setMaximumHeight(120)
        layout.addWidget(self.items_list)
        crow = QHBoxLayout()
        self.check_all_btn = QPushButton("Check all", self)
        self.uncheck_all_btn = QPushButton("Uncheck all", self)
        crow.addWidget(self.check_all_btn)
        crow.addWidget(self.uncheck_all_btn)
        crow.addStretch(1)
        layout.addLayout(crow)

        # Timing
        form = QFormLayout()
        if self.is_base:
            self.interval_spin = QDoubleSpinBox(self)
            self.interval_spin.setRange(0.1, 60.0)
            self.interval_spin.setSingleStep(0.5)
            self.interval_spin.setDecimals(1)
            self.interval_spin.setValue(2.0)
            self.interval_spin.setSuffix(" s")
            form.addRow("Interval:", self.interval_spin)
        else:
            self.multiplier_spin = QSpinBox(self)
            self.multiplier_spin.setRange(1, 60)
            self.multiplier_spin.setValue(2)
            self.multiplier_spin.setPrefix("× ")  # "x "
            form.addRow("Speed (of base):", self.multiplier_spin)
        layout.addLayout(form)

        # Per-row status on its own full-width line so a long layer name can
        # wrap across as many lines as needed instead of overflowing sideways.
        self.status_label = QLabel("—", self)  # em dash
        self.status_label.setWordWrap(True)
        self.status_label.setAlignment(
            Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft
        )
        self.status_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        self.status_label.setMinimumWidth(0)
        # Ignore the label's own width hint so a long name can never widen the
        # row (which, with the horizontal scrollbar off, would clip the buttons).
        self.status_label.setSizePolicy(
            QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Minimum
        )
        layout.addWidget(self.status_label)

        # Buttons on their own right-aligned row.
        brow = QHBoxLayout()
        brow.addStretch(1)
        self.group_pause_btn = QPushButton("⏸ This", self)
        self.group_pause_btn.setToolTip(
            "Pause just this group; the others keep running"
        )
        self.group_pause_btn.setEnabled(False)
        brow.addWidget(self.group_pause_btn)
        if not self.is_base:
            self.remove_btn = QPushButton("✕ Remove", self)
            brow.addWidget(self.remove_btn)
        layout.addLayout(brow)

    def _connect(self):
        self.refresh_btn.clicked.connect(self.populate_groups)
        self.group_combo.currentIndexChanged.connect(self._on_group_changed)
        self.check_all_btn.clicked.connect(lambda: self._set_all_checked(True))
        self.uncheck_all_btn.clicked.connect(lambda: self._set_all_checked(False))
        self.group_pause_btn.clicked.connect(self._toggle_group_pause)
        if self.is_base:
            self.interval_spin.valueChanged.connect(
                lambda _v: self.config_changed.emit()
            )
        else:
            self.multiplier_spin.valueChanged.connect(
                lambda _v: self.config_changed.emit()
            )
            self.remove_btn.clicked.connect(
                lambda: self.remove_requested.emit(self)
            )

    # ------------------------------------------------------------- populating
    def populate_groups(self):
        """Walk the layer tree and list every group (nested included)."""
        self.group_combo.blockSignals(True)
        self.group_combo.clear()
        root = QgsProject.instance().layerTreeRoot()
        for group in self._iter_groups(root):
            self.group_combo.addItem(self._group_path(group, root))
            self.group_combo.setItemData(
                self.group_combo.count() - 1, group, NODE_ROLE
            )
        self.group_combo.blockSignals(False)
        if self.group_combo.count() == 0:
            self.items_list.clear()
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
        group = self.group_node()
        if group is None:
            return
        try:
            children = group.children()
        except RuntimeError:
            return
        for node in children:
            item = QListWidgetItem(node.name())
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Checked)
            item.setData(NODE_ROLE, node)
            self.items_list.addItem(item)

    def _set_all_checked(self, checked):
        state = Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked
        for i in range(self.items_list.count()):
            self.items_list.item(i).setCheckState(state)

    # --------------------------------------------------------------- accessors
    def group_node(self):
        idx = self.group_combo.currentIndex()
        if idx < 0:
            return None
        return self.group_combo.itemData(idx, NODE_ROLE)

    def included_nodes(self):
        nodes = []
        for i in range(self.items_list.count()):
            item = self.items_list.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                nodes.append(item.data(NODE_ROLE))
        return nodes

    def multiplier(self):
        return 1 if self.is_base else self.multiplier_spin.value()

    def base_interval(self):
        return self.interval_spin.value() if self.is_base else None

    def display_name(self):
        group = self.group_node()
        return group.name() if group is not None else "(no group)"

    # ---------------------------------------------------------------- updates
    def update_sync_header(self, base_seconds):
        """Refresh the 'x N = M s' explanation on a synced row."""
        if self.is_base:
            return
        mult = self.multiplier_spin.value()
        self.header_label.setText(
            "Synced to base — advances every ×{0} "
            "= {1:.1f} s".format(mult, mult * base_seconds)
        )

    def set_editable(self, editable):
        self.group_combo.setEnabled(editable)
        self.refresh_btn.setEnabled(editable)
        self.items_list.setEnabled(editable)
        self.check_all_btn.setEnabled(editable)
        self.uncheck_all_btn.setEnabled(editable)
        if self.is_base:
            self.interval_spin.setEnabled(editable)
        else:
            self.multiplier_spin.setEnabled(editable)
            self.remove_btn.setEnabled(editable)

    def set_running_controls(self, active):
        """Per-group Pause is usable only while a run is active."""
        self.group_pause_btn.setEnabled(active)
        if not active and self._paused:
            self._paused = False
            self._update_pause_btn()

    def clear_status(self):
        self._status_core = "—"
        self._paused = False
        self._update_pause_btn()
        self._refresh_status()

    # ----------------------------------------------------------------- signals
    def _on_group_changed(self, _index):
        self.populate_items()
        self.config_changed.emit()

    def _on_current_changed(self, name, position, total):
        self._status_core = "{} / {} — {}".format(position, total, name)
        self._refresh_status()

    def _toggle_group_pause(self):
        self._paused = not self._paused
        self._update_pause_btn()
        self._refresh_status()
        self.group_pause_changed.emit(self, self._paused)

    def _update_pause_btn(self):
        self.group_pause_btn.setText("▶ This" if self._paused else "⏸ This")

    def _refresh_status(self):
        suffix = "   ⏸ paused" if self._paused else ""
        self.status_label.setText(self._add_break_hints(self._status_core) + suffix)

    @staticmethod
    def _add_break_hints(text, max_run=12):
        """Insert zero-width spaces so long, space-less names can still wrap.

        Word wrap only breaks on real spaces, so a long token (e.g.
        ``Very_Long_Layer_Name_2024``) keeps a wide minimum width. We add a
        break opportunity after common separators and within any run longer
        than ``max_run`` characters, keeping the label's minimum width small
        without visibly changing the text.
        """
        zwsp = "​"
        out = []
        run = 0
        for ch in text:
            out.append(ch)
            if ch.isspace() or ch in "/_-.":
                out.append(zwsp)
                run = 0
            else:
                run += 1
                if run >= max_run:
                    out.append(zwsp)
                    run = 0
        return "".join(out)
