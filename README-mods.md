# STL modifier and modified STLs for filesforhand

This branch adds a parameterized STL modifier script, a README with instructions, and modified copies of the STL files with tendon and hinge holes, fingertip anchors, elastic hooks, and a wrist bracket for 3 external SG90 servos grouped as: Thumb | Index+Middle | Ring+Pinky.

Files added:
- stl_modifier.py  (script to reproduce/adjust modifications)
- README-mods.md   (instructions)
- modified_stls/   (all *_mod.stl files)

Notes:
- Boolean operations used by the script require OpenSCAD or a boolean-capable backend. The branch includes precomputed *_mod.stl files so you can print immediately.
- I did not overwrite original files. Modified files are named <original>_mod.stl.

Print the test finger and wrist bracket first to verify fit before printing the whole set.
