#!/usr/bin/env python3
"""
Frozen / PyInstaller entry point for FlatCAM.

Kept as a thin, separate module (rather than freezing FlatCAMApp.py directly)
so that the entry runs as __main__ while every other module still does a normal
`import FlatCAMApp` and shares the same module object — otherwise FlatCAMApp
would be loaded twice (once as __main__) and FlatCAMApp.App would have two
distinct identities.
"""
from FlatCAMApp import main

if __name__ == '__main__':
    main()
