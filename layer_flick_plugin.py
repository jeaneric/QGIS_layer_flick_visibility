"""Main plugin class: registers the menu/toolbar action and owns the dock."""

import os

from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction

from .flick_dock_widget import FlickDockWidget

MENU_NAME = "&Layer Flick Visibility"
ACTION_TEXT = "Layer Flick Visibility"


class LayerFlickPlugin:
    """QGIS plugin lifecycle (initGui / unload) and panel toggling."""

    def __init__(self, iface):
        self.iface = iface
        self.plugin_dir = os.path.dirname(__file__)
        self.dock = None
        self.action = None

    def initGui(self):
        icon_path = os.path.join(self.plugin_dir, "icon.png")
        icon = QIcon(icon_path) if os.path.exists(icon_path) else QIcon()
        self.action = QAction(icon, ACTION_TEXT, self.iface.mainWindow())
        self.action.setToolTip("Cycle visibility through a group's first-level items")
        self.action.triggered.connect(self.toggle_panel)
        self.iface.addPluginToMenu(MENU_NAME, self.action)
        self.iface.addToolBarIcon(self.action)

    def toggle_panel(self):
        if self.dock is None:
            self.dock = FlickDockWidget(self.iface, self.iface.mainWindow())
            self.iface.addDockWidget(Qt.RightDockWidgetArea, self.dock)
            self.dock.show()
        else:
            self.dock.setVisible(not self.dock.isVisible())

    def unload(self):
        if self.dock is not None:
            try:
                self.dock.controller.stop()
            except Exception:
                pass
            self.iface.removeDockWidget(self.dock)
            self.dock.deleteLater()
            self.dock = None
        if self.action is not None:
            self.iface.removePluginMenu(MENU_NAME, self.action)
            self.iface.removeToolBarIcon(self.action)
            self.action = None
