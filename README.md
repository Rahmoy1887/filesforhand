# filesforhand

## STL modification script

Use `/home/runner/work/filesforhand/filesforhand/generate_modified_stls.py` to generate modified, printer-readable STL files from `obj_*.stl` inputs.

### What it does

For each source STL, the script:
- loads and repairs the mesh,
- builds tendon-hole cylinders, hinge-hole cylinders, and a fingertip slot box,
- subtracts these cutouts using OpenSCAD (`trimesh` boolean engine `scad`),
- exports `<name>_modified.stl`,
- re-loads the written file to verify it is a valid non-empty STL.

### Requirements

- Python 3.9+
- `trimesh`, `scipy`, `manifold3d` (`pip install trimesh scipy manifold3d`)
- Optional: OpenSCAD on `PATH` (used automatically if a compatible `scad` boolean engine is available)

### Run

```bash
python /home/runner/work/filesforhand/filesforhand/generate_modified_stls.py \
  --input-dir /home/runner/work/filesforhand/filesforhand \
  --output-dir /home/runner/work/filesforhand/filesforhand/modified_stls
```

Optional:
- `--pattern "obj_*.stl"` (default)
