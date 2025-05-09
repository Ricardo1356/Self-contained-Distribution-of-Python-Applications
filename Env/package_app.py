#!/usr/bin/env python3
"""
package_app.py   –   build a *folder* ready for ISCC
┌────────────────────────────────────────────────────────────┐
│  <out‑dir>/                                               │
│     SetupFiles/   boot.py  metadata.txt  custom_pth.txt   │
│     setup.bat                                              │
│     <YourProject>/  (your whole source tree, patched)      │
└────────────────────────────────────────────────────────────┘
No ZIP is produced; ISCC can point straight at <out‑dir>.
"""

import argparse, os, re, shutil, sys
from pathlib import Path

# ───────────────────── helpers ─────────────────────
def get_python_version(req: Path) -> str:
    """Return python==X.Y.Z from requirements.txt or 3.10.0."""
    pat = re.compile(r"python==([\d.]+)", re.I)
    for line in req.read_text(encoding="utf-8").splitlines():
        m = pat.search(line)
        if m:
            return m.group(1)
    return "3.10.0"

def generate_custom_pth(ver: str) -> str:
    parts = ver.split(".")
    base  = "python" + parts[0] + parts[1] if len(parts) >= 2 else "python" + ver.replace(".","")
    return f"{base}.zip\nLib\n.\nimport site\n"

def create_boot_py(internal_dir: Path, app_pkg: str, entry: str) -> None: # Renamed parameter
    mod = Path(entry.replace("\\", ".").replace("/", ".")).with_suffix("")
    # Adjust path relative to boot.py location inside _internal
    boot = f'''import sys, os, runpy
inst = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
app  = os.path.join(inst, "{app_pkg}")
for p in (inst, app):
    sys.path.insert(0, p) if p not in sys.path else None
runpy.run_module("{app_pkg}.{mod}", run_name="__main__")
'''
    (internal_dir/"boot.py").write_text(boot, encoding="utf-8") # Write to internal_dir

def ensure_pkg_tree(root: Path) -> None:
    for cur,_,files in os.walk(root):
        if any(f.endswith(".py") for f in files):
            ip = Path(cur, "__init__.py")
            if not ip.exists(): ip.touch()

# ───────────────────── main build ─────────────────────
def build(out_dir: Path,
          src_dir: Path,
          app_name: str,
          entry_file: str,
          version: str) -> None:

    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True)

    # Create the _internal directory instead of SetupFiles
    internal_dir = out_dir / "_internal"
    internal_dir.mkdir()

    # Copy installer scripts into _internal
    here = Path(__file__).parent
    for fname in ("setup.ps1", "setup_gui.ps1"): # Add other setup files if needed
        f = here / fname
        if f.is_file():
            shutil.copy2(f, internal_dir)

    # Create metadata & boot script inside _internal
    (internal_dir/"metadata.txt").write_text(
        f"AppName={app_name}\n"
        f"AppFolder={src_dir.name}\n"
        f"EntryFile={entry_file}\n"
        f"Version={version}\n", encoding="utf-8")

    create_boot_py(internal_dir, src_dir.name, entry_file) # Pass internal_dir

    # Generate custom pth file inside _internal if needed
    py_ver = get_python_version(src_dir / "requirements.txt")
    (internal_dir/"custom_pth.txt").write_text(generate_custom_pth(py_ver), encoding="ascii")

    # Copy the actual application code to the root of out_dir
    app_dest = out_dir / src_dir.name
    shutil.copytree(src_dir, app_dest, ignore=shutil.ignore_patterns('__pycache__'))
    ensure_pkg_tree(app_dest)

    # Optional: Copy icon file into _internal
    icon_src = here / f"{app_name}.ico" # Assuming icon is next to build scripts
    if icon_src.exists():
        shutil.copy2(icon_src, internal_dir / f"{app_name}.ico")
    else:
         # If you store the icon elsewhere, adjust the source path
         print(f"Warning: Icon file '{icon_src}' not found. Skipping icon copy.")

    print(f"✓ Build folder ready → {out_dir}")

# ───────────────────── CLI ─────────────────────
def main() -> None:
    ap = argparse.ArgumentParser(description="Create build folder for ISCC.")
    ap.add_argument("app_folder", help="Path to project with requirements.txt")
    ap.add_argument("--app-name",   default=None, help="Default: folder name")
    ap.add_argument("--entry-file", default="core.py")
    ap.add_argument("--version",    default="1.0.0")
    ap.add_argument("--out-dir",
                    help="Where to place the build folder "
                         "(default: _temp/<AppName>_pkg beside script)")
    args = ap.parse_args()

    src = Path(args.app_folder).resolve()
    if not src.is_dir():
        sys.exit("ERROR: app_folder not found")

    out_base = Path(args.out_dir) if args.out_dir else \
               Path("_temp", f"{args.app_name or src.name}_pkg")
    build(out_base.resolve(), src,
          args.app_name or src.name, args.entry_file, args.version)

if __name__ == "__main__":
    main()
