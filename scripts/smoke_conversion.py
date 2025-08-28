#!/usr/bin/env python3
from __future__ import annotations

import sys
import shutil
from pathlib import Path


def main() -> None:
    if sys.version_info < (3, 9):
        print("[SKIP] Python >=3.9 required for conversion engine; current:", sys.version)
        return

    ROOT = Path(__file__).resolve().parents[1]
    SRC = ROOT / "src"
    sys.path.insert(0, str(SRC))

    # Lazy imports after sys.path
    from tg_bot.services.conversion import build_options, ensure_dirs  # type: ignore
    from sticker_convert.job import Job  # type: ignore
    from sticker_convert.utils.files.metadata_handler import MetadataHandler  # type: ignore

    sample_dir = ROOT / "tests" / "samples"
    if not sample_dir.is_dir():
        print("[SKIP] samples directory not found:", sample_dir)
        return

    work = ROOT / "tmp_smoke_conv"
    in_dir = work / "in"
    out_dir = work / "out"
    shutil.rmtree(work, ignore_errors=True)
    ensure_dirs(in_dir)
    ensure_dirs(out_dir)

    # Copy a few static samples to input
    for name in [
        "static_png_1_800x600.png",
        "static_jpg_800x600.jpg",
        "static_jpeg_800x600.jpeg",
    ]:
        src = sample_dir / name
        if src.exists():
            shutil.copy2(src, in_dir / name)

    MetadataHandler.generate_emoji_file(in_dir, default_emoji="😀")
    (in_dir / "title.txt").write_text("Smoke Pack", encoding="utf-8")

    opt_input, comp, out, cred = build_options(in_dir, out_dir, platform="local", url=None)
    job = Job(opt_input, comp, out, cred, print, print, lambda *a, **k: None, lambda *a, **k: False, lambda *a, **k: "")
    job.start()

    files = [p for p in sorted(out_dir.iterdir()) if p.is_file()]
    print(f"[OK] Conversion produced {len(files)} files:")
    for p in files:
        print(" ", p.name)


if __name__ == "__main__":
    main()
