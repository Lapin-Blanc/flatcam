#!/bin/bash
# Build a FlatCAM AppImage from the PyInstaller onedir bundle (dist/FlatCAM).
#
# Usage: packaging/build_appimage.sh [VERSION]
# Requires: a prior `pyinstaller FlatCAM.spec`, plus the xcb/GL system libs
# installed on the build host (so they can be bundled into the AppImage).
set -euo pipefail

VERSION="${1:-dev}"
BUNDLE="dist/FlatCAM"
APPDIR="AppDir"

[ -d "$BUNDLE" ] || { echo "Missing $BUNDLE — run pyinstaller FlatCAM.spec first." >&2; exit 1; }

rm -rf "$APPDIR"
mkdir -p "$APPDIR/usr"
cp -a "$BUNDLE" "$APPDIR/usr/flatcam"

# Icon + desktop entry (required at the AppDir root by the AppImage spec).
cp share/flatcam_icon256.png "$APPDIR/flatcam.png"
cat > "$APPDIR/flatcam.desktop" <<'DESKTOP'
[Desktop Entry]
Name=FlatCAM
Comment=2D Computer-Aided PCB Manufacturing
Exec=flatcam
Icon=flatcam
Type=Application
Categories=Graphics;Engineering;
Keywords=cam;pcb;gerber;cnc;
Terminal=false
DESKTOP

# Launcher: prepend the bundled libs to the search path, then exec the binary.
cat > "$APPDIR/AppRun" <<'APPRUN'
#!/bin/sh
HERE="$(dirname "$(readlink -f "$0")")"
export LD_LIBRARY_PATH="$HERE/usr/flatcam/_internal:${LD_LIBRARY_PATH:-}"
exec "$HERE/usr/flatcam/flatcam" "$@"
APPRUN
chmod +x "$APPDIR/AppRun"

# Bundle the xcb/GL/xkbcommon system libs the Qt "xcb" platform plugin needs.
# PyInstaller does not ship these; without them the AppImage fails on a clean
# system with "Could not load the Qt platform plugin xcb".
LIBDST="$APPDIR/usr/flatcam/_internal"
for soname in \
    libxcb-icccm.so.4 libxcb-image.so.0 libxcb-keysyms.so.1 \
    libxcb-render-util.so.0 libxcb-util.so.1 libxcb-xinerama.so.0 \
    libxcb-xkb.so.1 libxkbcommon-x11.so.0 libxkbcommon.so.0; do
    src=$(ldconfig -p | awk -v s="$soname" '$1==s {print $NF; exit}')
    if [ -n "${src:-}" ] && [ -f "$src" ]; then
        cp -n "$src" "$LIBDST/" && echo "bundled $soname"
    else
        echo "WARNING: $soname not found on host — install it before building" >&2
    fi
done

# Fetch appimagetool and build. --appimage-extract-and-run avoids needing FUSE
# (GitHub-hosted runners have no FUSE).
TOOL="appimagetool-x86_64.AppImage"
if [ ! -x "$TOOL" ]; then
    wget -q "https://github.com/AppImage/appimagetool/releases/download/continuous/$TOOL"
    chmod +x "$TOOL"
fi

OUT="FlatCAM-${VERSION}-x86_64.AppImage"
ARCH=x86_64 APPIMAGE_EXTRACT_AND_RUN=1 "./$TOOL" "$APPDIR" "$OUT"
echo "Built $OUT"
