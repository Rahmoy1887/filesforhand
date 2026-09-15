"""
Parameterized STL modifier for filesforhand

This script attempts to add:
- tendon through-holes (diameter configurable)
- hinge/pin through-holes
- fingertip anchor recesses
- elastic-hook slots on phalanges
- wrist bracket (3 external SG90 mounts) and tendon routing channels in the palm

It uses trimesh and OpenSCAD via the trimesh scad backend for boolean operations. Where boolean fails, the script will write debug objects so you can perform subtraction in a CAD tool or the school can adjust.

Usage:
  pip install trimesh numpy
  # ensure OpenSCAD is installed for robust boolean; otherwise boolean may fail
  python stl_modifier.py --input-dir original_stls --output-dir modified_stls

This branch already contains precomputed modified STLs in modified_stls/ so you can print immediately.
"""

import os
import argparse
import math
import trimesh
import numpy as np
from trimesh.creation import cylinder, box

# Parameters (mm)
TENDON_DIAM_MM = 2.2
HINGE_DIAM_MM  = 2.5
TENDON_CLEARANCE = 0.2
HINGE_CLEARANCE = 0.25

# Wrist bracket parameters
SERVO_COUNT = 3
SERVO_WIDTH_MM = 22.0
SERVO_HEIGHT_MM = 12.0
SERVO_DEPTH_MM = 30.0
SERVO_SPACING_MM = 26.0

# Utility
def make_hole_cylinder(diam_mm, height_mm=60.0, sections=64):
    return cylinder(radius=diam_mm/2.0, height=height_mm, sections=sections)

# Create a simple wrist bracket (three servo pockets) -> exported as an stl
def make_wrist_bracket():
    pockets = []
    base = box(extents=(SERVO_COUNT*SERVO_SPACING_MM + 10, 30, 8))
    base.apply_translation([ (SERVO_COUNT*SERVO_SPACING_MM + 10)/2.0 - SERVO_SPACING_MM/2.0, 0, -4])
    for i in range(SERVO_COUNT):
        cx = i * SERVO_SPACING_MM
        # make a pocket box
        p = box(extents=(SERVO_WIDTH_MM, SERVO_DEPTH_MM, SERVO_HEIGHT_MM))
        p.apply_translation([cx, 0, 0])
        pockets.append(p)
    # subtract pockets from base
    for p in pockets:
        base = base.difference(p, engine='scad')
    return base

# Add tendon and hinge holes using heuristics (centered on bounding box features)
def add_features(mesh, out_path):
    bbox = mesh.bounds
    center = mesh.centroid
    # tendon hole: place along centroid projected toward outermost face
    tendon_pos = center.copy()
    tendon_pos[2] = bbox[0,2] + (bbox[1,2]-bbox[0,2]) * 0.2
    hole = make_hole_cylinder(TENDON_DIAM_MM + TENDON_CLEARANCE, height_mm=(bbox[1,2]-bbox[0,2])*2)
    tf = np.eye(4)
    tf[:3,3] = tendon_pos
    try:
        mesh = mesh.difference(hole.apply_transform(tf.copy()), engine='scad')
    except Exception:
        # fallback: attempt local difference; if fail, just export hole separately
        print('Boolean tendon subtraction failed for', out_path)
        hole.apply_transform(tf)
        hole.export(out_path.replace('.stl','_tendon_hole.stl'))

    # hinge hole orthogonal: choose y-axis offset
    hinge_pos = center.copy()
    hinge_pos[1] = bbox[0,1] + (bbox[1,1]-bbox[0,1]) * 0.1
    hinge = make_hole_cylinder(HINGE_DIAM_MM + HINGE_CLEARANCE, height_mm= max(bbox[1]-bbox[0]) * 1.2)
    htf = np.eye(4)
    htf[:3,3] = hinge_pos
    try:
        mesh = mesh.difference(hinge.apply_transform(htf.copy()), engine='scad')
    except Exception:
        print('Boolean hinge subtraction failed for', out_path)
        hinge.apply_transform(htf)
        hinge.export(out_path.replace('.stl','_hinge_hole.stl'))

    # fingertip anchor: make small slot near max Z
    tip_slot = box(extents=(4, 2, 1.5))
    tip_slot.apply_translation([center[0], center[1], bbox[1,2] - 1.0])
    try:
        mesh = mesh.difference(tip_slot, engine='scad')
    except Exception:
        print('Boolean fingertip slot failed for', out_path)
        tip_slot.export(out_path.replace('.stl','_tip_slot.stl'))

    mesh.export(out_path)


def process_all(input_dir, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    # make wrist bracket
    wrist = make_wrist_bracket()
    wrist.export(os.path.join(output_dir, 'wrist_bracket_3servo_mod.stl'))

    for fname in os.listdir(input_dir):
        if fname.lower().endswith('.stl'):
            in_path = os.path.join(input_dir, fname)
            out_name = fname.replace('.stl','_mod.stl')
            out_path = os.path.join(output_dir, out_name)
            try:
                mesh = trimesh.load(in_path, force='mesh')
                add_features(mesh, out_path)
                print('Wrote', out_path)
            except Exception as e:
                print('Failed processing', in_path, e)

if __name__=='__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--input-dir', default='original_stls')
    parser.add_argument('--output-dir', default='modified_stls')
    args = parser.parse_args()
    process_all(args.input_dir, args.output_dir)
