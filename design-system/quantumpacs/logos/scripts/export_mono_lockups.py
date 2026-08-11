#!/usr/bin/env python3
"""Export mono-light (reversed, white-ink) lockup PNGs for the email-signature kit.

Each lockup is recolored: white ink for the mark + wordmark, cyan-400 (#22D3EE)
accent on the "PACS" tspan, and secondary mark elements at reduced opacity so
the monochrome hierarchy reads on dark surfaces. Orbit gets an inline rebuild
(no mono-light SVG exists); Q-Orbit and Aperture SVGs are recolored in place.

Outputs: logos/png/{family}/{family}-lockup-mono-light-{128,256,512}.png
"""
import subprocess, os, re

ROOT = "/home/dev/Documents/OPP/openpacs/design-system/quantumpacs/logos"
CHROME = "/usr/bin/google-chrome-stable"
TMP = "/tmp/qp_mono_lockup"
os.makedirs(TMP, exist_ok=True)

# ── Orbit: exact-geometry inline rebuild, white ink ──
ORBIT_WHITE = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 340 80" role="img" aria-labelledby="t0lw d0lw">
  <title id="t0lw">QuantumPACS — Orbit lockup, mono light (reversed)</title>
  <desc id="d0lw">Orbit mark and QuantumPACS wordmark in white for dark surfaces.</desc>
  <g id="icon" transform="translate(8,8) scale(1.6)">
    <circle cx="20" cy="20" r="18" stroke="#FFFFFF" stroke-width="3" fill="none"/>
    <circle cx="20" cy="20" r="10" stroke="#FFFFFF" stroke-width="2" fill="none" opacity="0.55"/>
    <line x1="20" y1="2" x2="20" y2="10" stroke="#FFFFFF" stroke-width="2" stroke-linecap="round"/>
    <line x1="20" y1="30" x2="20" y2="38" stroke="#FFFFFF" stroke-width="2" stroke-linecap="round"/>
    <ellipse cx="20" cy="20" rx="6" ry="2.5" stroke="#FFFFFF" stroke-width="1.5" fill="none" opacity="0.7"/>
    <circle cx="20" cy="20" r="2.5" fill="#FFFFFF"/>
  </g>
  <text x="90" y="50" font-family="Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif" font-size="34" font-weight="700" fill="#FFFFFF">
    Quantum<tspan fill="#22D3EE">PACS</tspan>
  </text>
</svg>"""

# ── Q-Orbit / Aperture: recolor in place ──
def recolor(svg: str) -> str:
    svg = re.sub(r'fill="#[0-9A-Fa-f]{6}"', 'fill="#FFFFFF"', svg)
    svg = re.sub(r'stroke="#[0-9A-Fa-f]{6}"', 'stroke="#FFFFFF"', svg)
    svg = svg.replace('fill="url(#g)"', 'fill="#FFFFFF"')
    svg = svg.replace('stroke="url(#g)"', 'stroke="#FFFFFF"')
    # secondary elements get reduced opacity to preserve hierarchy
    svg = svg.replace('<circle cx="84" cy="84" r="6.5" fill="#FFFFFF"/>',
                      '<circle cx="84" cy="84" r="6.5" fill="#FFFFFF" opacity="0.7"/>')
    svg = svg.replace('<circle cx="42" cy="42" r="6.5" fill="#FFFFFF"/>',
                      '<circle cx="42" cy="42" r="6.5" fill="#FFFFFF" opacity="0.7"/>')
    svg = svg.replace('<circle cx="50" cy="50" r="24" fill="none" stroke="#FFFFFF" stroke-width="3.5"/>',
                      '<circle cx="50" cy="50" r="24" fill="none" stroke="#FFFFFF" stroke-width="3.5" opacity="0.55"/>')
    svg = svg.replace('<circle cx="50" cy="50" r="4.5" fill="#FFFFFF"/>',
                      '<circle cx="50" cy="50" r="4.5" fill="#FFFFFF" opacity="0.7"/>')
    # PACS accent LAST — match the ALREADY-WHITENED tspan (the white pass above
    # rewrote fill="#0E7490" to fill="#FFFFFF"; matching the original hex would
    # find nothing). Regex, not string replace: source has a newline between
    # Quantum and <tspan>.
    svg = re.sub(r'<tspan fill="#FFFFFF">PACS</tspan>',
                 '<tspan fill="#22D3EE">PACS</tspan>', svg, flags=re.S)
    return svg

def build_svg(fam: str) -> str:
    if fam == "orbit":
        return ORBIT_WHITE
    src = os.path.join(ROOT, "round2", "%s-lockup-horizontal.svg" % fam)
    with open(src) as f:
        return recolor(f.read())

def rasterize(svg_path: str, out_path: str, w: int, h: int):
    subprocess.run([CHROME, "--headless", "--disable-gpu", "--no-sandbox",
                    "--force-device-scale-factor=1", "--default-background-color=00000000",
                    "--window-size=%d,%d" % (w, h), "--screenshot=%s" % out_path,
                    "file://" + svg_path], capture_output=True, timeout=60, check=True)

def main():
    import xml.etree.ElementTree as ET
    sizes = [128, 256, 512]
    for fam in ("orbit", "qorbit", "aperture"):
        svg_path = os.path.join(TMP, fam + "-lockup-mono-light.svg")
        with open(svg_path, "w") as f:
            f.write(build_svg(fam))
        vb = ET.parse(svg_path).getroot().get("viewBox")
        _, _, vw, vh = map(float, vb.split())
        out_dir = os.path.join(ROOT, "png", fam)
        os.makedirs(out_dir, exist_ok=True)
        for w in sizes:
            h = max(1, round(w * vh / vw))
            out = os.path.join(out_dir, "%s-lockup-mono-light-%d.png" % (fam, w))
            rasterize(svg_path, out, w, h)
            print("wrote %s %dx%d" % (os.path.relpath(out, ROOT), w, h))
    print("done")

if __name__ == "__main__":
    main()
