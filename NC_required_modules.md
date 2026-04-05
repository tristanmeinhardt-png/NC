
# NC Required Python Modules

This file lists the Python modules required to run NC (NeuroConsole).

NC itself mostly uses the Python standard library, but some features require additional modules.

## Recommended installation (all features)

Run this command:

pip install pyinstaller PySide6 PySide6-QtWebEngine

---

## Module explanation

pyinstaller
Used to convert .nc programs into Windows .exe files.

Command:
pip install pyinstaller

---

PySide6
Required for GUI window output (TWIN system).

Command:
pip install PySide6

---

PySide6-QtWebEngine
Required if NC windows display HTML content.

Command:
pip install PySide6-QtWebEngine

---

## Minimum installation (console only)

If you only want the basic console language:

Python 3.10 or newer is usually enough.

---

## Install everything at once

pip install pyinstaller PySide6 PySide6-QtWebEngine

---

## Optional

If future NC modules require additional libraries, they will be listed here.
