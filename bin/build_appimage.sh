#!/usr/bin/env bash

cd "$(dirname "$0")"
DIR_CURRENT="$(pwd)"
DIR_PARENT="$(dirname "$DIR_CURRENT")"

cd $DIR_PARENT

# Download AppImage Builder if not already present
BUILDER="appimage-builder-1.1.0-x86_64.AppImage"
if [ ! -f $BUILDER ]; then
    echo "Downloading AppImage Builder..."
    wget "https://github.com/AppImageCrafters/appimage-builder/releases/download/v1.1.0/$BUILDER"
fi

chmod +x $BUILDER

# Clean up previous builds
if [ -d AppDir ]; then
    echo "Removing existing AppDir..."
    rm -rf AppDir
fi

if [ -d appimage-build ]; then
    echo "Removing existing appimage-build directory..."
    rm -rf AppDir
fi

# Build the AppImage
echo "Building the AppImage..."
./$BUILDER --recipe ./AppImageBuilder.yml --skip-test
if [ $? -ne 0 ]; then
    echo "AppImage build failed!"
    exit 1
fi
echo "AppImage build completed successfully."