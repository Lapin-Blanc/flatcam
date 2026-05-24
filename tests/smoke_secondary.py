#!/usr/bin/env python3
"""
Headless smoke test for FlatCAM's secondary tools / geometry operations.

Drives the TCL command layer (which the GUI tools call into) to exercise the
heavy geometry code paths where Python 3.12 / PySide6 / shapely 2.x porting
regressions tend to hide. It does NOT validate CAM correctness -- it only
checks that each operation runs without an unexpected Python-level exception.

Run with:
    QT_QPA_PLATFORM=offscreen python tests/smoke_secondary.py
"""
import os
import re
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))  # project root

from PySide6 import QtWidgets  # noqa: E402
from FlatCAMApp import App  # noqa: E402
GERBER = os.path.join(HERE, "gerber_files", "simple1.gbr")
EXCELLON = os.path.join(HERE, "excellon_files", "case1.drl")

# Markers of a genuine porting regression (vs. a legitimate domain error
# raised on purpose by a command, e.g. "Object not found").
PORT_BUG_MARKERS = (
    "not iterable", "has no attribute", "AttributeError", "TypeError",
    "object is not", "takes no", "unexpected keyword", "positional argument",
    "NameError", "ImportError", "RuntimeError", "must be", "'NoneType'",
)


def main():
    app = QtWidgets.QApplication(sys.argv)
    fc = App(user_defaults=False)

    # Load source objects (synchronous, no worker threads).
    fc.open_gerber(GERBER)
    fc.open_excellon(EXCELLON)

    g = "simple1.gbr"     # gerber object name
    e = "case1.drl"       # excellon object name

    # (label, tcl command). Order matters: some commands consume earlier outputs.
    steps = [
        ("Isolate (Gerber->Geo)",   'isolate %s -dia 0.1 -outname iso' % g),
        ("Follow",                  'follow %s -outname fol' % g),
        ("Exteriors",               'exteriors iso -outname ext'),
        ("Interiors",               'interiors iso -outname inte'),
        ("GeoUnion",                'geo_union iso'),
        ("Offset (Transform)",      'offset iso 1.0 1.0'),
        ("Scale (Transform)",       'scale iso 2.0'),
        ("Mirror X (DblSided)",     'mirror iso -axis X'),
        ("Mirror Y -box",          'mirror iso -axis Y -box %s' % g),
        ("Cutout (Gerber)",         'cutout %s -dia 0.1 -margin 1 -gapsize 1 -gaps 4' % g),
        ("GeoCutout (Geo)",         'geocutout iso -dia 0.1 -margin 1 -gapsize 1 -gaps 4'),
        ("Paint -all (Paint tool)", 'paint fol 0.1 0.2 -all 1 -outname painted'),
        ("Panelize",                'panelize %s -rows 2 -columns 2' % g),
        # Fresh isolation for CNCjob: 'iso' has been mutated by the transforms
        # above into a degenerate (possibly empty) geometry.
        ("Isolate (fresh)",         'isolate %s -dia 0.1 -outname iso2' % g),
        ("CNCjob (from Geo)",       'cncjob iso2 -tooldia 0.1'),
        ("MillHoles (Excellon)",    'millholes %s -tooldia 0.01' % e),
        ("Drillcncjob (Excellon)",  'drillcncjob %s -drillz -2 -travelz 2 -feedrate 100' % e),
    ]

    passed, port_bugs, domain_errors = [], [], []

    for label, cmd in steps:
        try:
            fc.exec_command_test(cmd, reraise=True)
            passed.append(label)
            print("  PASS  %-26s | %s" % (label, cmd))
        except Exception as ex:  # noqa: BLE001
            msg = str(ex).strip().replace("\n", " ")[:300]
            is_port_bug = any(m in str(ex) for m in PORT_BUG_MARKERS)
            (port_bugs if is_port_bug else domain_errors).append((label, cmd, msg))
            tag = "PORTBUG" if is_port_bug else "dom-err"
            print("  %s %-26s | %s\n            -> %s" % (tag, label, cmd, msg))

    print("\n" + "=" * 70)
    print("PASS: %d | PORT BUGS: %d | domain errors: %d (of %d)"
          % (len(passed), len(port_bugs), len(domain_errors), len(steps)))
    if port_bugs:
        print("\n--- PORTING REGRESSIONS (need fixing) ---")
        for label, cmd, msg in port_bugs:
            print("  * %s\n    cmd: %s\n    err: %s" % (label, cmd, msg))
    if domain_errors:
        print("\n--- domain errors (likely legitimate, review) ---")
        for label, cmd, msg in domain_errors:
            print("  * %s: %s" % (label, msg))

    # Exit non-zero only if a real porting regression was found.
    sys.exit(1 if port_bugs else 0)


if __name__ == "__main__":
    main()
