"""Pytest bootstrap shared by the whole suite.

Placed at the project root so that:
  * the headless Qt platform is selected before any QApplication is built;
  * the root modules (FlatCAMApp, camlib, ...) are importable from tests.
"""
import os
import sys

# Qt must run without a display in CI. Set this before importing PySide6
# anywhere, hence the root-level conftest (loaded before test modules).
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

# Force a non-interactive matplotlib backend so plot()/show() in some tests
# do not open a blocking window (a few tests call pyplot.show()).
os.environ.setdefault("MPLBACKEND", "Agg")

# Make the flat top-level modules importable (`from FlatCAMApp import App`).
ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# FlatCAMApp parses sys.argv at class-definition time (in the App body), so
# pytest's own CLI args would hit getopt and raise SystemExit on import.
# Neutralise argv before any test imports FlatCAMApp.
# Proper fix: move argument parsing into main() (see plan.md, 3.3).
sys.argv = sys.argv[:1]

# Neutralise modal dialogs. The app pops QMessageBox/QDialog via .exec(),
# which blocks forever in a headless run (no user to dismiss it). Tests do not
# assert on dialogs, so make .exec() a non-blocking no-op returning 0 (which
# reads as "Cancel/rejected" for the few callers that inspect the result).
from PySide6 import QtWidgets  # noqa: E402  (after MPLBACKEND/QT_QPA env setup)


def _noop_exec(self, *args, **kwargs):
    return 0


QtWidgets.QMessageBox.exec = _noop_exec
QtWidgets.QDialog.exec = _noop_exec

# Each App() starts two persistent worker QThreads and never stops them. Held
# alive by Qt references, they survive until interpreter shutdown, where they
# are destroyed "while still running" -> "QThread: Destroyed while thread is
# still running" -> SIGABRT (core dump, exit 134) on Linux CI (silent on
# Windows). Track every started QThread and stop it cleanly at session end,
# before the C++ teardown runs.
from PySide6 import QtCore  # noqa: E402

_started_threads = []
_orig_thread_start = QtCore.QThread.start


def _tracking_start(self, *args, **kwargs):
    _started_threads.append(self)
    return _orig_thread_start(self, *args, **kwargs)


QtCore.QThread.start = _tracking_start


def pytest_sessionfinish(session, exitstatus):
    for thread in _started_threads:
        try:
            if thread.isRunning():
                thread.quit()
                thread.wait(2000)
        except RuntimeError:
            pass  # underlying C++ QThread already deleted
    app = QtWidgets.QApplication.instance()
    if app is not None:
        app.processEvents()


# Excluded from automatic collection:
#   * tests/other/      - manual/interactive plotting & profiling scripts
#                         (some are named test_*.py but assert nothing).
#   * test_tclCommands/ - orphan helper functions, revived separately (plan 1.3).
collect_ignore_glob = [
    "tests/other/*",
    "tests/test_tclCommands/*",
]
