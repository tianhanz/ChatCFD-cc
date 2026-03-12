#!/bin/bash
# Generate mesh files from OpenFOAM tutorials for benchmark dataset

set -e

# Source OpenFOAM environment
source /usr/lib/openfoam/openfoam2406/etc/bashrc

TUTORIAL_DIR="/usr/lib/openfoam/openfoam2406/tutorials"
DATASET_DIR="datasets/of_case_grids"

# Counter for progress
total=0
success=0
failed=0

echo "=========================================="
echo "Generating meshes from OpenFOAM tutorials"
echo "=========================================="
echo ""

# Function to generate mesh for a case
generate_mesh() {
    local case_dir=$1
    local case_name=$(basename "$case_dir")

    # Parse case name: category_solver_casename
    # Example: basic_laplacianFoam_flange -> basic/laplacianFoam/flange
    local parts=(${case_name//_/ })
    local category=${parts[0]}
    local solver=${parts[1]}
    local casename="${parts[@]:2}"
    casename="${casename// /_}"

    # Construct tutorial path
    local tutorial_path="$TUTORIAL_DIR/$category/$solver/$casename"

    total=$((total + 1))

    # Check if tutorial exists
    if [ ! -d "$tutorial_path" ]; then
        echo "[$total] SKIP: $case_name (tutorial not found: $tutorial_path)"
        return
    fi

    # Check if mesh already exists and is not LFS pointer
    if [ -f "$case_dir/constant/polyMesh/points" ]; then
        local filesize=$(stat -c%s "$case_dir/constant/polyMesh/points")
        if [ $filesize -gt 1000 ]; then
            echo "[$total] SKIP: $case_name (mesh already exists, ${filesize} bytes)"
            success=$((success + 1))
            return
        fi
    fi

    echo "[$total] Processing: $case_name"
    echo "    Tutorial: $tutorial_path"

    # Create temporary directory
    local temp_dir=$(mktemp -d)
    cd "$temp_dir"

    # Copy tutorial case
    cp -r "$tutorial_path"/* .

    # Run mesh generation (Allrun or specific mesh commands)
    if [ -f "Allrun" ]; then
        # Run Allrun but stop after mesh generation
        timeout 60s bash Allrun > /dev/null 2>&1 || true
    fi

    # Check if mesh was generated
    if [ -f "constant/polyMesh/points" ]; then
        local mesh_size=$(stat -c%s "constant/polyMesh/points")
        if [ $mesh_size -gt 1000 ]; then
            # Copy mesh files to dataset
            mkdir -p "$OLDPWD/$case_dir/constant/polyMesh"
            cp constant/polyMesh/* "$OLDPWD/$case_dir/constant/polyMesh/" 2>/dev/null || true
            echo "    ✓ Mesh generated (${mesh_size} bytes)"
            success=$((success + 1))
        else
            echo "    ✗ Mesh generation failed (file too small)"
            failed=$((failed + 1))
        fi
    else
        echo "    ✗ Mesh generation failed (no polyMesh/points)"
        failed=$((failed + 1))
    fi

    # Cleanup
    cd "$OLDPWD"
    rm -rf "$temp_dir"
}

# Process all cases
for case_dir in "$DATASET_DIR"/*; do
    if [ -d "$case_dir" ]; then
        generate_mesh "$case_dir"
    fi
done

echo ""
echo "=========================================="
echo "Summary:"
echo "  Total cases: $total"
echo "  Success: $success"
echo "  Failed: $failed"
echo "=========================================="
