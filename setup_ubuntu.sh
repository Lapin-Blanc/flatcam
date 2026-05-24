#!/bin/sh -e
# System setup for FlatCAM on Debian/Ubuntu.
#
# Python dependencies are installed with pip from pyproject.toml; only the
# non-pip system bits are handled here:
#   - python3-tk : tkinter, required by the TCL shell (not available on PyPI)
#   - libgl1     : OpenGL runtime needed by the Qt bundled in the PyQt5 wheel
#
# The numeric/geometry stack (PyQt5, numpy, scipy, matplotlib, shapely, rtree)
# ships as manylinux wheels, so no compilers or -dev headers are required.

sudo apt-get update
sudo apt-get install -y python3 python3-venv python3-pip python3-tk libgl1

# Create an isolated environment and install FlatCAM into it (editable).
python3 -m venv .venv
. .venv/bin/activate
pip install --upgrade pip
pip install -e .

echo
echo "Done. Activate the environment with:  . .venv/bin/activate"
echo "Then launch FlatCAM with:             flatcam"
