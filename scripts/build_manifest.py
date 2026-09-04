#!/usr/bin/env python3
"""Regenerate screensaver.json from the images in photos/.

Emits one entry per image with its raw.githubusercontent.com URL plus the EXIF
bits the TV launcher's overlay needs: GPS coordinates (reverse-geocoded to a
place name on-device) and the capture time as ISO-8601.

    {
      "count": 48,
      "images": [
        {"url": "https://raw.githubusercontent.com/...jpg",
         "lat": 37.7749, "lon": -122.4194,
         "taken": "2024-07-06T01:09:29"}
      ]
    }

The output is deterministic for a given photo set — no build timestamp — so the
workflow's "commit only if changed" check actually means something. Git history
is the record of when the manifest last changed.

`lat`/`lon`/`taken` are omitted for photos that carry no such EXIF. The launcher
also accepts a plain ["url", ...] array, so this shape is a superset.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import quote

from PIL import Image

REPO_ROOT = Path(__file__).resolve().parent.parent
PHOTO_DIR = REPO_ROOT / "photos"
MANIFEST = REPO_ROOT / "screensaver.json"

EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}

# EXIF tag ids (see exif spec). Pillow exposes these IFDs by id.
EXIF_IFD = 0x8769
GPS_IFD = 0x8825
TAG_DATETIME_ORIGINAL = 36867
TAG_DATETIME = 306
GPS_LAT_REF, GPS_LAT, GPS_LON_REF, GPS_LON = 1, 2, 3, 4


def raw_url_base() -> str:
    """Base URL photos are served from — derived from the CI environment."""
    repo = os.environ.get("GITHUB_REPOSITORY", "rahinroy/photos")
    branch = os.environ.get("GITHUB_REF_NAME", "main")
    return f"https://raw.githubusercontent.com/{repo}/{branch}/photos"


def to_degrees(value) -> float | None:
    """Convert an EXIF (deg, min, sec) rational triple to decimal degrees."""
    try:
        deg, minute, sec = (float(v) for v in value)
    except (TypeError, ValueError):
        return None
    return deg + minute / 60 + sec / 3600


def read_exif(path: Path) -> dict:
    """Pull lat/lon/taken out of one image. Never raises — bad EXIF just yields {}."""
    out: dict = {}
    try:
        with Image.open(path) as img:
            exif = img.getexif()
            if not exif:
                return out

            gps = exif.get_ifd(GPS_IFD)
            if gps:
                lat = to_degrees(gps.get(GPS_LAT))
                lon = to_degrees(gps.get(GPS_LON))
                if lat is not None and lon is not None:
                    if str(gps.get(GPS_LAT_REF, "N")).upper().startswith("S"):
                        lat = -lat
                    if str(gps.get(GPS_LON_REF, "E")).upper().startswith("W"):
                        lon = -lon
                    out["lat"] = round(lat, 6)
                    out["lon"] = round(lon, 6)

            sub = exif.get_ifd(EXIF_IFD)
            raw = sub.get(TAG_DATETIME_ORIGINAL) or exif.get(TAG_DATETIME)
            if raw:
                # EXIF stores "YYYY:MM:DD HH:MM:SS"; emit ISO-8601 instead.
                try:
                    taken = datetime.strptime(str(raw).strip(), "%Y:%m:%d %H:%M:%S")
                    out["taken"] = taken.isoformat()
                except ValueError:
                    pass
    except Exception as exc:  # unreadable / truncated / not really an image
        print(f"  ! {path.name}: could not read EXIF ({exc})", file=sys.stderr)
    return out


def main() -> int:
    if not PHOTO_DIR.is_dir():
        print(f"No photos/ directory at {PHOTO_DIR}", file=sys.stderr)
        return 1

    base = raw_url_base()
    files = sorted(
        (p for p in PHOTO_DIR.iterdir() if p.suffix.lower() in EXTENSIONS),
        key=lambda p: p.name,
    )

    images = []
    for path in files:
        entry = {"url": f"{base}/{quote(path.name)}"}
        entry.update(read_exif(path))
        images.append(entry)
        bits = [k for k in ("lat", "taken") if k in entry]
        print(f"  {path.name}" + (f"  [{', '.join(bits)}]" if bits else "  [no exif]"))

    manifest = {"count": len(images), "images": images}
    MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"\nWrote {MANIFEST.name}: {len(images)} image(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
