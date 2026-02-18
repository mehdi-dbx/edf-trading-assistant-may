#!/usr/bin/env python3
"""Download PNG logos for each distinct airline in data/checkin_raw.csv into data/img/.

Uses Wikimedia Commons API for thumbnail/direct URLs. Run: uv run python data/download_airline_logos.py
"""
import csv
import json
import re
import urllib.parse
import urllib.request
from pathlib import Path

# Commons filename per airline (File:... on Commons)
AIRLINE_LOGO_MAP = {
    "Air France": "File:Air_France_Logo.svg",
    "British Airways": "File:BRITISH AIRWAYS logo.svg",
    "Delta Air Lines": "File:Delta_logo.svg",
    "Emirates": "File:Emirates_logo.svg",
    "Lufthansa": "File:Lufthansa_Group.svg",
    "Qatar Airways": "File:Qatar_Airways_Logo.png",
    "United Airlines": "File:United_Airlines_logo_(1973_-_2010).svg",
}

WIKI_API = "https://commons.wikimedia.org/w/api.php"
THUMB_WIDTH = 330


def _slug(name: str) -> str:
    """Filesystem-safe slug: e.g. 'Delta Air Lines' -> 'delta_air_lines'."""
    s = re.sub(r"[^\w\s-]", "", name)
    s = re.sub(r"[-\s]+", "_", s).strip("_").lower()
    return s or "logo"


def _get_image_url(commons_title: str) -> str | None:
    """Get PNG URL: thumburl (330px) for SVG, url for PNG. Returns None on failure."""
    params = {
        "action": "query",
        "titles": commons_title,
        "prop": "imageinfo",
        "iiprop": "url",
        "iiurlwidth": THUMB_WIDTH,
        "format": "json",
    }
    url = WIKI_API + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": "AmadeusAirops/1.0"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        data = json.loads(resp.read().decode())
    pages = data.get("query", {}).get("pages", {})
    for pid, page in pages.items():
        if pid == "-1":
            return None
        info = (page.get("imageinfo") or [None])[0]
        if not info:
            return None
        # Prefer thumbnail for SVG (PNG render); else direct url
        return info.get("thumburl") or info.get("url")
    return None


def main() -> None:
    data_dir = Path(__file__).resolve().parent
    csv_path = data_dir / "checkin_raw.csv"
    img_dir = data_dir / "img"
    img_dir.mkdir(parents=True, exist_ok=True)

    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        airlines = sorted({row["airline"] for row in reader})

    opener = urllib.request.build_opener()
    opener.addheaders = [("User-Agent", "AmadeusAirops/1.0 (logo download)")]
    urllib.request.install_opener(opener)

    for airline in airlines:
        commons_title = AIRLINE_LOGO_MAP.get(airline)
        if not commons_title:
            print(f"Skip (no mapping): {airline}")
            continue
        url = _get_image_url(commons_title)
        if not url:
            print(f"Skip (no URL from API): {airline}")
            continue
        slug = _slug(airline)
        out_path = img_dir / f"{slug}.png"
        try:
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = resp.read()
            out_path.write_bytes(data)
            print(f"Downloaded: {airline} -> {out_path}")
        except Exception as e:
            print(f"Failed {airline}: {e}")


if __name__ == "__main__":
    main()
