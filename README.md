# Layer Flick Visibility (QGIS plugin)

Animate ("flick") through the contents of a layer **group** in the QGIS Layers
panel. The plugin shows the first **first-level** child (a layer or a subgroup),
waits a set interval, hides it, shows the next one, and loops continuously — a
quick way to compare before/after imagery, design alternatives, or time
snapshots.

## Features

- Pick any group in the project (nested groups included).
- Single interval (seconds) applied to every item.
- **Play / Pause / Resume / Stop** plus manual **◀ Previous / Next ▶** stepping.
- **Include / exclude** individual first-level items with checkboxes, so only a
  chosen subset participates in the loop.
- Continuous looping; visibility is **left as-is** when stopped (non-prescriptive
  about your final state).
- Controls live in a dockable panel, launched from the **Plugins** menu.

## Install

Copy this folder into your QGIS profile's plugins directory so the folder name
matches the Python package, e.g. on Windows:

```
%APPDATA%\QGIS\QGIS3\profiles\default\python\plugins\layer_flick_visibility\
```

For live editing you can instead create a directory junction pointing at this
repo:

```powershell
New-Item -ItemType Junction `
  -Path "$env:APPDATA\QGIS\QGIS3\profiles\default\python\plugins\layer_flick_visibility" `
  -Target "D:\git\03_AECOM\QGIS_layer_flick_visibility"
```

Then in QGIS: **Plugins ▸ Manage and Install Plugins ▸ Installed** and enable
**Layer Flick Visibility**. (This build is marked *experimental*; enable
"Show also experimental plugins" in the manager's Settings if it is hidden.)

## Usage

1. **Plugins ▸ Layer Flick Visibility** to open the dock.
2. Choose a **Group**; its first-level children fill the list (all checked).
3. Uncheck anything you want to exclude, set the **Interval**, press **▶ Play**.
4. Use **⏸ Pause / ▶ Resume**, **◀ Prev / Next ▶**, and **■ Stop** as needed.

## Files

| File | Purpose |
| --- | --- |
| `__init__.py` | `classFactory` entry point |
| `metadata.txt` | Plugin metadata |
| `layer_flick_plugin.py` | Menu/toolbar action and dock lifecycle |
| `flick_dock_widget.py` | The options panel UI and wiring |
| `flick_controller.py` | Timer-driven visibility engine (UI-free) |
