#!/bin/bash
# Generate meshes from OpenFOAM tutorials - Improved version

TUTORIAL_BASE="/usr/lib/openfoam/openfoam2406/tutorials"
PROJECT_DIR="/var/tmp/vibe-kanban/worktrees/7518-use-home-develop/ChatCFD-cc"
DATASET_DIR="$PROJECT_DIR/datasets/of_case_grids"

# Source OpenFOAM
source /usr/lib/openfoam/openfoam2406/etc/bashrc 2>/dev/null

echo "Generating meshes from OpenFOAM tutorials"
echo ""

success=0
failed=0
skipped=0

# Process each case
cd "$DATASET_DIR"

for case_dir in */; do
    case_name="${case_dir%/}"

    # Check if mesh exists
    if [ -f "$case_name/constant/polyMesh/points" ]; then
        size=$(stat -c%s "$case_name/constant/polyMesh/points" 2>/dev/null || echo 0)
        if [ $size -gt 1000 ]; then
            echo "SKIP: $case_name (mesh exists, ${size} bytes)"
            skipped=$((skipped + 1))
            continue
        fi
    fi

    # Parse case name: category_solver_rest
    IFS='_' read -ra parts <<< "$case_name"
    category="${parts[0]}"
    solver="${parts[1]}"
    rest="${case_name#${category}_${solver}_}"

    # Build tutorial path
    tutorial_path="$TUTORIAL_BASE/$category/$solver/$rest"

    if [ ! -d "$tutorial_path" ]; then
        echo "SKIP: $case_name (tutorial not found)"
        continue
    fi

    echo "Processing: $case_name"

    # Create temp directory
    temp_dir=$(mktemp -d)
    cp -r "$tutorial_path"/* "$temp_dir/" 2>/dev/null

    cd "$temp_dir"

    # Try blockMesh first (most common)
    if [ -f "system/blockMeshDict" ]; then
        blockMesh >/dev/null 2>&1
    fi

    # If no mesh yet, try Allrun but stop after mesh generation
    if [ ! -f "constant/polyMesh/points" ] && [ -f "Allrun" ]; then
        # Run Allrun with timeout, ignore errors
        timeout 60s bash Allrun >/dev/null 2>&1 || true
    fi

    # Check result
    if [ -f "constant/polyMesh/points" ]; then
        mesh_size=$(stat -c%s "constant/polyMesh/points")
        if [ $mesh_size -gt 1000 ]; then
            # Copy mesh
            mkdir -p "$DATASET_DIR/$case_name/constant/polyMesh"
            cp constant/polyMesh/* "$DATASET_DIR/$case_name/constant/polyMesh/" 2>/dev/null
            echo "  ✓ Generated ($mesh_size bytes)"
            success=$((success + 1))
        else
            echo "  ✗ Failed (too small: $mesh_size bytes)"
            failed=$((failed + 1))
        fi
    else
        echo "  ✗ Failed (no mesh generated)"
        failed=$((failed + 1))
    fi

    cd "$DATASET_DIR"
    rm -rf "$temp_dir"
done

echo ""
echo "=========================================="
echo "Summary:"
echo "  Success: $success"
echo "  Failed: $failed"
echo "  Skipped: $skipped"
echo "=========================================="
