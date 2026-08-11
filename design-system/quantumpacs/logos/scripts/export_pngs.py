#!/usr/bin/env python3
"""Regenerate the QuantumPACS logo PNG export set.

Renders every SVG in the three logo families (Orbit, Q-Orbit, Aperture)
to transparent-background RGBA PNGs via headless Chrome:

  square assets (icon / mono-dark / mono-light / favicon)  -> 32 / 48 / 64 / 128px edge
  lockups (horizontal + vertical)                          -> 128 / 256 / 512px wide

Lockups skip the sub-128 sizes on purpose: BRAND-KIT.md §2.9 sets a
140px minimum lockup width, below which the wordmark is unreadable.

Requires: google-chrome (or chromium) on PATH, Python 3.8+.
Usage:    python3 export_pngs.py          # writes design-system/quantumpacs/logos/png/
"""
import os
import re
import shutil
import subprocess
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # .../logos
OUT = os.path.join(BASE, "png")
SQUARE_SIZES = [32, 48, 64, 128]
LOCKUP_SIZES = [128, 256, 512]

# family -> (svg stem, kind)
FAMILIES = {
    "orbit": [
        ("orbit-current-icon", "square"),
        ("orbit-current-icon-mono-dark", "square"),
        ("orbit-current-icon-mono-light", "square"),
        ("orbit-current-favicon", "square"),
        ("orbit-current-lockup", "lockup"),
        ("orbit-current-lockup-vertical", "lockup"),
    ],
    "qorbit": [
        ("qorbit-icon", "square"),
        ("qorbit-icon-mono-dark", "square"),
        ("qorbit-icon-mono-light", "square"),
        ("qorbit-favicon", "square"),
        ("qorbit-lockup-horizontal", "lockup"),
        ("qorbit-lockup-vertical", "lockup"),
    ],
    "aperture": [
        ("aperture-icon", "square"),
        ("aperture-icon-mono-dark", "square"),
        ("aperture-icon-mono-light", "square"),
        ("aperture-favicon", "square"),
        ("aperture-lockup-horizontal", "lockup"),
        ("aperture-lockup-vertical", "lockup"),
    ],
}

VIEWBOX_RE = re.compile(r'viewBox="([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)"')


def chrome_bin():
    for name in ("google-chrome-stable", "google-chrome", "chromium", "chromium-browser"):
        path = shutil.which(name)
        if path:
            return path
    raise SystemExit("No Chrome/Chromium found — install one or use Inkscape/ImageMagick instead.")


def viewbox_dims(path):
    with open(path) as f:
        m = VIEWBOX_RE.search(f.read())
    if not m:
        return None
    _, _, w, h = (float(g) for g in m.groups())
    return w, h


def render(chrome, svg_path, out_png, target_w, target_h):
    cmd = [
        chrome, "--headless", "--disable-gpu", "--no-sandbox",
        "--force-device-scale-factor=1",
        f"--window-size={target_w},{target_h}",
        "--default-background-color=00000000",
        f"--screenshot={out_png}",
        "file://" + svg_path,
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0 or not os.path.exists(out_png):
        return f"FAIL {svg_path}: {r.stderr.strip()[-200:]}"
    return None


def main():
    chrome = chrome_bin()
    errors = []
    made = 0
    for family, assets in FAMILIES.items():
        fdir = os.path.join(OUT, family)
        os.makedirs(fdir, exist_ok=True)
        for stem, kind in assets:
            src = os.path.join(BASE, f"{stem}.svg") if family == "orbit" else os.path.join(BASE, "round2", f"{stem}.svg")
            dims = viewbox_dims(src)
            if not dims:
                errors.append(f"no viewBox: {src}")
                continue
            vw, vh = dims
            for size in (SQUARE_SIZES if kind == "square" else LOCKUP_SIZES):
                if kind == "square":
                    tw = th = size
                elif vw >= vh:  # wide lockup: size = width
                    tw, th = size, max(1, round(size * vh / vw))
                else:  # tall lockup: size = height
                    th, tw = size, max(1, round(size * vw / vh))
                out_png = os.path.join(fdir, f"{stem}-{size}.png")
                err = render(chrome, src, out_png, tw, th)
                if err:
                    errors.append(err)
                else:
                    made += 1
    print(f"rendered {made} PNGs into {OUT}")
    if errors:
        print("ERRORS:")
        for e in errors[:20]:
            print(" ", e)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
