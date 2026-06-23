# Layer Flick Visibility (QGIS plugin)

Animate ("flick") through the contents of a layer **group** in the QGIS Layers
panel. The plugin shows the first **first-level** child (a layer or a subgroup),
waits a set interval, hides it, shows the next one, and loops continuously — a
quick way to compare before/after imagery, design alternatives, or time
snapshots.

## Features

- Pick any group in the project (nested groups included).
- A **base** group sets the interval in seconds.
- **Add synced groups**: each additional group flicks at a whole-number
  **multiplier** of the base interval (e.g. ×2 = every other base step), so every
  group stays perfectly in sync off a single shared clock. Each synced row shows
  a header with its effective interval and a **Remove** button to cancel it.
- **Play / Pause / Resume / Stop** plus manual **◀ Previous / Next ▶** stepping,
  shared across all groups.
- **Per-group pause**: each group has its own **⏸ This** button to freeze just
  that group while the others keep flicking; press again to resume it in sync.
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
2. In the **Base group**, choose a group; its first-level children fill the list
   (all checked). Uncheck anything to exclude, and set the **Interval**.
3. *(Optional)* Press **➕ Add synced group** to add another group. Pick its group,
   set its **Speed (× of base)** multiplier, and trim its items. The header shows
   the resulting interval. Use **✕ Remove** to cancel an added group.
4. Press **▶ Play**. Use **⏸ Pause / ▶ Resume**, **◀ Prev / Next ▶**, and
   **■ Stop** as needed — they drive all groups together. Each group's **⏸ This**
   button freezes only that group while the rest keep running.

## Files

| File | Purpose |
| --- | --- |
| `__init__.py` | `classFactory` entry point |
| `metadata.txt` | Plugin metadata |
| `layer_flick_plugin.py` | Menu/toolbar action and dock lifecycle |
| `flick_dock_widget.py` | The options panel: base + synced rows, transport |
| `flick_group_widget.py` | One group's config block (group, items, timing) |
| `flick_coordinator.py` | Single shared timer + tick-based sync across groups |
| `flick_controller.py` | Per-group visibility state (UI-free, timer-free) |
