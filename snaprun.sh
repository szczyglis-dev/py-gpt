#!/bin/bash

# export QTWEBENGINE_DISABLE_GPU=1
# export QTWEBENGINE_CHROMIUM_FLAGS="--enable-logging --log-level=0 --v=1"

case "$SNAP_ARCH" in
    "amd64") ARCH='x86_64-linux-gnu'
    ;;
    "arm64") ARCH='aarch64-linux-gnu'
    ;;
    *)
        echo "Unsupported architecture for this app build: $SNAP_ARCH"
        exit 1
    ;;
esac

export QTWEBENGINEPROCESS_PATH=$SNAP/lib/python3.12/site-packages/PySide6/Qt/libexec/QtWebEngineProcess
export QT_QPA_PLATFORM_PLUGIN_PATH="$SNAP/lib/python3.12/site-packages/PySide6/Qt/plugins/platforms"

# QtMultimedia/libpulse needs libpulsecommon from the private PulseAudio
# directory. Put only that directory first. Keep paths provided by the
# core24 gpu extension ahead of the snap's generic library directory so the
# Mesa/NVIDIA runtime selected by the extension is not shadowed.
PULSE_LIBRARY_PATH="$SNAP/usr/lib/$ARCH/pulseaudio"
LOCAL_LIBRARY_PATH="$SNAP/usr/lib/$ARCH:$SNAP/usr/lib/$ARCH/blas:$SNAP/usr/lib/$ARCH/lapack"
if [ -n "${LD_LIBRARY_PATH:-}" ]; then
    export LD_LIBRARY_PATH="$PULSE_LIBRARY_PATH:$LD_LIBRARY_PATH:$LOCAL_LIBRARY_PATH"
else
    export LD_LIBRARY_PATH="$PULSE_LIBRARY_PATH:$LOCAL_LIBRARY_PATH"
fi
export GTK_PATH="$SNAP/usr/lib/$ARCH/gtk-3.0"
export GST_PLUGIN_SYSTEM_PATH_1_0="$SNAP/usr/lib/$ARCH/gstreamer-1.0"
export GST_PLUGIN_PATH_1_0="$SNAP/usr/lib/$ARCH/gstreamer-1.0"

# Prefer Wayland when available, fall back to X11 automatically
#if [ -n "$WAYLAND_DISPLAY" ]; then
#  export QT_QPA_PLATFORM=wayland
  # Ensure QtWebEngine uses Wayland Ozone backend when on Wayland
  # export QTWEBENGINE_CHROMIUM_FLAGS="${QTWEBENGINE_CHROMIUM_FLAGS} --ozone-platform=wayland --enable-features=UseOzonePlatform"
#else
#  export QT_QPA_PLATFORM=xcb
#fi

# Do not override LIBGL_DRIVERS_PATH here. The gpu extension/provider wrapper
# selects the correct Mesa or host NVIDIA drivers for the current machine.

# snapd gives strict snaps a private XDG_RUNTIME_DIR such as
# /run/user/<uid>/snap.pygpt, while the host PulseAudio/PipeWire-Pulse socket
# is exposed through the audio-playback/audio-record interfaces at
# /run/user/<uid>/pulse/native. Point libpulse (used by QtMultimedia) to the
# host socket explicitly. This is normally done by desktop extensions; PyGPT
# uses only the core24 gpu extension, so the wrapper has to do it here.
if [ -n "${XDG_RUNTIME_DIR:-}" ]; then
    # snapd exposes the host PulseAudio/PipeWire-Pulse socket one directory
    # above the snap-private XDG_RUNTIME_DIR. The path was verified from a
    # confined `snap run --shell pygpt` session.
    export PULSE_SERVER="unix:$XDG_RUNTIME_DIR/../pulse/native"
fi

python3 $SNAP/src/pygpt_net/app.py "$@"