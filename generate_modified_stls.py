#!/usr/bin/env python3
"""Generate modified STLs by subtracting tendon/hinge holes and fingertip slots.

This script expects OpenSCAD to be installed and available on PATH so trimesh can
run boolean operations with the `scad` engine.
"""

from __future__ import annotations

import argparse
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List

import trimesh


@dataclass(frozen=True)
class CutoutConfig:
    tendon_hole_radius_ratio: float = 0.025
    hinge_hole_radius_ratio: float = 0.04
    fingertip_slot_depth_ratio: float = 0.2
    fingertip_slot_width_ratio: float = 0.35
    fingertip_slot_height_ratio: float = 0.2
    cylinder_sections: int = 48


def load_mesh(stl_path: Path) -> trimesh.Trimesh:
    mesh = trimesh.load_mesh(stl_path, force="mesh")
    if not isinstance(mesh, trimesh.Trimesh):
        raise TypeError(f"Expected a single mesh in {stl_path}, got {type(mesh)}")
    if mesh.is_empty:
        raise ValueError(f"Mesh is empty: {stl_path}")
    return mesh


def clean_mesh(mesh: trimesh.Trimesh) -> trimesh.Trimesh:
    mesh = mesh.copy()
    mesh.remove_duplicate_faces()
    mesh.remove_degenerate_faces()
    mesh.remove_unreferenced_vertices()
    mesh.process(validate=True)
    trimesh.repair.fix_normals(mesh)
    trimesh.repair.fix_inversion(mesh)
    trimesh.repair.fill_holes(mesh)
    return mesh


def build_cutouts(mesh: trimesh.Trimesh, config: CutoutConfig) -> List[trimesh.Trimesh]:
    bounds = mesh.bounds
    mins, maxs = bounds
    extents = maxs - mins
    x_len, y_len, z_len = extents

    min_dim = max(min(extents), 1e-6)
    tendon_r = max(min_dim * config.tendon_hole_radius_ratio, 0.35)
    hinge_r = max(min_dim * config.hinge_hole_radius_ratio, 0.6)

    x_center = (mins[0] + maxs[0]) / 2.0
    y_center = (mins[1] + maxs[1]) / 2.0
    z_center = (mins[2] + maxs[2]) / 2.0

    long_x = x_len + 8.0
    long_z = z_len + 8.0

    def cylinder_along_x(radius: float, y_pos: float, z_pos: float) -> trimesh.Trimesh:
        cyl = trimesh.creation.cylinder(
            radius=radius,
            height=long_x,
            sections=config.cylinder_sections,
        )
        # Cylinder defaults to Z axis; rotate to X axis.
        rot = trimesh.transformations.rotation_matrix(math.radians(90.0), [0, 1, 0])
        cyl.apply_transform(rot)
        cyl.apply_translation([x_center, y_pos, z_pos])
        return cyl

    def cylinder_along_z(radius: float, x_pos: float, y_pos: float) -> trimesh.Trimesh:
        cyl = trimesh.creation.cylinder(
            radius=radius,
            height=long_z,
            sections=config.cylinder_sections,
        )
        cyl.apply_translation([x_pos, y_pos, z_center])
        return cyl

    cutouts: List[trimesh.Trimesh] = []

    # Tendon holes (two parallel channels, typically near the top half).
    tendon_z = mins[2] + z_len * 0.72
    cutouts.append(cylinder_along_x(tendon_r, mins[1] + y_len * 0.35, tendon_z))
    cutouts.append(cylinder_along_x(tendon_r, mins[1] + y_len * 0.65, tendon_z))

    # Hinge holes (two vertical pivot channels near the base/middle region).
    hinge_y = mins[1] + y_len * 0.2
    cutouts.append(cylinder_along_z(hinge_r, mins[0] + x_len * 0.35, hinge_y))
    cutouts.append(cylinder_along_z(hinge_r, mins[0] + x_len * 0.65, hinge_y))

    # Small fingertip slot box near distal end.
    slot_size = [
        max(x_len * config.fingertip_slot_width_ratio, 1.2),
        max(y_len * config.fingertip_slot_depth_ratio, 1.2),
        max(z_len * config.fingertip_slot_height_ratio, 1.0),
    ]
    slot = trimesh.creation.box(extents=slot_size)
    slot_center = [
        x_center,
        maxs[1] - slot_size[1] * 0.55,
        mins[2] + z_len * 0.78,
    ]
    slot.apply_translation(slot_center)
    cutouts.append(slot)

    return cutouts


def boolean_subtract(mesh: trimesh.Trimesh, cutouts: Iterable[trimesh.Trimesh]) -> trimesh.Trimesh:
    result = trimesh.boolean.difference([mesh, *cutouts], engine="scad")
    if result is None or result.is_empty:
        raise RuntimeError("Boolean subtraction failed or produced an empty mesh")
    if isinstance(result, trimesh.Scene):
        result = trimesh.util.concatenate(tuple(result.dump()))
    if not isinstance(result, trimesh.Trimesh):
        raise TypeError(f"Unexpected boolean output type: {type(result)}")
    return result


def process_stl(stl_path: Path, output_dir: Path, config: CutoutConfig) -> Path:
    original = load_mesh(stl_path)
    original = clean_mesh(original)
    cutouts = build_cutouts(original, config)
    modified = boolean_subtract(original, cutouts)
    modified = clean_mesh(modified)

    output_path = output_dir / f"{stl_path.stem}_modified.stl"
    output_dir.mkdir(parents=True, exist_ok=True)
    modified.export(output_path, file_type="stl")

    # Read-back validation for slicer compatibility.
    round_trip = trimesh.load_mesh(output_path, force="mesh")
    if not isinstance(round_trip, trimesh.Trimesh) or round_trip.is_empty:
        raise RuntimeError(f"Exported file is not a valid non-empty STL: {output_path}")

    return output_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Apply tendon/hinge/fingertip cutouts to obj_*.stl meshes"
    )
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=Path.cwd(),
        help="Directory containing source obj_*.stl files",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path.cwd() / "modified_stls",
        help="Directory where modified STL files are written",
    )
    parser.add_argument(
        "--pattern",
        default="obj_*.stl",
        help="Glob pattern used to select source STLs",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    source_files = sorted(args.input_dir.glob(args.pattern))

    if not source_files:
        raise SystemExit(f"No input STL files matched pattern: {args.input_dir / args.pattern}")

    config = CutoutConfig()

    print(f"Found {len(source_files)} STL files in {args.input_dir}")
    for stl_path in source_files:
        output_path = process_stl(stl_path, args.output_dir, config)
        print(f"OK: {stl_path.name} -> {output_path}")


if __name__ == "__main__":
    main()
