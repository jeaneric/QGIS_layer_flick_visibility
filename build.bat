@echo off
REM Build the QGIS plugin zip into the dist\ folder.
REM Only the Python standard library is used, so any Python 3 works.

setlocal
set "SCRIPT_DIR=%~dp0"
set "PYEXE="

REM Prefer the QGIS/OSGeo4W Python if present (avoids the Microsoft Store stub),
REM then the py launcher, then python on PATH.
if exist "C:\OSGeo4W\apps\Python312\python.exe" set "PYEXE=C:\OSGeo4W\apps\Python312\python.exe"
if not defined PYEXE ( where py >nul 2>nul && set "PYEXE=py" )
if not defined PYEXE ( where python >nul 2>nul && set "PYEXE=python" )

if not defined PYEXE (
  echo ERROR: No Python found. Install Python 3 or QGIS/OSGeo4W, or add python to PATH.
  exit /b 1
)

"%PYEXE%" "%SCRIPT_DIR%build_plugin.py"
set "RC=%ERRORLEVEL%"
endlocal & exit /b %RC%
