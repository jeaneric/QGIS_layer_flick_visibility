"""Dockable options panel for the Layer Flick Visibility plugin.

Hosts a base group plus any number of synced groups, a shared transport row and
an Add button. All groups are driven by a single :class:`FlickCoordinator` so
they stay in sync; each synced group runs at an integer multiplier of the base
interval.
"""

from qgis.PyQt.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QScrollArea,
)
from qgis.gui import QgsDockWidget

from .flick_coordinator import FlickCoordinator, STOPPED, RUNNING, PAUSED
from .flick_group_widget import FlickGroupWidget


class FlickDockWidget(QgsDockWidget):
    """Panel with one base group, optional synced groups and shared transport."""

    def __init__(self, iface, parent=None):
        super().__init__("Layer Flick Visibility", parent)
        self.iface = iface
        self.setObjectName("LayerFlickDockWidget")

        self.coordinator = FlickCoordinator(self)
        self.rows = []  # FlickGroupWidget list; rows[0] is always the base
        self._build_ui()
        self._add_base_row()

        self.coordinator.state_changed.connect(self._update_buttons)
        self._update_buttons(STOPPED)

    # ------------------------------------------------------------------- build
    def _build_ui(self):
        container = QWidget(self)
        root = QVBoxLayout(container)

        # Scrollable stack of group rows
        self.rows_container = QWidget()
        self.rows_layout = QVBoxLayout(self.rows_container)
        self.rows_layout.setContentsMargins(0, 0, 0, 0)
        self.rows_layout.addStretch(1)

        scroll = QScrollArea(container)
        scroll.setWidgetResizable(True)
        scroll.setWidget(self.rows_container)
        root.addWidget(scroll, 1)

        self.add_btn = QPushButton("➕ Add synced group", container)
        self.add_btn.clicked.connect(self._add_synced_row)
        root.addWidget(self.add_btn)

        # Shared transport
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

        self.state_label = QLabel("Stopped.", container)
        root.addWidget(self.state_label)

        self.play_btn.clicked.connect(self._on_play)
        self.pause_btn.clicked.connect(self._on_pause_resume)
        self.stop_btn.clicked.connect(self.coordinator.stop)
        self.prev_btn.clicked.connect(lambda: self.coordinator.step(-1))
        self.next_btn.clicked.connect(lambda: self.coordinator.step(1))

        self.setWidget(container)

    # -------------------------------------------------------------------- rows
    def _add_base_row(self):
        row = FlickGroupWidget(self.iface, is_base=True)
        row.config_changed.connect(self._refresh_headers)
        self._insert_row(row)
        self.rows.append(row)

    def _add_synced_row(self):
        row = FlickGroupWidget(self.iface, is_base=False)
        row.config_changed.connect(self._refresh_headers)
        row.remove_requested.connect(self._remove_row)
        self._insert_row(row)
        self.rows.append(row)
        self._refresh_headers()

    def _insert_row(self, row):
        # Insert before the trailing stretch so rows stack top-down.
        self.rows_layout.insertWidget(self.rows_layout.count() - 1, row)

    def _remove_row(self, row):
        if row.is_base or row not in self.rows:
            return
        self.rows.remove(row)
        self.rows_layout.removeWidget(row)
        row.setParent(None)
        row.deleteLater()

    def _refresh_headers(self):
        base_seconds = self.rows[0].base_interval()
        for row in self.rows[1:]:
            row.update_sync_header(base_seconds)

    # ----------------------------------------------------------------- actions
    def _on_play(self):
        entries = []
        for i, row in enumerate(self.rows):
            if row.group_node() is None or not row.included_nodes():
                label = "Base group" if row.is_base else "Group #{0}".format(i + 1)
                self.iface.messageBar().pushWarning(
                    "Layer Flick",
                    "{0} ({1}) needs a group with at least one checked item."
                    .format(label, row.display_name()),
                )
                return
            row.controller.prepare(row.group_node(), row.included_nodes())
            entries.append((row.controller, row.multiplier()))

        base_seconds = self.rows[0].base_interval()
        self.coordinator.start(base_seconds, entries)

    def _on_pause_resume(self):
        if self.coordinator.state == RUNNING:
            self.coordinator.pause()
        elif self.coordinator.state == PAUSED:
            self.coordinator.resume()

    # ----------------------------------------------------------------- signals
    def _update_buttons(self, state):
        running = state == RUNNING
        paused = state == PAUSED
        active = running or paused

        self.play_btn.setEnabled(state == STOPPED)
        self.pause_btn.setEnabled(active)
        self.stop_btn.setEnabled(active)
        self.prev_btn.setEnabled(active)
        self.next_btn.setEnabled(active)
        self.add_btn.setEnabled(not active)
        self.pause_btn.setText("⏸ Pause" if running else "▶ Resume")

        # Group editing is locked while a run is active.
        for row in self.rows:
            row.set_editable(not active)

        if state == STOPPED:
            self.state_label.setText("Stopped.")
            for row in self.rows:
                row.clear_status()
        elif running:
            self.state_label.setText("Running.")
        elif paused:
            self.state_label.setText("Paused.")

    # ------------------------------------------------------------------- close
    def closeEvent(self, event):
        self.coordinator.stop()
        super().closeEvent(event)
