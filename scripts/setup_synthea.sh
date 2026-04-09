#!/bin/bash

# Downloads the Synthea jar into the synthea/ directory.
# Run this once before generating any patient data.
# Requires: Java 11 or higher (check with: java -version)

set -e

SYNTHEA_DIR="$(dirname "$0")/../synthea"
JAR_PATH="$SYNTHEA_DIR/synthea-with-dependencies.jar"
DOWNLOAD_URL="https://github.com/synthetichealth/synthea/releases/latest/download/synthea-with-dependencies.jar"

mkdir -p "$SYNTHEA_DIR"

if [ -f "$JAR_PATH" ]; then
    echo "Synthea jar already exists at $JAR_PATH, skipping download."
    exit 0
fi

echo "Downloading Synthea jar..."
wget -O "$JAR_PATH" "$DOWNLOAD_URL"
echo "Done. Synthea jar saved to $JAR_PATH"