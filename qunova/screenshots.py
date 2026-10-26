"""Capture sections of the local docs preview as PNGs for review PRs.

The preview (`./start`) must already be serving http://localhost:3000. The
preview mounts the working tree, so check out the ref you want to capture,
wait for the page to reload, and run this once per ref with a different
label (for example `before` on upstream/main, `after` on the change branch).

    uv run --with playwright python qunova/screenshots.py \
        --shots shots.json --label after --out /tmp/shots

shots.json is a list of sections. Each section runs from the first heading
or paragraph whose text starts with `start` to the one that starts with
`end`, or to the end of the page when `end` is null:

    [
      {"name": "api-outputs", "url": "/docs/api/functions/qunova-chemistry",
       "start": "Outputs", "end": null},
      {"name": "guide-changelog", "url": "/docs/guides/qunova-chemistry",
       "start": "Changelog", "end": "Get support"}
    ]

Files are written as <out>/<name>-<label>.png. A section that is not on the
page (for example a new section, captured on the old ref) is skipped.

Uses the installed Google Chrome, so no browser download is needed.
"""

import argparse
import json
from pathlib import Path

from playwright.sync_api import sync_playwright

CLIP_JS = """([start, end]) => {
  const main = document.querySelector('main');
  const els = [...main.querySelectorAll('h1,h2,h3,h4,p')];
  const find = t => els.find(x => x.innerText.trim().startsWith(t));
  const a = find(start);
  if (!a) return null;
  const b = end ? find(end) : null;
  const m = main.getBoundingClientRect(), y0 = window.scrollY;
  const top = a.getBoundingClientRect().top + y0 - 16;
  const bottom = b ? b.getBoundingClientRect().top + y0 - 12 : m.bottom + y0;
  return {x: Math.max(m.left - 16, 0), y: top, width: m.width + 32, height: bottom - top};
}"""


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--shots", required=True, type=Path)
    parser.add_argument("--label", required=True)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--base-url", default="http://localhost:3000")
    args = parser.parse_args()

    shots = json.loads(args.shots.read_text())
    args.out.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome")
        page = browser.new_page(
            viewport={"width": 1400, "height": 1000}, device_scale_factor=2
        )
        for shot in shots:
            page.goto(
                args.base_url + shot["url"], wait_until="networkidle", timeout=180000
            )
            page.wait_for_timeout(1500)
            clip = page.evaluate(CLIP_JS, [shot["start"], shot.get("end")])
            if not clip:
                print(f"{shot['name']}: not on this page, skipped")
                continue
            path = args.out / f"{shot['name']}-{args.label}.png"
            page.screenshot(path=path, clip=clip, full_page=True)
            print(f"{shot['name']}: {path}")
        browser.close()


if __name__ == "__main__":
    main()
