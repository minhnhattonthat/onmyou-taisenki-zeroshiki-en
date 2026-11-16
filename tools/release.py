"""Release gate + patch + zip (references/pipeline.md §Release). Stops at the first failure:

    build -> tests + lint (tools/check.py) -> smoke (boot route) -> jp_left.py (no unintended Japanese)
    -> qa_gate.py check on every work/qa/**/manifest.tsv (visual tour, story pass) -> text coverage (cover.py report)
    -> docs/polish.md all ticked -> README.md has no template placeholder -> no debug code in the build
    -> BPS patch -> re-apply to a clean original and compare -> zip (patch + README.txt)

    python -X utf8 tools/release.py [--version 1.0] [--force] [--skip-smoke]

Writes release/vX.Y/<Name>_vX.Y.bps, release/vX.Y/README.txt and release/<Name>_vX.Y.zip. Refuses to overwrite an
existing version without --force. The playable image stays in build/ (the zip holds only the patch). Publishing
(`gh release create`) is the owner's call and is not done here.
"""
import argparse
import glob
import hashlib
import re
import subprocess
import sys
import zipfile
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

NAME = "Onmyou_Taisenki_Zeroshiki_EN"
BUILT = ROOT / "build/onmyou_zeroshiki_en.gba"
ZIP_README = ROOT / "docs/release-readme.txt"


def skill():
    return subprocess.run([sys.executable, str(ROOT / "tools/skill.py")], capture_output=True, text=True,
                          check=True).stdout.strip()


def step(name, cmd, ok_codes=(0,)):
    print(f"== {name}", flush=True)
    rc = subprocess.run(cmd, cwd=ROOT).returncode
    if rc not in ok_codes:
        sys.exit(f"release: {name} failed (exit {rc})")


def hashes(data):
    return {"size": len(data), "crc32": f"{zlib.crc32(data):08X}", "md5": hashlib.md5(data).hexdigest(),
            "sha1": hashlib.sha1(data).hexdigest()}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--version", default="1.0")
    ap.add_argument("--force", action="store_true", help="overwrite this version's existing files")
    ap.add_argument("--skip-smoke", action="store_true", help="iteration only: a real release runs the smoke test")
    a = ap.parse_args(argv)
    ver = f"v{a.version.lstrip('v')}"
    out = ROOT / "release" / ver
    patch, readme, zpath = out / f"{NAME}_{ver}.bps", out / "README.txt", ROOT / "release" / f"{NAME}_{ver}.zip"
    if not a.force and any(p.exists() for p in (patch, readme, zpath)):
        sys.exit(f"release: {ver} already has files in release/ (pass --force to overwrite)")
    py = [sys.executable, "-X", "utf8"]
    sk = Path(skill())
    import build  # noqa: E402  (after the path set-up)
    orig_path = build.ROM

    step("build", py + ["build.py"])
    step("tests + lint", py + ["tools/check.py"])
    if not a.skip_smoke:
        step("smoke", py + [str(sk / "scripts/emu.py"), str(BUILT), "--out", "work/qa/smoke", "--route",
                            "tools/routes/boot.txt", "--smoke"])
    print("== jp_left", flush=True)
    r = subprocess.run(py + [str(sk / "scripts/jp_left.py"), str(BUILT), "--orig", str(orig_path), "--sjis",
                             "--gba-ptrs", "--known", "tbl/jp_known.txt"], cwd=ROOT, capture_output=True, text=True)
    print(r.stdout.strip().splitlines()[-1] if r.stdout.strip() else r.stderr)
    m = re.search(r"^(\d+) Japanese runs", r.stdout, re.M)
    if r.returncode not in (0, 1) or not m or m.group(1) != "0":
        sys.exit("release: jp_left found Japanese the build still shows (see above)")
    manifests = sorted(glob.glob(str(ROOT / "work/qa/**/manifest.tsv"), recursive=True))
    if not manifests:
        sys.exit("release: no work/qa/**/manifest.tsv (visual tour and story pass gates)")
    for man in manifests:
        step(f"qa_gate {Path(man).relative_to(ROOT)}",
             py + [str(sk / "scripts/qa_gate.py"), "check", man, str(Path(man).parent / "verdicts")])
    step("text coverage", py + ["tools/debug/cover.py", "report"])
    print("== polish list", flush=True)
    open_lines = [ln for ln in (ROOT / "docs/polish.md").read_text(encoding="utf-8").splitlines()
                  if ln.startswith("- [ ]")]
    if open_lines:
        sys.exit(f"release: docs/polish.md has {len(open_lines)} unticked lines, first: {open_lines[0][:100]}")
    print("== README placeholders", flush=True)
    left = re.findall(r"<(?:Game title|platform|publisher|year|repo|file|size|sha1|game|ext|Dialogue[^>]*|"
                      r"Menus[^>]*|Title[^>]*|Name entry|Songs[^>]*|Translated[^>]*|Left in Japanese|none known[^>]*)>",
                      (ROOT / "README.md").read_text(encoding="utf-8"))
    if left:
        sys.exit(f"release: README.md still has template placeholders: {sorted(set(left))[:6]}")
    print("== no debug code in the build", flush=True)
    import romgate  # noqa: E402
    import textdb  # noqa: E402
    orig = orig_path.read_bytes()
    scripts, strings = textdb.overrides(orig, None)
    rom, log = build.build(orig, scripts=scripts, strings=strings, engine=True)
    if rom != BUILT.read_bytes():
        sys.exit("release: build/ image differs from a default build (a --qa/--marker build?)")
    debug = [ln for ln in log if re.search(r"\b(debug|warp|marker|qa)\b", str(ln), re.I)]
    errs, _ = romgate.gate(orig, rom, log)
    if debug or errs:
        sys.exit(f"release: debug/QA writes or ROM-gate errors in the build: {(debug + errs)[:5]}")
    print("   ok: the warp tool is emulator-side Lua (tools/debug/*.lua); the ROM build writes no debug hook")

    out.mkdir(parents=True, exist_ok=True)
    step("patch", py + [str(sk / "scripts/bps.py"), "make", str(orig_path), str(BUILT), str(patch)])
    print("== re-apply to a clean original", flush=True)
    check = out / "check.gba"
    step("apply", py + [str(sk / "scripts/bps.py"), "apply", str(orig_path), str(patch), str(check)])
    if check.read_bytes() != BUILT.read_bytes():
        sys.exit("release: the patched clean original differs from build/")
    check.unlink()
    base, new = hashes(orig), hashes(BUILT.read_bytes())
    text = ZIP_README.read_text(encoding="utf-8")
    for k, v in {"version": ver, "patch": patch.name, **{f"base_{k}": v for k, v in base.items()},
                 **{f"new_{k}": v for k, v in new.items()}}.items():
        text = text.replace("{" + k + "}", str(v))
    if re.search(r"\{[a-z_0-9]+\}", text):
        sys.exit(f"release: unfilled field in {ZIP_README.name}: {re.findall(r'{[a-z_0-9]+}', text)[:4]}")
    readme.write_text(text, encoding="utf-8", newline="\r\n")
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
        z.write(patch, patch.name)
        z.write(readme, "README.txt")
    with zipfile.ZipFile(zpath) as z:
        names = sorted(z.namelist())
        assert names == sorted([patch.name, "README.txt"]), names
        assert z.read(patch.name) == patch.read_bytes()
    print(f"\nrelease {ver}: {zpath.relative_to(ROOT)} ({zpath.stat().st_size} bytes)")
    print(f"  patch {patch.name}: sha1 {hashlib.sha1(patch.read_bytes()).hexdigest()}")
    print(f"  base  CRC32 {base['crc32']}  SHA-1 {base['sha1']}")
    print(f"  built CRC32 {new['crc32']}  SHA-1 {new['sha1']}  ({new['size']} bytes)")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
