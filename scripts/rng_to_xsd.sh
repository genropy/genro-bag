#!/bin/bash
# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
#
# Convert HTML5 RNG schema files to a single XSD file using trang.
#
# Prerequisites:
#   brew install jing-trang
#
# Usage:
#   ./scripts/rng_to_xsd.sh
#
# This script:
# 1. Downloads HTML5 RNG files from validator.nu if not present
# 2. Creates a combined RNG file that includes all modules
# 3. Converts to XSD using trang
# 4. Outputs to temp/html5.xsd

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
TEMP_DIR="$PROJECT_DIR/temp"
RNG_DIR="$TEMP_DIR/html5_rng"
OUTPUT_XSD="$TEMP_DIR/html5.xsd"

# Check trang is installed
if ! command -v trang &> /dev/null; then
    echo "Error: trang not found. Install with: brew install jing-trang"
    exit 1
fi

# Create temp directory
mkdir -p "$TEMP_DIR"

# Check if RNG files exist
if [ ! -d "$RNG_DIR" ] || [ -z "$(ls -A "$RNG_DIR"/*.rng 2>/dev/null)" ]; then
    echo "RNG files not found in $RNG_DIR"
    echo "Please download HTML5 RNG files first."
    echo ""
    echo "You can download them from:"
    echo "  https://github.com/nickhutchinson/html5-validator/tree/master/schema"
    echo ""
    echo "Or use rnc2rng to convert from RNC:"
    echo "  pip install rnc2rng"
    echo "  for f in *.rnc; do rnc2rng \"\$f\" \"\${f%.rnc}.rng\"; done"
    exit 1
fi

echo "Converting RNG to XSD..."
echo "  Input: $RNG_DIR"
echo "  Output: $OUTPUT_XSD"

# Find the main entry point (usually html5.rng or similar)
# The validator.nu schema uses html5full.rnc as entry point
# After conversion, we need to find a suitable entry

# Try common entry points
ENTRY_RNG=""
for candidate in html5full.rng html5.rng structural.rng; do
    if [ -f "$RNG_DIR/$candidate" ]; then
        ENTRY_RNG="$RNG_DIR/$candidate"
        break
    fi
done

if [ -z "$ENTRY_RNG" ]; then
    # If no standard entry point, create a combined one
    echo "Creating combined RNG file..."
    ENTRY_RNG="$TEMP_DIR/html5_combined.rng"

    cat > "$ENTRY_RNG" << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<grammar xmlns="http://relaxng.org/ns/structure/1.0"
         datatypeLibrary="http://www.w3.org/2001/XMLSchema-datatypes">
EOF

    # Include all RNG files
    for rng in "$RNG_DIR"/*.rng; do
        basename_rng=$(basename "$rng")
        echo "  <include href=\"html5_rng/$basename_rng\"/>" >> "$ENTRY_RNG"
    done

    echo "</grammar>" >> "$ENTRY_RNG"
fi

echo "Using entry point: $ENTRY_RNG"

# Run trang
cd "$TEMP_DIR"
trang -I rng -O xsd "$(basename "$ENTRY_RNG")" html5.xsd

echo ""
echo "Done! XSD file created: $OUTPUT_XSD"
echo ""
echo "To generate the schema for HtmlBuilder:"
echo "  python -c \"from genro_bag.builders.xsd import XsdBuilder; ...\""
