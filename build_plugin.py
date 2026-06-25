#!/usr/bin/env python3
"""Package this plugin into a QGIS-installable zip under ./dist.

The zip contains a single top-level folder named like the plugin package, so it
can be installed straight from QGIS via
*Plugins > Manage and Install Plugins > Install from ZIP*. Development cruft
(``.git``, ``__pycache__``, ``*.pyc``, the ``dist`` folder and the build scripts
themselves) is excluded.

Uses only the Python standard library, so any Python 3 works -- no QGIS needed.
"""

import configparser
import fnmatch
import os
import zipfile

# Folder name QGIS installs the plugin into; must match the Python package.
PLUGIN_SLUG = "layer_flick_visibility"

HERE = os.path.dirname(os.path.abspath(__file__))
DIST_DIR = os.path.join(HERE, "dist")

# Directories pruned entirely from the walk.
EXCLUDE_DIRS = {".git", "dist", "__pycache__", ".idea", ".vscode", ".mypy_cache"}
# Exact file names never packaged.
EXCLUDE_FILES = {"build.bat", "build_plugin.py", ".gitignore"}
# Glob patterns never packaged.
EXCLUDE_GLOBS = ("*.pyc", "*.pyo", "*.zip")


def read_version():
    cfg = configparser.ConfigParser()
    cfg.read(os.path.join(HERE, "metadata.txt"), encoding="utf-8")
    try:
        return cfg.get("general", "version")
    except (configparser.Error, KeyError):
        return "0.0"


def is_excluded_file(name):
    if name in EXCLUDE_FILES:
        return True
    return any(fnmatch.fnmatch(name, pat) for pat in EXCLUDE_GLOBS)


def iter_files():
    for root, dirs, files in os.walk(HERE):
        # Prune excluded directories in-place so os.walk does not descend them.
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
        for name in sorted(files):
            if is_excluded_file(name):
                continue
            abspath = os.path.join(root, name)
            relpath = os.path.relpath(abspath, HERE)
            yield abspath, relpath


def main():
    version = read_version()
    os.makedirs(DIST_DIR, exist_ok=True)
    zip_path = os.path.join(DIST_DIR, "{0}_v{1}.zip".format(PLUGIN_SLUG, version))

    if os.path.exists(zip_path):
        os.remove(zip_path)

    count = 0
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for abspath, relpath in iter_files():
            arcname = "{0}/{1}".format(PLUGIN_SLUG, relpath.replace(os.sep, "/"))
            zf.write(abspath, arcname)
            print("  + {0}".format(arcname))
            count += 1

    print("")
    print("Created {0}".format(zip_path))
    print("Packaged {0} file(s) under {1}/".format(count, PLUGIN_SLUG))


if __name__ == "__main__":
    main()
